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
        "prepare_institution_interview",
    }
    lookup = next(tool for tool in tools if tool["name"] == "lookup_region_codes")
    assert "inputSchema" in lookup
    assert "input_schema" not in lookup
    assert lookup["annotations"] == {
        "title": "Lookup Region Codes",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
    assert "kr-gov-job-mcp" in lookup["description"]
    _assert_issue_112_input_schemas(tools)


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


def test_mcp_stdio_tool_domain_error_is_tool_result() -> None:
    responses = _run_stdio(
        [
            {
                "jsonrpc": "2.0",
                "id": "bad-role",
                "method": "tools/call",
                "params": {
                    "name": "prepare_institution_interview",
                    "arguments": {"institution_name": "한국인터넷진흥원", "target_role": "정보보안"},
                },
            }
        ]
    )

    result = responses[0]["result"]
    assert result["isError"] is True
    assert "prepare_institution_interview does not support target_role='정보보안'" in result[
        "structuredContent"
    ]["error"]
    assert "정보통신" in result["structuredContent"]["error"]


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
