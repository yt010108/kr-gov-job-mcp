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
    signal = result["strategy_signals"][0]
    assert signal["category"] == "business_direction"
    assert signal["summary"] == "디지털 신뢰 기반 조성과 정보보호 산업 지원"
    assert signal["strategy_type"] == "정보보호/안전/규제 대응"
    assert signal["priority"] == 1
    assert signal["confidence"] == "high"
    assert "alio_disclosure" in signal["source_reason"]
    assert "ISMS-P" in signal["job_connection"]
    assert "면접에서는" in signal["interview_talking_point"]
    assert "자기소개서에서는" in signal["resume_angle"]
    assert {"디지털", "정보보호", "신뢰"}.issubset(set(signal["keywords"]))
    assert signal["needs_verification"] is False
    assert signal["evidence"][0]["source_type"] == "alio_disclosure"
    assert not any(note["field"] == "strategy_signals" for note in result["verification_notes"])


def test_analyze_institution_strategy_prioritizes_and_links_by_job_family() -> None:
    tool = create_analyze_institution_strategy_tool()

    result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "year": 2026,
            "job_family": "전산",
            "evidence": [
                {
                    "title": "수동 메모",
                    "source_type": "manual",
                    "excerpt": "사회적 가치와 상생 활동",
                },
                {
                    "title": "기관 홈페이지 사업 소개",
                    "source_type": "institution_homepage",
                    "collected_at": "2026-07-08",
                    "excerpt": (
                        "디지털 플랫폼과 데이터 기반 서비스를 고도화하고 클라우드 시스템 "
                        "운영 안정성을 강화한다."
                    ),
                },
            ],
        }
    )

    first, second = result["strategy_signals"]
    assert first["priority"] == 1
    assert first["strategy_type"] == "디지털 전환"
    assert first["confidence"] == "high"
    assert "시스템 안정성" in first["job_relevance"]
    assert first["needs_verification"] is False
    assert second["priority"] == 2
    assert second["strategy_type"] == "ESG/상생/사회적 가치"
    assert second["needs_verification"] is True
    assert any(note["field"] == "strategy_signals.needs_verification" for note in result["verification_notes"])


def test_analyze_institution_strategy_uses_business_management_connection() -> None:
    tool = create_analyze_institution_strategy_tool()

    result = tool.handler(
        {
            "institution_name": "한국농수산식품유통공사",
            "job_family": "사업관리",
            "signals": [
                {
                    "category": "business_direction",
                    "title": "농수산식품 수출 지원",
                    "summary": "농수산식품 산업 수출 지원과 지역 기업 지원 정책 집행 강화",
                    "matched_keywords": ["수출", "지역"],
                    "evidence": [
                        {
                            "title": "ALIO 주요사업",
                            "source_type": "alio_disclosure",
                            "fields": {"year": 2026},
                            "excerpt": "농수산식품 산업 수출 지원과 지역 기업 지원 정책 집행 강화",
                        }
                    ],
                }
            ],
        }
    )

    signal = result["strategy_signals"][0]
    assert signal["strategy_type"] == "지역/산업 지원"
    assert signal["confidence"] == "high"
    assert "성과관리" in signal["job_connection"]
    assert "이해관계자 조율" in signal["job_relevance"]
    assert {"수출", "지역", "산업", "지원"}.issubset(set(signal["keywords"]))


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
