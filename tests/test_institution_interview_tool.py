import pytest

from kr_gov_job_mcp.analysis.alio_institution_context import AlioInstitutionContext
from kr_gov_job_mcp.schemas.institution import InstitutionEvidence, InstitutionSignalCandidate
from kr_gov_job_mcp.tools.institution_analysis import create_prepare_institution_interview_tool


def test_prepare_institution_interview_returns_cards_from_manual_signals() -> None:
    major_business = InstitutionEvidence(
        title="ALIO 주요사업",
        source_type="alio_disclosure",
        excerpt="가장 큰 규모는 디지털 신뢰 기반 조성 사업입니다.",
        fields={"source_type": "major_business", "alio_item_no": "40"},
    )
    audit_point = InstitutionEvidence(
        title="국회 지적사항",
        source_type="alio_disclosure",
        excerpt="정보보호 서비스 운영 체계의 개선 필요성이 지적되었습니다.",
        fields={"source_type": "audit_point", "alio_item_no": "47-1"},
    )
    tool = create_prepare_institution_interview_tool()

    result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "target_role": "정보통신",
            "year": 2026,
            "fetch_live_alio": False,
            "focus_areas": ["지원동기", "개선과제"],
            "evidence": [major_business.model_dump(mode="json"), audit_point.model_dump(mode="json")],
            "signals": [
                {
                    "category": "business_direction",
                    "title": "주요사업",
                    "summary": major_business.excerpt,
                    "evidence": [major_business.model_dump(mode="json")],
                },
                {
                    "category": "improvement_task",
                    "title": "국회 지적사항",
                    "summary": audit_point.excerpt,
                    "evidence": [audit_point.model_dump(mode="json")],
                },
            ],
        }
    )

    assert result["source"] == "institution_interview"
    assert result["query"]["target_role"] == "정보통신"
    assert [card["question_type"] for card in result["interview_cards"]] == ["지원동기", "개선과제"]
    assert result["interview_cards"][0]["evidence"][0]["fields"]["alio_item_no"] == "40"
    assert result["interview_cards"][1]["safe_framing"] is not None
    assert result["warnings"] == []


def test_prepare_institution_interview_uses_live_alio_context(monkeypatch) -> None:
    major_business = InstitutionEvidence(
        title="ALIO 주요사업",
        source_type="alio_disclosure",
        excerpt="가장 큰 규모는 한국보건의료정보원 사업입니다.",
        fields={"source_type": "major_business", "alio_item_no": "40"},
    )
    research = InstitutionEvidence(
        title="보건의료데이터 연구보고서",
        source_type="alio_disclosure",
        excerpt="연구보고서를 직무 관심도 근거로 연결할 수 있습니다.",
        fields={"source_type": "policy_research", "alio_item_no": "50-1"},
    )
    audit_point = InstitutionEvidence(
        title="국회 지적사항",
        source_type="alio_disclosure",
        excerpt="공적 항공 마일리지 사용 현황을 점검하고 관리할 것",
        fields={"source_type": "audit_point", "alio_item_no": "47-1"},
    )

    def fake_fetch_alio_context(*, institution_name: str, alio_id: str | None = None):
        assert institution_name == "(재)한국보건의료정보원"
        assert alio_id is None
        return AlioInstitutionContext(
            institution_id="C1304",
            institution_name="(재)한국보건의료정보원",
            evidence=[major_business, research, audit_point],
            signals=[
                InstitutionSignalCandidate(
                    category="business_direction",
                    title="주요사업",
                    summary=major_business.excerpt,
                    evidence=[major_business],
                ),
                InstitutionSignalCandidate(
                    category="job_connection",
                    title="연구보고서",
                    summary=research.excerpt,
                    evidence=[research],
                ),
                InstitutionSignalCandidate(
                    category="improvement_task",
                    title="국회 지적사항",
                    summary=audit_point.excerpt,
                    evidence=[audit_point],
                ),
            ],
        )

    monkeypatch.setattr(
        "kr_gov_job_mcp.tools.institution_analysis.fetch_alio_institution_context_sync",
        fake_fetch_alio_context,
    )
    tool = create_prepare_institution_interview_tool()

    result = tool.handler(
        {
            "institution_name": "(재)한국보건의료정보원",
            "target_role": "보건의료정보",
            "year": 2026,
            "focus_areas": ["지원동기", "기관이해", "개선과제"],
        }
    )

    assert result["query"]["alio_id"] == "C1304"
    assert [card["question_type"] for card in result["interview_cards"]] == [
        "지원동기",
        "기관 현안 이해",
        "개선과제",
    ]
    assert result["interview_cards"][0]["evidence"][0]["fields"]["source_type"] == "major_business"
    assert result["interview_cards"][1]["evidence"][0]["fields"]["source_type"] == "policy_research"
    assert result["interview_cards"][2]["evidence"][0]["fields"]["source_type"] == "audit_point"


def test_prepare_institution_interview_rejects_invalid_arguments() -> None:
    tool = create_prepare_institution_interview_tool()

    try:
        tool.handler({"institution_name": "한국인터넷진흥원", "target_role": "정보통신", "unknown": True})
    except ValueError as exc:
        assert "unsupported prepare_institution_interview arguments" in str(exc)
    else:
        raise AssertionError("expected invalid argument to be rejected")


def test_prepare_institution_interview_rejects_unsupported_security_role_alias() -> None:
    tool = create_prepare_institution_interview_tool()

    try:
        tool.handler({"institution_name": "한국인터넷진흥원", "target_role": "정보보안"})
    except ValueError as exc:
        assert "prepare_institution_interview does not support target_role='정보보안'" in str(exc)
        assert "Use the Job-ALIO NCS category '정보통신' instead." in str(exc)
    else:
        raise AssertionError("expected unsupported target_role to be rejected")


@pytest.mark.parametrize(
    "role_arguments",
    [
        {"target_role": "정보통신"},
        {"job_family": "정보통신"},
    ],
)
def test_prepare_institution_interview_accepts_each_role_alias(
    role_arguments: dict[str, str],
) -> None:
    tool = create_prepare_institution_interview_tool()

    result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "fetch_live_alio": False,
            **role_arguments,
        }
    )

    assert result["query"]["target_role"] == "정보통신"


def test_prepare_institution_interview_role_alias_contract() -> None:
    tool = create_prepare_institution_interview_tool()

    result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "target_role": "정보통신",
            "job_family": "정보통신",
            "fetch_live_alio": False,
        }
    )

    assert result["query"]["target_role"] == "정보통신"
    with pytest.raises(ValueError, match="institution_name is required"):
        tool.handler({"target_role": "정보통신", "fetch_live_alio": False})
    with pytest.raises(ValueError, match="institution_name is required"):
        tool.handler(
            {"institution_name": "   ", "target_role": "정보통신", "fetch_live_alio": False}
        )
    with pytest.raises(ValueError, match="target_role is required"):
        tool.handler({"institution_name": "한국인터넷진흥원", "fetch_live_alio": False})
    with pytest.raises(ValueError, match="target_role is required"):
        tool.handler(
            {
                "institution_name": "한국인터넷진흥원",
                "job_family": "   ",
                "fetch_live_alio": False,
            }
        )

    preferred_result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "target_role": "정보통신",
            "job_family": "보건의료정보",
            "fetch_live_alio": False,
        }
    )

    assert preferred_result["query"]["target_role"] == "정보통신"
