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
    assert result["weakness_signals"][0]["risk_area"] == "국회 지적"
    assert result["weakness_signals"][0]["severity"] == "high"
    assert "반드시 잘못했다" in result["weakness_signals"][0]["do_not_say"]
    assert "면접에서는" in result["weakness_signals"][0]["interview_safe_answer"]


def test_analyze_institution_weakness_prioritizes_audit_before_management_eval() -> None:
    tool = create_analyze_institution_weakness_tool()

    result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "year": 2026,
            "evidence": [
                {
                    "title": "경영평가 개선 권고",
                    "source_type": "cleaneye",
                    "url": "https://example.test/eval",
                    "fields": {"year": 2026},
                    "excerpt": "경영평가 성과관리 지표 환류 개선 필요",
                },
                {
                    "title": "감사결과",
                    "source_type": "alio_disclosure",
                    "url": "https://example.test/audit",
                    "fields": {"year": 2026},
                    "excerpt": "감사결과 접근권한 관리 미흡 사항에 대한 시정 요구",
                },
            ],
        }
    )

    first, second = result["weakness_signals"]
    assert first["priority"] == 1
    assert first["risk_area"] == "감사 지적"
    assert first["severity"] == "high"
    assert first["evidence_strength"] == "high"
    assert "조치 결과" in " ".join(first["follow_up_checks"])
    assert second["priority"] == 2
    assert second["risk_area"] == "경영평가 개선 필요"
    assert second["severity"] == "medium"
    assert "평가등급 자체를 과장하지 않고" in second["careful_wording"]


def test_analyze_institution_weakness_limits_financial_claims_without_numbers() -> None:
    tool = create_analyze_institution_weakness_tool()

    result = tool.handler(
        {
            "institution_name": "샘플기관",
            "evidence": [
                {
                    "title": "수동 메모",
                    "source_type": "manual",
                    "excerpt": "부채 관리 개선 필요",
                }
            ],
        }
    )

    signal = result["weakness_signals"][0]
    assert signal["risk_area"] == "재무/부채 리스크"
    assert signal["needs_verification"] is True
    assert "원문 수치와 기준 연도" in signal["careful_wording"]
    assert "부채가 심각하다" in signal["do_not_say"]
    assert "재무/부채 관련 수치" in " ".join(signal["follow_up_checks"])
    assert any(note["field"] == "weakness_signals.needs_verification" for note in result["verification_notes"])


def test_analyze_institution_weakness_avoids_security_incident_assumption() -> None:
    tool = create_analyze_institution_weakness_tool()

    result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "evidence": [
                {
                    "title": "개선 과제",
                    "source_type": "alio_disclosure",
                    "url": "https://example.test/security",
                    "fields": {"year": 2026},
                    "excerpt": "개인정보 접근권한 점검과 보안 통제 체계 개선 필요",
                }
            ],
        }
    )

    signal = result["weakness_signals"][0]
    assert signal["risk_area"] == "보안/개인정보/정보보호"
    assert signal["severity"] == "high"
    assert "사고 발생을 단정하지 않고" in signal["careful_wording"]
    assert "개인정보 유출이 있었다" in signal["do_not_say"]
    assert "보안 점검 자동화" in signal["applicant_connection"]


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
