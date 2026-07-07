"""Minimal MCP Streamable HTTP transport backed by the in-process tool registry."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
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
DEFAULT_CORS_ALLOW_HEADERS = "accept, content-type, mcp-protocol-version"
DEFAULT_CORS_ALLOW_METHODS = "GET, POST, OPTIONS"
DEFAULT_CORS_MAX_AGE = "86400"
DEFAULT_CORS_ALLOWED_ORIGINS = ("*",)


def run_http_server(
    registry: ToolRegistry,
    *,
    host: str,
    port: int,
    allowed_origins: Iterable[str] | None = None,
) -> int:
    """Serve MCP JSON-RPC requests over HTTP until the process is interrupted."""

    server = ThreadingHTTPServer(
        (host, port),
        make_mcp_http_handler(registry, allowed_origins=allowed_origins),
    )
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
    allowed_origins: Iterable[str] | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Create an HTTP handler bound to a tool registry."""

    cors_allowed_origins = _normalize_allowed_origins(allowed_origins)

    class MCPHTTPHandler(BaseHTTPRequestHandler):
        server_version = "kr-gov-job-mcp"

        def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path not in {"/", "/health", MCP_ENDPOINT}:
                self._send_empty(HTTPStatus.NOT_FOUND)
                return
            self._send_empty(HTTPStatus.NO_CONTENT, cors_preflight=True)

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

        def _send_empty(self, status: HTTPStatus, *, cors_preflight: bool = False) -> None:
            self.send_response(status)
            self._send_cors_headers(preflight=cors_preflight)
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()

        def _send_json(self, status: HTTPStatus, payload: Mapping[str, Any] | list[Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers(preflight=False)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def _send_cors_headers(self, *, preflight: bool) -> None:
            allow_origin = _resolve_cors_allow_origin(
                self.headers.get("Origin"),
                cors_allowed_origins,
            )
            if allow_origin is None:
                return

            self.send_header("Access-Control-Allow-Origin", allow_origin)
            if allow_origin != "*":
                self.send_header("Vary", "Origin")
            if preflight:
                self.send_header("Access-Control-Allow-Methods", DEFAULT_CORS_ALLOW_METHODS)
                self.send_header(
                    "Access-Control-Allow-Headers",
                    self.headers.get("Access-Control-Request-Headers")
                    or DEFAULT_CORS_ALLOW_HEADERS,
                )
                self.send_header("Access-Control-Max-Age", DEFAULT_CORS_MAX_AGE)

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


def _normalize_allowed_origins(allowed_origins: Iterable[str] | None) -> tuple[str, ...]:
    if allowed_origins is not None:
        normalized = tuple(origin.strip() for origin in allowed_origins if origin.strip())
        return normalized or DEFAULT_CORS_ALLOWED_ORIGINS

    raw_origins = (
        os.environ.get("MCP_CORS_ALLOW_ORIGINS")
        or os.environ.get("MCP_CORS_ALLOW_ORIGIN")
        or "*"
    )
    normalized = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
    return normalized or DEFAULT_CORS_ALLOWED_ORIGINS


def _resolve_cors_allow_origin(origin: str | None, allowed_origins: tuple[str, ...]) -> str | None:
    if not origin:
        return None
    if "*" in allowed_origins:
        return "*"
    if origin in allowed_origins:
        return origin
    return None
