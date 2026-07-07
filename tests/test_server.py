import json
from io import StringIO

from kr_gov_job_mcp.server import build_parser, main, run_command
from kr_gov_job_mcp.tools import create_default_registry


def test_server_health_command_outputs_json(capsys) -> None:
    exit_code = main(["--health"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == {
        "registered_tools": 7,
        "revision": "unknown",
        "service": "kr-gov-job-mcp",
        "source_ref": "unknown",
        "status": "ok",
        "version": "0.1.0",
    }


def test_server_list_tools_command_outputs_registered_tools(capsys) -> None:
    exit_code = main(["--list-tools"])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["tools"][0]["name"] == "analyze_institution_strategy"
    assert payload["tools"][1]["name"] == "analyze_institution_weakness"
    assert payload["tools"][2]["name"] == "analyze_job_fit_report"
    assert payload["tools"][3]["name"] == "fetch_job_detail"
    assert payload["tools"][4]["name"] == "health_check"
    assert payload["tools"][5]["name"] == "lookup_region_codes"
    assert payload["tools"][6]["name"] == "search_public_jobs"


def test_server_call_tool_command_outputs_result(capsys) -> None:
    exit_code = main(["--call-tool", "health_check", "--input", "{}"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["status"] == "ok"


def test_server_call_tool_rejects_non_object_input(capsys) -> None:
    exit_code = main(["--call-tool", "health_check", "--input", "[]"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--input must be a JSON object" in captured.err


def test_server_stdio_command_uses_mcp_transport() -> None:
    args = build_parser().parse_args(["--stdio"])
    stdin = StringIO(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "health_check", "arguments": {}},
            }
        )
        + "\n"
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run_command(
        args,
        registry=create_default_registry(),
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )

    response = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert response["id"] == 1
    assert response["result"]["structuredContent"]["status"] == "ok"
