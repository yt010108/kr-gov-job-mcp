import json
from io import StringIO

from kr_gov_job_mcp.server import build_parser, main, run_command
from kr_gov_job_mcp.tools import create_default_registry


def test_server_health_command_outputs_json(capsys) -> None:
    exit_code = main(["--health"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == {
        "registered_tools": 8,
        "service": "kr-gov-job-mcp",
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
    assert payload["tools"][5]["name"] == "lookup_job_alio_codes"
    assert payload["tools"][6]["name"] == "lookup_region_codes"
    assert payload["tools"][7]["name"] == "search_public_jobs"


def test_server_call_tool_command_outputs_result(capsys) -> None:
    exit_code = main(["--call-tool", "health_check", "--input", "{}"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["status"] == "ok"


def test_server_cli_calls_institution_analysis_without_evidence(capsys) -> None:
    exit_code = main(
        [
            "--call-tool",
            "analyze_institution_strategy",
            "--input",
            json.dumps(
                {
                    "institution_name": "한국인터넷진흥원",
                    "year": 2026,
                    "job_family": "정보보호",
                    "fetch_live_alio": False,
                },
                ensure_ascii=False,
            ),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["strategy_signals"] == []
    assert {note["field"] for note in payload["verification_notes"]}.issuperset(
        {"identity_candidates", "evidence", "strategy_signals"}
    )


def test_server_cli_calls_institution_weakness_with_evidence(capsys) -> None:
    exit_code = main(
        [
            "--call-tool",
            "analyze_institution_weakness",
            "--input",
            json.dumps(
                {
                    "institution_name": "한국인터넷진흥원",
                    "year": 2026,
                    "evidence": [
                        {
                            "title": "국회 지적사항",
                            "source_type": "alio_disclosure",
                            "url": "https://example.test/audit",
                            "excerpt": "정보보호 서비스 운영 체계의 개선 필요성이 지적되었다.",
                            "fields": {"source_type": "audit_point"},
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["weakness_signals"][0]["category"] == "improvement_task"
    assert payload["weakness_signals"][0]["evidence"][0]["fields"] == {"source_type": "audit_point"}


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
