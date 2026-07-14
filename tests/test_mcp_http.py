import json
from collections.abc import Iterator
from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
from typing import Any

import pytest

from kr_gov_job_mcp.mcp_http import make_mcp_http_handler
from kr_gov_job_mcp.tools import create_default_registry


@contextmanager
def _mcp_http_server() -> Iterator[tuple[str, int]]:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_mcp_http_handler(create_default_registry()),
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
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-11-25",
    }
    connection = HTTPConnection(host, port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
        parsed = json.loads(response_body) if response_body else None
        return response.status, parsed
    finally:
        connection.close()


def _assert_issue_112_input_schemas(tools: list[dict]) -> None:
    schemas = {tool["name"]: tool["inputSchema"] for tool in tools}
    id_aliases = [
        {"required": ["job_id"]},
        {"required": ["source_job_id"]},
        {"required": ["recruitment_notice_sn"]},
    ]

    assert schemas["analyze_institution_strategy"]["required"] == ["institution_name"]
    assert "anyOf" not in schemas["analyze_institution_strategy"]
    assert schemas["analyze_institution_weakness"]["required"] == ["institution_name"]
    assert "anyOf" not in schemas["analyze_institution_weakness"]
    assert schemas["fetch_job_detail"]["anyOf"] == id_aliases
    assert schemas["analyze_job_fit_report"]["anyOf"] == id_aliases
    assert schemas["prepare_institution_interview"]["required"] == ["institution_name"]
    assert schemas["prepare_institution_interview"]["anyOf"] == [
        {"required": ["target_role"]},
        {"required": ["job_family"]},
    ]
    required_strings = {
        "analyze_institution_strategy": ["institution_name"],
        "analyze_institution_weakness": ["institution_name"],
        "fetch_job_detail": ["job_id", "source_job_id", "recruitment_notice_sn"],
        "analyze_job_fit_report": ["job_id", "source_job_id", "recruitment_notice_sn"],
        "prepare_institution_interview": ["institution_name", "target_role", "job_family"],
    }
    for tool_name, fields in required_strings.items():
        for field in fields:
            assert schemas[tool_name]["properties"][field]["pattern"] == r"\S"


def test_mcp_http_health_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SOURCE_REF", "refs/heads/main")
    monkeypatch.setenv("APP_REVISION", "257e45c")

    with _mcp_http_server() as (host, port):
        status, payload = _request(host, port, "GET", "/health")

    assert status == 200
    assert payload["status"] == "ok"
    assert payload["registered_tools"] == 9
    assert payload["source_ref"] == "refs/heads/main"
    assert payload["revision"] == "257e45c"


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
    tools = list_payload["result"]["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert "lookup_region_codes" in tool_names
    assert "search_public_jobs" in tool_names
    search_public_jobs = next(tool for tool in tools if tool["name"] == "search_public_jobs")
    assert "kr-gov-job-mcp" in search_public_jobs["description"]
    assert search_public_jobs["annotations"]["readOnlyHint"] is True
    assert search_public_jobs["annotations"]["openWorldHint"] is True
    expected_schemas = {
        tool["name"]: tool["input_schema"] for tool in create_default_registry().list_tools()
    }
    assert {tool["name"]: tool["inputSchema"] for tool in tools} == expected_schemas
    _assert_issue_112_input_schemas(tools)


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
