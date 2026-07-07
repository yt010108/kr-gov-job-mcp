"""Minimal MCP Streamable HTTP transport backed by the in-process tool registry."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
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
SUPPORTED_PROTOCOL_VERSIONS = {DEFAULT_PROTOCOL_VERSION, "2025-03-26"}
_CORS_ALLOW_HEADERS = (
    "Accept, Content-Type, Last-Event-ID, MCP-Protocol-Version, MCP-Session-Id"
)
_CORS_EXPOSE_HEADERS = "MCP-Protocol-Version, MCP-Session-Id"
_HTTP_METHODS = {"GET", "POST", "OPTIONS"}
_MCP_POST_ACCEPT_TYPES = {"application/json", "text/event-stream"}


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
            if not self._validate_origin():
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
                if not self._validate_accept(required={"text/event-stream"}):
                    return
                self._send_json(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    {
                        "error": "SSE GET streams are not implemented; send JSON-RPC requests with POST.",
                    },
                )
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if not self._validate_origin():
                return
            if self.path not in {"/", MCP_ENDPOINT}:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            if not self._validate_protocol_version():
                return
            if not self._validate_accept(required=_MCP_POST_ACCEPT_TYPES):
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

        def do_DELETE(self) -> None:  # noqa: N802 - stdlib handler API
            if not self._validate_origin():
                return
            if self.path != MCP_ENDPOINT:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            if not self._validate_protocol_version():
                return
            self._send_json(
                HTTPStatus.METHOD_NOT_ALLOWED,
                {
                    "error": (
                        "Session termination is not implemented because this server does not "
                        "maintain HTTP sessions."
                    )
                },
                headers={"Allow": "GET, POST, OPTIONS"},
            )

        def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
            if not self._validate_origin():
                return
            if self.path not in {"/", "/health", MCP_ENDPOINT}:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            requested_method = self.headers.get("Access-Control-Request-Method", "").upper()
            if requested_method and requested_method not in _HTTP_METHODS:
                self._send_json(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    {"error": f"method not allowed for CORS preflight: {requested_method}"},
                    headers={"Allow": "GET, POST, OPTIONS"},
                )
                return
            self._send_empty(
                HTTPStatus.NO_CONTENT,
                headers={
                    "Allow": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": _CORS_ALLOW_HEADERS,
                    "Access-Control-Max-Age": "600",
                },
            )

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _read_body(self) -> str:
            length_header = self.headers.get("Content-Length", "0")
            try:
                length = int(length_header)
            except ValueError:
                length = 0
            return self.rfile.read(length).decode("utf-8")

        def _send_empty(
            self,
            status: HTTPStatus,
            *,
            headers: Mapping[str, str] | None = None,
        ) -> None:
            self.send_response(status)
            self._send_common_headers(headers=headers)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _send_json(
            self,
            status: HTTPStatus,
            payload: Mapping[str, Any] | list[Any],
            *,
            headers: Mapping[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self._send_common_headers(headers=headers)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_common_headers(self, *, headers: Mapping[str, str] | None = None) -> None:
            self.send_header("Connection", "close")
            self.send_header("MCP-Protocol-Version", DEFAULT_PROTOCOL_VERSION)
            for key, value in _cors_response_headers(self).items():
                self.send_header(key, value)
            for key, value in (headers or {}).items():
                self.send_header(key, value)

        def _validate_origin(self) -> bool:
            origin = self.headers.get("Origin")
            if not origin:
                return True
            if _is_allowed_origin(origin, self.headers.get("Host")):
                return True
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": f"origin is not allowed: {origin}"},
            )
            return False

        def _validate_protocol_version(self) -> bool:
            protocol_version = self.headers.get("MCP-Protocol-Version")
            if not protocol_version:
                return True
            if protocol_version in SUPPORTED_PROTOCOL_VERSIONS:
                return True
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "error": f"unsupported MCP-Protocol-Version: {protocol_version}",
                    "supported_protocol_versions": sorted(SUPPORTED_PROTOCOL_VERSIONS),
                },
            )
            return False

        def _validate_accept(self, *, required: set[str]) -> bool:
            accept = self.headers.get("Accept")
            accepted_types = _parse_accept_header(accept)
            if "*/*" in accepted_types or required.issubset(accepted_types):
                return True
            self._send_json(
                HTTPStatus.NOT_ACCEPTABLE,
                {
                    "error": "unsupported Accept header",
                    "required_accept": sorted(required),
                },
            )
            return False

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


def _parse_accept_header(value: str | None) -> set[str]:
    if not value:
        return set()
    accepted: set[str] = set()
    for item in value.split(","):
        media_type = item.split(";", 1)[0].strip().lower()
        if media_type:
            accepted.add(media_type)
    return accepted


def _cors_response_headers(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    origin = handler.headers.get("Origin")
    if not origin or not _is_allowed_origin(origin, handler.headers.get("Host")):
        return {}
    allow_origin = "*" if _allow_all_origins() else origin
    headers = {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Headers": _CORS_ALLOW_HEADERS,
        "Access-Control-Expose-Headers": _CORS_EXPOSE_HEADERS,
        "Vary": "Origin",
    }
    if allow_origin != "*":
        headers["Access-Control-Allow-Credentials"] = "true"
    return headers


def _is_allowed_origin(origin: str, host_header: str | None) -> bool:
    if _allow_all_origins():
        return True
    if _is_same_host_origin(origin, host_header):
        return True
    if _is_loopback_origin(origin):
        return True
    return origin in _configured_allowed_origins()


def _allow_all_origins() -> bool:
    return "*" in _configured_allowed_origins()


def _configured_allowed_origins() -> set[str]:
    raw = os.environ.get("MCP_ALLOWED_ORIGINS") or os.environ.get("MCP_CORS_ALLOW_ORIGINS") or ""
    return {item.strip().rstrip("/") for item in raw.split(",") if item.strip()}


def _is_same_host_origin(origin: str, host_header: str | None) -> bool:
    if not host_header:
        return False
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"}:
        return False
    return parsed.netloc == host_header


def _is_loopback_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"}:
        return False
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}
