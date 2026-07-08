import json
from io import StringIO

from kr_gov_job_mcp.mcp_stdio import run_stdio_server
from kr_gov_job_mcp.tools import create_default_registry


def _run_stdio(messages: list[dict]) -> list[dict]:
    stdin = StringIO("".join(json.dumps(message, ensure_ascii=False) + "\n" for message in messages))
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run_stdio_server(
        create_default_registry(),
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert stderr.getvalue() == ""
    return [json.loads(line) for line in stdout.getvalue().splitlines()]


def test_mcp_stdio_initialize_and_list_tools() -> None:
    responses = _run_stdio(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25"},
            },
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
            },
        ]
    )

    assert len(responses) == 2
    assert responses[0]["id"] == 1
    assert responses[0]["result"]["protocolVersion"] == "2025-11-25"
    assert responses[0]["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert responses[0]["result"]["serverInfo"]["name"] == "kr-gov-job-mcp"
    tools = responses[1]["result"]["tools"]
    assert {tool["name"] for tool in tools} >= {
        "health_check",
        "lookup_region_codes",
        "search_public_jobs",
        "fetch_job_detail",
        "analyze_job_fit_report",
        "analyze_institution_strategy",
        "analyze_institution_weakness",
        "normalize_job_role",
        "prepare_institution_interview",
    }
    lookup = next(tool for tool in tools if tool["name"] == "lookup_region_codes")
    assert "inputSchema" in lookup
    assert "input_schema" not in lookup


def test_mcp_stdio_call_tool_returns_text_and_structured_content() -> None:
    responses = _run_stdio(
        [
            {
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {
                    "name": "lookup_region_codes",
                    "arguments": {"query": "서울특별시"},
                },
            }
        ]
    )

    result = responses[0]["result"]
    structured = result["structuredContent"]
    text_payload = json.loads(result["content"][0]["text"])
    assert result["isError"] is False
    assert structured == text_payload
    assert structured["matches"][0]["code"] == "R3010"
    assert structured["matches"][0]["name"] == "서울"


def test_mcp_stdio_tool_validation_error_is_tool_result() -> None:
    responses = _run_stdio(
        [
            {
                "jsonrpc": "2.0",
                "id": "bad-call",
                "method": "tools/call",
                "params": {
                    "name": "lookup_region_codes",
                    "arguments": {"unknown": True},
                },
            }
        ]
    )

    result = responses[0]["result"]
    assert result["isError"] is True
    assert "unsupported lookup_region_codes arguments" in result["structuredContent"]["error"]


def test_mcp_stdio_unknown_tool_returns_json_rpc_error() -> None:
    responses = _run_stdio(
        [
            {
                "jsonrpc": "2.0",
                "id": "missing-tool",
                "method": "tools/call",
                "params": {
                    "name": "missing_tool",
                    "arguments": {},
                },
            }
        ]
    )

    assert responses[0]["error"]["code"] == -32602
    assert "unknown tool" in responses[0]["error"]["message"]
