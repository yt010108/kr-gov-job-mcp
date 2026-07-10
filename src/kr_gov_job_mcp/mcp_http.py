"""Minimal, security-conscious MCP Streamable HTTP transport."""

from __future__ import annotations

import json
import os
from collections.abc import Collection, Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from kr_gov_job_mcp.mcp_stdio import (
    DEFAULT_PROTOCOL_VERSION,
    INVALID_REQUEST,
    PARSE_ERROR,
    _error_response,
    handle_json_rpc_message,
)
from kr_gov_job_mcp.tools import ToolRegistry


MCP_ENDPOINT = "/mcp"
ALLOWED_ORIGINS_ENV = "MCP_ALLOWED_ORIGINS"
_ALLOWED_REQUEST_HEADERS = "Content-Type, Accept, MCP-Protocol-Version"
_ALLOWED_METHODS = "GET, POST, OPTIONS"


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


def make_mcp_http_handler(
    registry: ToolRegistry,
    *,
    allowed_origins: Collection[str] | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Create an HTTP handler bound to a registry and an explicit Origin policy.

    Non-browser clients may omit ``Origin``. Browser requests are accepted only from configured
    origins (``MCP_ALLOWED_ORIGINS``, comma-separated) or local development origins.
    """
    configured_origins = frozenset(
        allowed_origins if allowed_origins is not None else _configured_allowed_origins()
    )

    class MCPHTTPHandler(BaseHTTPRequestHandler):
        server_version = "kr-gov-job-mcp"

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            if not self._origin_is_allowed():
                return
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
                    allow="POST, OPTIONS",
                )
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if not self._origin_is_allowed():
                return
            if self.path not in {"/", MCP_ENDPOINT}:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return

            header_error = self._mcp_header_error()
            if header_error:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": header_error})
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

        def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path != MCP_ENDPOINT:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            if not self._origin_is_allowed():
                return
            self._send_empty(HTTPStatus.NO_CONTENT, preflight=True)

        def do_DELETE(self) -> None:  # noqa: N802 - stdlib handler API
            if not self._origin_is_allowed():
                return
            if self.path == MCP_ENDPOINT:
                self._send_json(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    {"error": "MCP sessions are not implemented; DELETE is unsupported."},
                    allow="POST, OPTIONS",
                )
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _origin_is_allowed(self) -> bool:
            origin = self.headers.get("Origin")
            if _is_allowed_origin(origin, configured_origins):
                return True
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "Origin is not allowed."})
            return False

        def _mcp_header_error(self) -> str | None:
            content_type = self.headers.get("Content-Type", "")
            if not content_type.lower().startswith("application/json"):
                return "Content-Type must include application/json."

            accept = self.headers.get("Accept")
            if accept and "application/json" not in accept.lower():
                return "Accept must include application/json."

            protocol_version = self.headers.get("MCP-Protocol-Version")
            if protocol_version and protocol_version != DEFAULT_PROTOCOL_VERSION:
                return (
                    "Unsupported MCP-Protocol-Version: "
                    f"{protocol_version}. Supported version: {DEFAULT_PROTOCOL_VERSION}."
                )
            return None

        def _read_body(self) -> str:
            length_header = self.headers.get("Content-Length", "0")
            try:
                length = int(length_header)
            except ValueError:
                length = 0
            return self.rfile.read(length).decode("utf-8")

        def _send_empty(self, status: HTTPStatus, *, preflight: bool = False) -> None:
            self.send_response(status)
            self._send_common_headers(preflight=preflight)
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()

        def _send_json(
            self,
            status: HTTPStatus,
            payload: Mapping[str, Any] | list[Any],
            *,
            allow: str | None = None,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self._send_common_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            if allow:
                self.send_header("Allow", allow)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def _send_common_headers(self, *, preflight: bool = False) -> None:
            origin = self.headers.get("Origin")
            if origin and _is_allowed_origin(origin, configured_origins):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            if preflight:
                self.send_header("Access-Control-Allow-Methods", _ALLOWED_METHODS)
                self.send_header("Access-Control-Allow-Headers", _ALLOWED_REQUEST_HEADERS)
                self.send_header("Access-Control-Max-Age", "600")

    return MCPHTTPHandler


def _configured_allowed_origins() -> frozenset[str]:
    raw_value = os.getenv(ALLOWED_ORIGINS_ENV, "")
    return frozenset(value.strip() for value in raw_value.split(",") if value.strip())


def _is_allowed_origin(origin: str | None, configured_origins: Collection[str]) -> bool:
    if origin is None:
        return True
    if origin in configured_origins:
        return True

    parsed = urlparse(origin)
    return parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}


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
