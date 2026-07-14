import pytest

from kr_gov_job_mcp.analysis.alio_institution_context import AlioInstitutionContext
from kr_gov_job_mcp.schemas.institution import (
    InstitutionEvidence,
    InstitutionIdentityCandidate,
    InstitutionSignalCandidate,
)
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
            "job_family": "정보통신",
            "evidence": [
                {
                    "title": "ALIO 주요사업",
                    "source_type": "alio_disclosure",
                    "url": "https://example.test/alio",
                    "excerpt": "디지털 신뢰 기반 조성과 정보보호 산업 지원",
                    "fields": {"source_type": "major_business"},
                }
            ],
        }
    )

    assert result["source"] == "institution_analysis"
    assert result["institution_name"] == "한국인터넷진흥원"
    assert result["normalized_name"] == "한국인터넷진흥원"
    assert result["year"] == 2026
    assert result["job_family"] == "정보통신"
    assert result["strategy_signals"] == [
        {
            "category": "business_direction",
            "summary": "디지털 신뢰 기반 조성과 정보보호 산업 지원",
            "job_connection": (
                "정보통신 관점에서는 이 signal을 주요사업 근거로 삼아 기관이 중점 추진하는 "
                "문제, 필요한 역량, 지원 직무의 기여 가능성을 분리해 검토합니다."
            ),
            "evidence": [
                {
                    "title": "ALIO 주요사업",
                    "source_type": "alio_disclosure",
                    "url": "https://example.test/alio",
                    "source_id": None,
                    "collected_at": None,
                    "evidence_year": None,
                    "disclosed_at": None,
                    "retrieved_at": None,
                    "excerpt": "디지털 신뢰 기반 조성과 정보보호 산업 지원",
                    "fields": {"source_type": "major_business"},
                }
            ],
        }
    ]
    assert not any(note["field"] == "strategy_signals" for note in result["verification_notes"])


def test_analyze_institution_strategy_keeps_missing_evidence_as_verification_notes() -> None:
    tool = create_analyze_institution_strategy_tool()

    result = tool.handler(
        {"institution_name": "한국인터넷진흥원", "year": 2026, "fetch_live_alio": False}
    )

    assert result["strategy_signals"] == []
    fields = {note["field"] for note in result["verification_notes"]}
    assert {"identity_candidates", "evidence", "strategy_signals", "job_family"}.issubset(fields)


def test_analyze_institution_strategy_rejects_invalid_arguments() -> None:
    tool = create_analyze_institution_strategy_tool()

    with pytest.raises(ValueError, match="institution_name is required"):
        tool.handler({})
    with pytest.raises(ValueError, match="institution_name is required"):
        tool.handler({"institution_name": "   "})

    with pytest.raises(ValueError, match="unsupported analyze_institution_strategy arguments"):
        tool.handler({"institution_name": "한국인터넷진흥원", "extra": True})

    with pytest.raises(ValueError, match="expected integer value for year"):
        tool.handler({"institution_name": "한국인터넷진흥원", "year": "올해"})

    with pytest.raises(ValueError, match="Use the Job-ALIO NCS category '정보통신'"):
        tool.handler({"institution_name": "한국인터넷진흥원", "job_family": "정보보안"})


def test_analyze_institution_strategy_uses_live_alio_context(monkeypatch: pytest.MonkeyPatch) -> None:
    tool = create_analyze_institution_strategy_tool()
    evidence = InstitutionEvidence(
        title="ALIO 주요사업",
        source_type="alio_disclosure",
        source_id="2026041303152259",
        url="https://www.alio.go.kr/item/itemReport.do?seq=2026041303152259",
        evidence_year=2026,
        disclosed_at="2026-04-13T00:00:00+00:00",
        retrieved_at="2026-07-14T00:00:00+00:00",
        collected_at="2026-07-14T00:00:00+00:00",
        excerpt="가장 큰 규모는 수탁사업으로 2026년 예산 56,012백만원입니다.",
        fields={"source_type": "major_business", "alio_item_no": "40"},
    )

    def fake_context(
        *, institution_name: str, alio_id: str | None, year: int | None
    ) -> AlioInstitutionContext:
        assert institution_name == "(재)한국보건의료정보원"
        assert alio_id is None
        assert year == 2026
        return AlioInstitutionContext(
            institution_id="C1304",
            institution_name="(재)한국보건의료정보원",
            identity_candidates=[
                InstitutionIdentityCandidate(
                    name="(재)한국보건의료정보원",
                    source_type="alio_disclosure",
                    source_id="C1304",
                    code_type="apbaId",
                    confidence="high",
                )
            ],
            evidence=[evidence],
            signals=[
                InstitutionSignalCandidate(
                    category="business_direction",
                    title="ALIO 주요사업",
                    summary=evidence.excerpt,
                    evidence=[evidence],
                )
            ],
        )

    monkeypatch.setattr(
        "kr_gov_job_mcp.tools.institution_analysis.fetch_alio_institution_context_sync",
        fake_context,
    )

    result = tool.handler(
        {
            "institution_name": "(재)한국보건의료정보원",
            "year": 2026,
            "job_family": "보건의료정보",
        }
    )

    assert result["query"]["alio_id"] == "C1304"
    assert result["strategy_signals"][0]["summary"] == evidence.excerpt
    assert result["strategy_signals"][0]["evidence"][0]["evidence_year"] == 2026
    assert result["strategy_signals"][0]["evidence"][0]["disclosed_at"] == "2026-04-13T00:00:00+00:00"
    assert result["strategy_signals"][0]["evidence"][0]["retrieved_at"] == "2026-07-14T00:00:00+00:00"
    assert result["verification_notes"] == []


