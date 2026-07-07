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
_CAREFUL_WORDING = "기관을 단정적으로 비판하지 않고, 원문 근거가 있는 개선 필요 영역으로 표현합니다."
_APPLICANT_CONNECTION = (
    "지원자는 이 개선 과제를 자신의 직무 경험, 문제 해결 방식, 공공성 관점의 기여 포인트와 "
    "연결해 준비할 수 있습니다."
)


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
                reason="개선 과제를 확정할 수 있는 evidence 기반 signal이 없습니다.",
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
                careful_wording=_CAREFUL_WORDING,
                applicant_connection=_APPLICANT_CONNECTION,
                evidence=signal.evidence,
            )
        )
    return weakness_signals


def _signal_from_evidence(evidence: InstitutionEvidence) -> InstitutionWeaknessSignal:
    return InstitutionWeaknessSignal(
        category="improvement_task",
        summary=evidence.excerpt or evidence.title,
        careful_wording=_CAREFUL_WORDING,
        applicant_connection=_APPLICANT_CONNECTION,
        evidence=[evidence],
    )


def _has_usable_text(evidence: InstitutionEvidence) -> bool:
    return bool((evidence.excerpt or evidence.title).strip())
