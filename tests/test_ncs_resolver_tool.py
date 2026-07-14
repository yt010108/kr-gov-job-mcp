import pytest

from kr_gov_job_mcp.schemas.job import JobAlioSearchResult
from kr_gov_job_mcp.tools.code_lookup import create_resolve_ncs_code_tool
from kr_gov_job_mcp.tools.institution_analysis import (
    create_analyze_institution_strategy_tool,
    create_prepare_institution_interview_tool,
)
from kr_gov_job_mcp.tools.public_jobs import create_search_public_jobs_tool


@pytest.mark.parametrize(
    ("query", "expected_name", "expected_code"),
    [
        ("전산", "정보통신", "R600020"),
        ("전산직", "정보통신", "R600020"),
        ("IT", "정보통신", "R600020"),
        ("정보보안", "정보통신", "R600020"),
        ("정보보호", "정보통신", "R600020"),
        ("보안", "정보통신", "R600020"),
        ("네트워크", "정보통신", "R600020"),
        ("개발", "정보통신", "R600020"),
        ("데이터", "정보통신", "R600020"),
        ("전기직", "전기·전자", "R600019"),
        ("전자", "전기·전자", "R600019"),
        ("환경직", "환경·에너지·안전", "R600023"),
        ("안전", "환경·에너지·안전", "R600023"),
        ("사무직", "경영·회계·사무", "R600002"),
        ("행정", "경영·회계·사무", "R600002"),
        ("회계", "경영·회계·사무", "R600002"),
        ("연구직", "연구", "R600025"),
    ],
)
def test_resolve_ncs_code_maps_representative_aliases(
    query: str,
    expected_name: str,
    expected_code: str,
) -> None:
    result = create_resolve_ncs_code_tool().handler({"query": query})

    assert result["selected_ncs_name"] == expected_name
    assert result["selected_ncs_code"] == expected_code
    assert result["confidence"] == 0.92
    assert result["search_public_jobs_arguments"] == {"ncs_code": expected_code}
    assert result["report_context"]["target_role"] == query
    assert result["report_context"]["job_family"] == expected_name
    assert result["warnings"] == []


def test_resolve_ncs_code_preserves_original_role_and_report_context() -> None:
    result = create_resolve_ncs_code_tool().handler(
        {
            "query": "KISA 전산직 공고 찾아줘",
            "target_role": "정보보안",
            "job_family": "정보통신",
        }
    )

    assert result["original_query"] == "KISA 전산직 공고 찾아줘"
    assert result["original_target_role"] == "정보보안"
    assert result["original_job_family"] == "정보통신"
    assert result["selected_ncs_code"] == "R600020"
    assert result["report_context"] == {
        "original_target_role": "정보보안",
        "target_role": "정보보안",
        "original_job_family": "정보통신",
        "job_family": "정보통신",
        "ncs_code": "R600020",
    }


def test_resolve_ncs_code_uses_supporting_inputs_when_role_is_omitted() -> None:
    result = create_resolve_ncs_code_tool().handler({"known_skills": ["전산직"]})

    assert result["resolved_query"] == "전산직"
    assert result["selected_ncs_code"] == "R600020"


def test_report_context_is_accepted_by_prepare_institution_interview() -> None:
    resolved = create_resolve_ncs_code_tool().handler(
        {"target_role": "정보보안", "job_family": "정보통신"}
    )

    result = create_prepare_institution_interview_tool().handler(
        {
            "institution_name": "한국인터넷진흥원",
            "fetch_live_alio": False,
            **resolved["report_context"],
        }
    )

    assert result["target_role"] == "정보보안"
    assert result["query"]["job_family"] == "정보통신"
    assert result["query"]["original_job_family"] == "정보통신"
    assert result["query"]["ncs_code"] == "R600020"


def test_report_context_is_accepted_by_analyze_institution_strategy() -> None:
    resolved = create_resolve_ncs_code_tool().handler(
        {"target_role": "정보보안", "job_family": "정보통신"}
    )

    result = create_analyze_institution_strategy_tool().handler(
        {
            "institution_name": "한국인터넷진흥원",
            "fetch_live_alio": False,
            **resolved["report_context"],
        }
    )

    assert result["query"]["target_role"] == "정보보안"
    assert result["query"]["original_target_role"] == "정보보안"
    assert result["query"]["job_family"] == "정보통신"
    assert result["query"]["original_job_family"] == "정보통신"
    assert result["query"]["ncs_code"] == "R600020"


def test_resolve_ncs_code_returns_candidates_without_selecting_ambiguous_input() -> None:
    result = create_resolve_ncs_code_tool().handler({"query": "기", "limit": 1})

    assert len(result["candidates"]) == 1
    assert result["selected_ncs_code"] is None
    assert result["search_public_jobs_arguments"] == {}
    assert result["recommended_next_calls"][0]["tool"] == "lookup_job_alio_codes"
    assert "확정하지 않았습니다" in result["warnings"][0]


def test_resolve_ncs_code_returns_safe_empty_search_arguments_for_unknown_input() -> None:
    result = create_resolve_ncs_code_tool().handler({"query": "없는직무"})

    assert result["candidates"] == []
    assert result["selected_ncs_code"] is None
    assert result["search_public_jobs_arguments"] == {}
    assert "ncs_code는 비워 둡니다" in result["warnings"][0]


def test_resolve_ncs_code_rejects_invalid_arguments() -> None:
    tool = create_resolve_ncs_code_tool()

    with pytest.raises(ValueError, match="resolve_ncs_code requires"):
        tool.handler({})
    with pytest.raises(ValueError, match="unsupported resolve_ncs_code arguments"):
        tool.handler({"query": "전산직", "extra": True})
    with pytest.raises(ValueError, match="expected list value for known_skills"):
        tool.handler({"known_skills": "전산직"})
    with pytest.raises(ValueError, match="resolve_ncs_code requires"):
        tool.handler({"known_skills": []})


def test_resolved_ncs_code_passes_to_search_public_jobs() -> None:
    captured: dict[str, object] = {}

    def fake_search_jobs(**kwargs: object) -> JobAlioSearchResult:
        captured.update(kwargs)
        return JobAlioSearchResult(page=1, limit=20, total_count=0)

    resolved = create_resolve_ncs_code_tool().handler({"query": "전산직"})
    create_search_public_jobs_tool(search_jobs=fake_search_jobs).handler(
        {**resolved["search_public_jobs_arguments"], "ongoing_only": False}
    )

    assert captured["ncs_code"] == "R600020"