def test_analyze_institution_weakness_passes_year_to_live_alio_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    evidence = InstitutionEvidence(
        title="ALIO 국회 지적사항",
        source_type="alio_disclosure",
        evidence_year=2024,
        disclosed_at="2024-05-12T00:00:00+00:00",
        retrieved_at="2026-07-14T00:00:00+00:00",
        collected_at="2026-07-14T00:00:00+00:00",
        excerpt="운영 관리 체계를 개선할 필요가 있습니다.",
        fields={"source_type": "audit_point", "alio_item_no": "47-1"},
    )

    def fake_context(*, institution_name: str, alio_id: str | None, year: int | None) -> AlioInstitutionContext:
        captured.update(institution_name=institution_name, alio_id=alio_id, year=year)
        return AlioInstitutionContext(
            evidence=[evidence],
            signals=[
                InstitutionSignalCandidate(
                    category="improvement_task",
                    title=evidence.title,
                    summary=evidence.excerpt,
                    evidence=[evidence],
                )
            ],
            warnings=["requested-year warning"],
        )

    monkeypatch.setattr(
        "kr_gov_job_mcp.tools.institution_analysis.fetch_alio_institution_context_sync",
        fake_context,
    )

    result = create_analyze_institution_weakness_tool().handler(
        {"institution_name": "한국인터넷진흥원", "year": 2024}
    )

    assert captured == {
        "institution_name": "한국인터넷진흥원",
        "alio_id": None,
        "year": 2024,
    }
    assert result["warnings"] == ["requested-year warning"]
    returned_evidence = result["weakness_signals"][0]["evidence"][0]
    assert returned_evidence["evidence_year"] == 2024
    assert returned_evidence["disclosed_at"] == "2024-05-12T00:00:00+00:00"
    assert returned_evidence["retrieved_at"] == "2026-07-14T00:00:00+00:00"


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
    assert "호출 측 LLM" in result["weakness_signals"][0]["applicant_connection"]


def test_analyze_institution_weakness_classifies_evidence_source_context() -> None:
    tool = create_analyze_institution_weakness_tool()

    result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "year": 2026,
            "evidence": [
                {
                    "title": "경영평가 지적사항",
                    "source_type": "alio_disclosure",
                    "url": "https://example.test/evaluation",
                    "excerpt": "정보보호 서비스 운영 관리 체계 개선 필요",
                    "fields": {"source_type": "management_evaluation"},
                }
            ],
        }
    )

    signal = result["weakness_signals"][0]
    assert signal["category"] == "management_evaluation"
    assert signal["summary"] == "정보보호 서비스 운영 관리 체계 개선 필요"
    assert "평가 의견" in signal["careful_wording"]
    assert signal["evidence"][0]["fields"] == {"source_type": "management_evaluation"}


def test_analyze_institution_weakness_keeps_missing_evidence_as_verification_notes() -> None:
    tool = create_analyze_institution_weakness_tool()

    result = tool.handler(
        {"institution_name": "한국인터넷진흥원", "year": 2026, "fetch_live_alio": False}
    )

    assert result["weakness_signals"] == []
    fields = {note["field"] for note in result["verification_notes"]}
    assert {"identity_candidates", "evidence", "weakness_signals"}.issubset(fields)


def test_analyze_institution_weakness_rejects_invalid_arguments() -> None:
    tool = create_analyze_institution_weakness_tool()

    with pytest.raises(ValueError, match="institution_name is required"):
        tool.handler({})
    with pytest.raises(ValueError, match="institution_name is required"):
        tool.handler({"institution_name": "   "})

    with pytest.raises(ValueError, match="unsupported analyze_institution_weakness arguments"):
        tool.handler({"institution_name": "한국인터넷진흥원", "job_family": "정보보호"})
