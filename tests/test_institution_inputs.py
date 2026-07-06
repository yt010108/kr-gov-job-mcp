from kr_gov_job_mcp.analysis import (
    normalize_institution_name,
    prepare_institution_analysis_input,
)
from kr_gov_job_mcp.schemas.institution import (
    InstitutionAnalysisInput,
    InstitutionEvidence,
    InstitutionIdentityCandidate,
    InstitutionSignalCandidate,
)


def test_normalize_institution_name_keeps_legal_suffixes() -> None:
    assert normalize_institution_name(" 한국인터넷진흥원 ") == "한국인터넷진흥원"
    assert normalize_institution_name("서울  교통공사") == "서울 교통공사"
    assert normalize_institution_name("한국전력공사 ( 본사 )") == "한국전력공사 (본사)"


def test_prepare_institution_analysis_input_preserves_evidence_and_signals() -> None:
    evidence = InstitutionEvidence(
        title="ALIO 주요사업",
        source_type="alio_disclosure",
        url="https://alio.go.kr/example",
        source_id="C0399",
        excerpt="정보보호와 디지털 신뢰 기반 조성 사업",
        fields={"item": "주요사업"},
    )
    signal = InstitutionSignalCandidate(
        category="business_direction",
        title="디지털 신뢰 기반 조성",
        matched_keywords=["디지털", "정보보호"],
        evidence=[evidence],
    )
    identity = InstitutionIdentityCandidate(
        name="한국인터넷진흥원",
        source_type="alio_disclosure",
        source_id="C0399",
        code_type="apbaId",
        confidence="high",
    )

    prepared = prepare_institution_analysis_input(
        institution_name=" 한국인터넷진흥원 ",
        aliases=["KISA", "한국인터넷진흥원"],
        alio_id="C0399",
        identity_candidates=[identity],
        evidence=[evidence],
        signals=[signal],
    )

    assert InstitutionAnalysisInput.model_validate(prepared.model_dump())
    assert prepared.normalized_name == "한국인터넷진흥원"
    assert prepared.aliases == ["KISA"]
    assert prepared.evidence[0].source_type == "alio_disclosure"
    assert prepared.signals[0].category == "business_direction"
    assert prepared.verification_notes == []


def test_prepare_institution_analysis_input_adds_missing_source_notes() -> None:
    prepared = prepare_institution_analysis_input(institution_name="기관명")

    assert {note.field for note in prepared.verification_notes} == {
        "identity_candidates",
        "evidence",
    }


def test_signal_without_evidence_is_marked_for_verification() -> None:
    signal = InstitutionSignalCandidate(
        category="improvement_task",
        title="운영 개선 과제",
        summary="근거 없는 후보",
    )

    prepared = prepare_institution_analysis_input(
        institution_name="기관명",
        alio_id="C0000",
        evidence=[InstitutionEvidence(title="원문", source_type="manual")],
        signals=[signal],
    )

    assert prepared.verification_notes[0].field == "signals[0].evidence"
