"""Minimal MCP stdio transport backed by the in-process tool registry."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, TextIO

from kr_gov_job_mcp import __version__
from kr_gov_job_mcp.tools import ToolRegistry


JSONRPC_VERSION = "2.0"
DEFAULT_PROTOCOL_VERSION = "2025-11-25"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def run_stdio_server(
    registry: ToolRegistry,
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Serve newline-delimited MCP JSON-RPC messages until stdin closes."""

    for line in stdin:
        if not line.strip():
            continue
        response = _handle_line(line, registry)
        if response is None:
            continue
        _write_message(response, stdout)
    return 0


def _handle_line(line: str, registry: ToolRegistry) -> dict[str, Any] | None:
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        return _error_response(None, PARSE_ERROR, f"Parse error: {exc.msg}")

    return handle_json_rpc_message(message, registry)


def handle_json_rpc_message(message: Any, registry: ToolRegistry) -> dict[str, Any] | None:
    """Handle one MCP JSON-RPC message.

    A return value of ``None`` means the message was a notification and no response should be
    written by the active transport.
    """

    if not isinstance(message, dict):
        return _error_response(None, INVALID_REQUEST, "Invalid Request")

    message_id = message.get("id")
    is_notification = "id" not in message

    if message.get("jsonrpc") != JSONRPC_VERSION:
        if is_notification:
            return None
        return _error_response(message_id, INVALID_REQUEST, "Invalid JSON-RPC version")

    method = message.get("method")
    if not isinstance(method, str):
        if is_notification:
            return None
        return _error_response(message_id, INVALID_REQUEST, "Invalid or missing method")

    if is_notification:
        return None

    params = message.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return _error_response(message_id, INVALID_PARAMS, "params must be an object")

    try:
        result = _handle_request(method, params, registry)
    except KeyError as exc:
        return _error_response(message_id, INVALID_PARAMS, str(exc))
    except ValueError as exc:
        return _error_response(message_id, INVALID_PARAMS, str(exc))
    except Exception as exc:  # pragma: no cover - defensive boundary for stdio clients
        return _error_response(message_id, INTERNAL_ERROR, str(exc))
    return _success_response(message_id, result)


def _handle_request(
    method: str,
    params: Mapping[str, Any],
    registry: ToolRegistry,
) -> dict[str, Any]:
    if method == "initialize":
        requested_version = params.get("protocolVersion")
        protocol_version = (
            requested_version if isinstance(requested_version, str) else DEFAULT_PROTOCOL_VERSION
        )
        return {
            "protocolVersion": protocol_version,
            "capabilities": {
                "tools": {
                    "listChanged": False,
                }
            },
            "serverInfo": {
                "name": "kr-gov-job-mcp",
                "version": __version__,
            },
        }

    if method == "ping":
        return {}

    if method == "tools/list":
        return {
            "tools": [_mcp_tool_dict(tool) for tool in registry.list_tools()],
        }

    if method == "tools/call":
        return _call_tool(params, registry)

    raise KeyError(f"unknown MCP method: {method}")


def _call_tool(params: Mapping[str, Any], registry: ToolRegistry) -> dict[str, Any]:
    name = params.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("tools/call requires params.name")

    arguments = params.get("arguments", {})
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise ValueError("tools/call params.arguments must be an object")

    try:
        result = registry.call(name, arguments)
    except KeyError:
        raise
    except (ValueError, TypeError) as exc:
        return _tool_result({"error": str(exc)}, is_error=True)
    except Exception as exc:  # pragma: no cover - external source failures are surfaced to clients
        return _tool_result({"error": str(exc)}, is_error=True)

    return _tool_result(result, is_error=False)


def _tool_result(payload: Mapping[str, Any], *, is_error: bool) -> dict[str, Any]:
    structured = dict(payload)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(structured, ensure_ascii=False, sort_keys=True),
            }
        ],
        "structuredContent": structured,
        "isError": is_error,
    }


def _mcp_tool_dict(tool: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": tool["name"],
        "description": tool.get("description", ""),
        "inputSchema": tool.get("input_schema") or {"type": "object", "properties": {}},
        "annotations": tool.get("annotations") or {},
    }


def _success_response(message_id: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": message_id,
        "result": dict(result),
    }


def _error_response(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": message_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _write_message(message: Mapping[str, Any], stdout: TextIO) -> None:
    stdout.write(json.dumps(message, ensure_ascii=False, sort_keys=True))
    stdout.write("\n")
    stdout.flush()
