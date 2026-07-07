import json
from collections.abc import Iterator
from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
from typing import Any

from kr_gov_job_mcp.mcp_http import make_mcp_http_handler
from kr_gov_job_mcp.tools import create_default_registry


@contextmanager
def _mcp_http_server(allowed_origins: list[str] | None = None) -> Iterator[tuple[str, int]]:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_mcp_http_handler(create_default_registry(), allowed_origins=allowed_origins),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield str(host), int(port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(
    host: str,
    port: int,
    method: str,
    path: str,
    payload: Any | None = None,
) -> tuple[int, Any]:
    status, parsed, _headers = _request_with_headers(host, port, method, path, payload=payload)
    return status, parsed


def _request_with_headers(
    host: str,
    port: int,
    method: str,
    path: str,
    payload: Any | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, Any, dict[str, str]]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-11-25",
    }
    if extra_headers:
        headers.update(extra_headers)
    connection = HTTPConnection(host, port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
        parsed = json.loads(response_body) if response_body else None
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        return response.status, parsed, response_headers
    finally:
        connection.close()


def test_mcp_http_health_endpoint() -> None:
    with _mcp_http_server() as (host, port):
        status, payload = _request(host, port, "GET", "/health")

    assert status == 200
    assert payload["status"] == "ok"
    assert payload["registered_tools"] == 7


def test_mcp_http_initialize_and_list_tools() -> None:
    with _mcp_http_server() as (host, port):
        init_status, init_payload = _request(
            host,
            port,
            "POST",
            "/mcp",
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25"},
            },
        )
        list_status, list_payload = _request(
            host,
            port,
            "POST",
            "/mcp",
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
            },
        )

    assert init_status == 200
    assert init_payload["result"]["serverInfo"]["name"] == "kr-gov-job-mcp"
    assert list_status == 200
    tool_names = {tool["name"] for tool in list_payload["result"]["tools"]}
    assert "lookup_region_codes" in tool_names
    assert "search_public_jobs" in tool_names


def test_mcp_http_call_tool_returns_structured_content() -> None:
    with _mcp_http_server() as (host, port):
        status, payload = _request(
            host,
            port,
            "POST",
            "/mcp",
            {
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {
                    "name": "lookup_region_codes",
                    "arguments": {"query": "서울특별시"},
                },
            },
        )

    result = payload["result"]
    assert status == 200
    assert result["isError"] is False
    assert result["structuredContent"]["matches"][0]["code"] == "R3010"
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]


def test_mcp_http_notification_returns_accepted_without_body() -> None:
    with _mcp_http_server() as (host, port):
        status, payload = _request(
            host,
            port,
            "POST",
            "/mcp",
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            },
        )

    assert status == 202
    assert payload is None


def test_mcp_http_options_preflight_returns_cors_headers() -> None:
    with _mcp_http_server() as (host, port):
        status, payload, headers = _request_with_headers(
            host,
            port,
            "OPTIONS",
            "/mcp",
            extra_headers={
                "Origin": "https://playmcp.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,accept",
            },
        )

    assert status == 204
    assert payload is None
    assert headers["access-control-allow-origin"] == "*"
    assert headers["access-control-allow-methods"] == "GET, POST, OPTIONS"
    assert headers["access-control-allow-headers"] == "content-type,accept"


def test_mcp_http_post_includes_cors_header_for_browser_clients() -> None:
    with _mcp_http_server() as (host, port):
        status, payload, headers = _request_with_headers(
            host,
            port,
            "POST",
            "/mcp",
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25"},
            },
            extra_headers={"Origin": "https://playmcp.example"},
        )

    assert status == 200
    assert payload["result"]["serverInfo"]["name"] == "kr-gov-job-mcp"
    assert headers["access-control-allow-origin"] == "*"


def test_mcp_http_restricted_cors_origin_is_not_reflected() -> None:
    with _mcp_http_server(allowed_origins=["https://allowed.example"]) as (host, port):
        status, payload, headers = _request_with_headers(
            host,
            port,
            "OPTIONS",
            "/mcp",
            extra_headers={
                "Origin": "https://blocked.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert status == 204
    assert payload is None
    assert "access-control-allow-origin" not in headers
