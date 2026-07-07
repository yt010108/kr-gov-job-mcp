import pytest

from kr_gov_job_mcp.tools.institution_analysis import (
    create_analyze_institution_strategy_tool,
    create_analyze_institution_weakness_tool,
)


def test_analyze_institution_strategy_returns_evidence_backed_signal() -> None:
    tool = create_analyze_institution_strategy_tool()

    result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "year": 2026,
            "job_family": "정보보호",
            "evidence": [
                {
                    "title": "ALIO 주요사업",
                    "source_type": "alio_disclosure",
                    "url": "https://example.test/alio",
                    "excerpt": "디지털 신뢰 기반 조성과 정보보호 산업 지원",
                }
            ],
        }
    )

    assert result["source"] == "institution_analysis"
    assert result["institution_name"] == "한국인터넷진흥원"
    assert result["normalized_name"] == "한국인터넷진흥원"
    assert result["year"] == 2026
    assert result["job_family"] == "정보보호"
    assert result["strategy_signals"] == [
        {
            "category": "business_direction",
            "summary": "디지털 신뢰 기반 조성과 정보보호 산업 지원",
            "job_connection": (
                "정보보호 직무 준비에서는 이 사업 방향을 지원자의 경험, 기술 역량, "
                "기관 이해 근거와 연결해 설명할 수 있습니다."
            ),
            "evidence": [
                {
                    "title": "ALIO 주요사업",
                    "source_type": "alio_disclosure",
                    "url": "https://example.test/alio",
                    "source_id": None,
                    "collected_at": None,
                    "excerpt": "디지털 신뢰 기반 조성과 정보보호 산업 지원",
                    "fields": {},
                }
            ],
        }
    ]
    assert not any(note["field"] == "strategy_signals" for note in result["verification_notes"])


def test_analyze_institution_strategy_keeps_missing_evidence_as_verification_notes() -> None:
    tool = create_analyze_institution_strategy_tool()

    result = tool.handler({"institution_name": "한국인터넷진흥원", "year": 2026})

    assert result["strategy_signals"] == []
    fields = {note["field"] for note in result["verification_notes"]}
    assert {"identity_candidates", "evidence", "strategy_signals", "job_family"}.issubset(fields)


def test_analyze_institution_strategy_rejects_invalid_arguments() -> None:
    tool = create_analyze_institution_strategy_tool()

    with pytest.raises(ValueError, match="institution_name is required"):
        tool.handler({})

    with pytest.raises(ValueError, match="unsupported analyze_institution_strategy arguments"):
        tool.handler({"institution_name": "한국인터넷진흥원", "extra": True})

    with pytest.raises(ValueError, match="expected integer value for year"):
        tool.handler({"institution_name": "한국인터넷진흥원", "year": "올해"})


def test_analyze_institution_weakness_returns_careful_evidence_backed_signal() -> None:
    tool = create_analyze_institution_weakness_tool()

    result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "year": 2026,
            "signals": [
                {
                    "category": "improvement_task",
                    "title": "개선 과제",
                    "summary": "보안 운영 체계 고도화 필요",
                    "evidence": [
                        {
                            "title": "ALIO 국회 지적사항",
                            "source_type": "alio_disclosure",
                            "url": "https://example.test/alio",
                            "excerpt": "보안 운영 체계 고도화 필요",
                        }
                    ],
                }
            ],
        }
    )

    assert result["source"] == "institution_analysis"
    assert result["institution_name"] == "한국인터넷진흥원"
    assert result["year"] == 2026
    assert result["weakness_signals"][0]["category"] == "improvement_task"
    assert result["weakness_signals"][0]["summary"] == "보안 운영 체계 고도화 필요"
    assert "단정적으로 비판하지 않고" in result["weakness_signals"][0]["careful_wording"]
    assert "기여 포인트" in result["weakness_signals"][0]["applicant_connection"]


def test_analyze_institution_weakness_keeps_missing_evidence_as_verification_notes() -> None:
    tool = create_analyze_institution_weakness_tool()

    result = tool.handler({"institution_name": "한국인터넷진흥원", "year": 2026})

    assert result["weakness_signals"] == []
    fields = {note["field"] for note in result["verification_notes"]}
    assert {"identity_candidates", "evidence", "weakness_signals"}.issubset(fields)


def test_analyze_institution_weakness_rejects_invalid_arguments() -> None:
    tool = create_analyze_institution_weakness_tool()

    with pytest.raises(ValueError, match="institution_name is required"):
        tool.handler({})

    with pytest.raises(ValueError, match="unsupported analyze_institution_weakness arguments"):
        tool.handler({"institution_name": "한국인터넷진흥원", "job_family": "정보보호"})
