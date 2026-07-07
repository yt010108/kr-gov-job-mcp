"""Minimal MCP Streamable HTTP transport backed by the in-process tool registry."""

from __future__ import annotations

import json
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from kr_gov_job_mcp.mcp_stdio import (
    INVALID_REQUEST,
    PARSE_ERROR,
    _error_response,
    handle_json_rpc_message,
)
from kr_gov_job_mcp.tools import ToolRegistry


MCP_ENDPOINT = "/mcp"


def run_http_server(
    registry: ToolRegistry,
    *,
    host: str,
    port: int,
) -> int:
    """Serve MCP JSON-RPC requests over HTTP until the process is interrupted."""

    server = ThreadingHTTPServer((host, port), make_mcp_http_handler(registry))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def make_mcp_http_handler(registry: ToolRegistry) -> type[BaseHTTPRequestHandler]:
    """Create an HTTP handler bound to a tool registry."""

    class MCPHTTPHandler(BaseHTTPRequestHandler):
        server_version = "kr-gov-job-mcp"

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path == "/health":
                self._send_json(HTTPStatus.OK, registry.call("health_check"))
                return
            if self.path == "/":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "service": "kr-gov-job-mcp",
                        "status": "ok",
                        "mcp_endpoint": MCP_ENDPOINT,
                    },
                )
                return
            if self.path == MCP_ENDPOINT:
                self._send_json(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    {
                        "error": "SSE GET streams are not implemented; send JSON-RPC requests with POST.",
                    },
                )
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path not in {"/", MCP_ENDPOINT}:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return

            raw_body = self._read_body()
            try:
                payload = json.loads(raw_body)
            except json.JSONDecodeError as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    _error_response(None, PARSE_ERROR, f"Parse error: {exc.msg}"),
                )
                return

            response = _handle_http_payload(payload, registry)
            if response is None:
                self._send_empty(HTTPStatus.ACCEPTED)
                return
            self._send_json(HTTPStatus.OK, response)

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _read_body(self) -> str:
            length_header = self.headers.get("Content-Length", "0")
            try:
                length = int(length_header)
            except ValueError:
                length = 0
            return self.rfile.read(length).decode("utf-8")

        def _send_empty(self, status: HTTPStatus) -> None:
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()

        def _send_json(self, status: HTTPStatus, payload: Mapping[str, Any] | list[Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

    return MCPHTTPHandler


def _handle_http_payload(payload: Any, registry: ToolRegistry) -> dict[str, Any] | list[Any] | None:
    if isinstance(payload, list):
        if not payload:
            return _error_response(None, INVALID_REQUEST, "Invalid Request")
        responses = [
            response
            for message in payload
            if (response := handle_json_rpc_message(message, registry)) is not None
        ]
        return responses or None

    return handle_json_rpc_message(payload, registry)
