import pytest

from kr_gov_job_mcp.tools.application_strategy import create_prepare_application_strategy_tool


def _institution(_arguments: object) -> dict[str, object]:
    return {
        "codes": [
            {
                "code": "C0399",
                "name": "한국인터넷진흥원",
                "score": 0.98,
            }
        ]
    }


def _ncs(_arguments: object) -> dict[str, object]:
    return {
        "selected_ncs_code": "R600020",
        "selected_ncs_name": "정보통신",
        "candidates": [],
    }


def _tool(**overrides: object):
    runners = {
        "lookup_institution": _institution,
        "resolve_ncs": _ncs,
        "search_jobs": lambda _arguments: {
            "jobs": [
                {
                    "id": "302001",
                    "institution_name": "한국인터넷진흥원",
                    "title": "정보통신 채용",
                    "source_url": ".",
                }
            ],
            "warnings": [],
            "diagnostics": None,
        },
        "analyze_job_fit": lambda arguments: {
            "job_id": arguments["job_id"],
            "preparation_items": [{"title": "직무기술서 확인"}],
            "evidence_links": [
                {"url": "https://example.test/job/302001", "title": "정보통신 채용"}
            ],
        },
        "map_ncs": lambda arguments: {
            "job_id": arguments["job_id"],
            "knowledge": [{"name": "정보보호 법령"}],
        },
        "analyze_strategy": lambda _arguments: {
            "strategy_signals": [{"title": "디지털 신뢰"}],
            "verification_notes": [],
        },
        "analyze_weakness": lambda _arguments: {
            "weakness_signals": [],
            "verification_notes": [{"field": "evidence", "reason": "근거 확인 필요"}],
        },
        "prepare_interview": lambda _arguments: {
            "interview_cards": [{"question": "지원 동기는 무엇인가요?"}],
        },
    }
    runners.update(overrides)
    return create_prepare_application_strategy_tool(**runners)


def test_prepare_application_strategy_combines_candidate_reports() -> None:
    result = _tool().handler(
        {
            "institution_name": "KISA",
            "target_role": "정보보안",
            "region": "서울",
            "known_skills": ["네트워크"],
            "fetch_live_alio": False,
        }
    )

    assert result["query"]["institution_code"] == "C0399"
    assert result["query"]["ncs_code"] == "R600020"
    assert result["recommended_job_ids"] == ["302001"]
    report = result["application_strategy"]["job_reports"][0]
    assert report["fit_report"]["preparation_items"]
    assert report["ncs"]["knowledge"][0]["name"] == "정보보호 법령"
    assert result["application_strategy"]["institution_strategy"]["strategy_signals"]
    assert result["application_strategy"]["interview_cards"]["interview_cards"]
    assert result["evidence_links"] == [
        {"url": "https://example.test/job/302001", "title": "정보통신 채용"}
    ]


def test_prepare_application_strategy_preserves_zero_result_diagnostics() -> None:
    diagnostics = {
        "reason": "no_results",
        "recommended_next_calls": [{"tool": "search_public_jobs", "arguments": {}}],
    }
    result = _tool(
        search_jobs=lambda _arguments: {
            "jobs": [],
            "warnings": [],
            "diagnostics": diagnostics,
        }
    ).handler({"institution_name": "KISA", "target_role": "정보보안"})

    assert result["job_candidates"] == []
    assert result["diagnostics"] == diagnostics
    assert any(note["field"] == "job_candidates" for note in result["verification_notes"])


def test_prepare_application_strategy_keeps_partial_results_on_analysis_failure() -> None:
    def fail(_arguments: object) -> dict[str, object]:
        raise RuntimeError("ALIO unavailable")

    result = _tool(analyze_strategy=fail).handler(
        {"institution_name": "KISA", "target_role": "정보보안"}
    )

    assert result["job_candidates"][0]["id"] == "302001"
    assert result["application_strategy"]["job_reports"][0]["fit_report"]
    assert result["application_strategy"]["institution_strategy"] == {}
    assert any("institution_strategy" in warning for warning in result["warnings"])


def test_prepare_application_strategy_stops_before_search_when_code_is_ambiguous() -> None:
    result = _tool(
        lookup_institution=lambda _arguments: {"codes": []},
        search_jobs=lambda _arguments: pytest.fail("must not search"),
    ).handler({"institution_name": "알 수 없는 기관", "target_role": "정보보안"})

    assert result["job_candidates"] == []
    assert result["query"]["institution_code"] is None
    assert result["application_strategy"]["institution_strategy"]["strategy_signals"]
    assert result["application_strategy"]["interview_cards"]["interview_cards"]
    assert any(note["field"] == "institution_code" for note in result["verification_notes"])


def test_prepare_application_strategy_keeps_institution_results_when_ncs_is_ambiguous() -> None:
    result = _tool(
        resolve_ncs=lambda _arguments: {
            "selected_ncs_code": None,
            "selected_ncs_name": None,
            "candidates": [{"code": "R600020", "name": "정보통신", "score": 0.68}],
        },
        search_jobs=lambda _arguments: pytest.fail("must not search"),
    ).handler({"institution_name": "KISA", "target_role": "보안 정책 기획"})

    assert result["job_candidates"] == []
    assert result["query"]["ncs_code"] is None
    assert result["application_strategy"]["institution_strategy"]["strategy_signals"]
    assert result["application_strategy"]["institution_weakness"]["verification_notes"]
    assert result["application_strategy"]["interview_cards"]["interview_cards"]
    assert any(note["field"] == "ncs_code" for note in result["verification_notes"])


def test_prepare_application_strategy_rejects_invalid_input() -> None:
    tool = _tool()

    with pytest.raises(ValueError, match="institution_name is required"):
        tool.handler({"target_role": "정보보안"})
    with pytest.raises(ValueError, match="unsupported prepare_application_strategy arguments"):
        tool.handler({"institution_name": "KISA", "target_role": "정보보안", "extra": True})
