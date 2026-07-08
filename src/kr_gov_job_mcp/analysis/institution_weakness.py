"""Generate conservative institution improvement reports from evidence candidates."""

from __future__ import annotations

from kr_gov_job_mcp.schemas.institution import (
    InstitutionAnalysisInput,
    InstitutionEvidence,
    InstitutionSignalCandidate,
    InstitutionVerificationNote,
    InstitutionWeaknessReport,
    InstitutionWeaknessSignal,
)


_WEAKNESS_CATEGORIES = {
    "improvement_task",
    "financial_or_operational",
    "management_evaluation",
}
_CAREFUL_WORDING_BY_CATEGORY = {
    "improvement_task": "기관을 단정적으로 비판하지 않고, 원문 근거가 있는 개선 필요 영역으로 표현합니다.",
    "financial_or_operational": "수치나 운영 상태를 과장하지 않고, 원문에서 확인되는 재무/운영 관리 이슈로 표현합니다.",
    "management_evaluation": "평가 의견을 기관 전체의 확정적 약점으로 단정하지 않고, 평가 문맥의 개선 과제로 표현합니다.",
}
_APPLICANT_CONNECTION_BY_CATEGORY = {
    "improvement_task": (
        "호출 측 LLM은 이 개선 과제의 원문 근거와 지원자 경험을 연결해 면접 답변용 문장으로 "
        "재구성합니다."
    ),
    "financial_or_operational": (
        "호출 측 LLM은 재무/운영 signal을 지원 직무의 관리, 효율화, 리스크 대응 경험과 "
        "연결할지 판단합니다."
    ),
    "management_evaluation": (
        "호출 측 LLM은 평가 의견의 근거와 지원 직무 맥락을 분리해 후속 질문 또는 답변 소재로 "
        "재가공합니다."
    ),
}
_MANAGEMENT_EVALUATION_HINTS = {
    "management_evaluation",
    "evaluation",
    "management_assessment",
    "경영평가",
    "평가",
}
_FINANCIAL_OR_OPERATIONAL_HINTS = {
    "financial_or_operational",
    "financial",
    "operation",
    "operational",
    "debt",
    "budget",
    "재무",
    "운영",
    "부채",
}


def generate_institution_weakness_report(
    analysis_input: InstitutionAnalysisInput,
    *,
    year: int | None = None,
) -> InstitutionWeaknessReport:
    """Return only weakness or improvement signals backed by explicit evidence."""

    verification_notes = list(analysis_input.verification_notes)
    weakness_signals = _signals_from_candidates(analysis_input.signals)

    if not weakness_signals and analysis_input.evidence:
        weakness_signals = [
            _signal_from_evidence(evidence)
            for evidence in analysis_input.evidence
            if _has_usable_text(evidence)
        ]

    if not weakness_signals:
        verification_notes.append(
            InstitutionVerificationNote(
                field="weakness_signals",
                reason="입력 evidence 또는 evidence가 연결된 signals가 없어 개선 과제 signal을 만들 수 없습니다.",
                suggested_check="ALIO 국회 지적사항, 경영평가, 감사 자료, Cleaneye 평가 evidence를 연결합니다.",
            )
        )

    return InstitutionWeaknessReport(
        institution_name=analysis_input.institution_name,
        normalized_name=analysis_input.normalized_name,
        year=year,
        weakness_signals=weakness_signals,
        verification_notes=verification_notes,
    )


def _signals_from_candidates(
    signals: list[InstitutionSignalCandidate],
) -> list[InstitutionWeaknessSignal]:
    weakness_signals: list[InstitutionWeaknessSignal] = []
    for signal in signals:
        if signal.category not in _WEAKNESS_CATEGORIES:
            continue
        if not signal.evidence:
            continue
        weakness_signals.append(
            InstitutionWeaknessSignal(
                category=signal.category,
                summary=signal.summary or signal.title,
                careful_wording=_careful_wording(signal.category),
                applicant_connection=_applicant_connection(signal.category),
                evidence=signal.evidence,
            )
        )
    return weakness_signals


def _signal_from_evidence(evidence: InstitutionEvidence) -> InstitutionWeaknessSignal:
    category = _category_from_evidence(evidence)
    return InstitutionWeaknessSignal(
        category=category,
        summary=evidence.excerpt or evidence.title,
        careful_wording=_careful_wording(category),
        applicant_connection=_applicant_connection(category),
        evidence=[evidence],
    )


def _category_from_evidence(evidence: InstitutionEvidence) -> str:
    source_text = _evidence_source_text(evidence)
    if _has_any_hint(source_text, _MANAGEMENT_EVALUATION_HINTS):
        return "management_evaluation"
    if _has_any_hint(source_text, _FINANCIAL_OR_OPERATIONAL_HINTS):
        return "financial_or_operational"
    return "improvement_task"


def _evidence_source_text(evidence: InstitutionEvidence) -> str:
    values: list[str] = [evidence.title, evidence.source_type]
    for key in ("source_type", "source_category", "section_type", "item_type", "report_type"):
        value = evidence.fields.get(key)
        if isinstance(value, str):
            values.append(value)
    return " ".join(values).lower()


def _has_any_hint(text: str, hints: set[str]) -> bool:
    return any(hint.lower() in text for hint in hints)


def _careful_wording(category: str) -> str:
    return _CAREFUL_WORDING_BY_CATEGORY[category]


def _applicant_connection(category: str) -> str:
    return _APPLICANT_CONNECTION_BY_CATEGORY[category]


def _has_usable_text(evidence: InstitutionEvidence) -> bool:
    return bool((evidence.excerpt or evidence.title).strip())
