import json

from kr_gov_job_mcp.server import main


def test_server_health_command_outputs_json(capsys) -> None:
    exit_code = main(["--health"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == {
        "registered_tools": 5,
        "service": "kr-gov-job-mcp",
        "status": "ok",
        "version": "0.1.0",
    }


def test_server_list_tools_command_outputs_registered_tools(capsys) -> None:
    exit_code = main(["--list-tools"])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["tools"][0]["name"] == "analyze_job_fit_report"
    assert payload["tools"][1]["name"] == "fetch_job_detail"
    assert payload["tools"][2]["name"] == "health_check"
    assert payload["tools"][3]["name"] == "lookup_region_codes"
    assert payload["tools"][4]["name"] == "search_public_jobs"


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
