"""Generate conservative institution strategy reports from evidence candidates."""

from __future__ import annotations

from kr_gov_job_mcp.schemas.institution import (
    InstitutionAnalysisInput,
    InstitutionEvidence,
    InstitutionSignalCandidate,
    InstitutionStrategyReport,
    InstitutionStrategySignal,
    InstitutionVerificationNote,
)


_STRATEGY_CATEGORIES = {"business_direction", "job_connection"}


def generate_institution_strategy_report(
    analysis_input: InstitutionAnalysisInput,
    *,
    year: int | None = None,
    job_family: str | None = None,
) -> InstitutionStrategyReport:
    """Return only strategy signals backed by explicit evidence."""

    verification_notes = list(analysis_input.verification_notes)
    strategy_signals = _signals_from_candidates(analysis_input.signals, job_family=job_family)

    if not strategy_signals and analysis_input.evidence:
        strategy_signals = [
            _signal_from_evidence(evidence, job_family=job_family)
            for evidence in analysis_input.evidence
            if _has_usable_text(evidence)
        ]

    if not strategy_signals:
        verification_notes.append(
            InstitutionVerificationNote(
                field="strategy_signals",
                reason="기관 사업 방향을 확정할 수 있는 evidence 기반 signal이 없습니다.",
                suggested_check="ALIO 주요사업, 기관 홈페이지 사업 소개, Cleaneye 사업보고서 evidence를 연결합니다.",
            )
        )

    if job_family is None:
        verification_notes.append(
            InstitutionVerificationNote(
                field="job_family",
                reason="직무군이 없어 사업 방향과 직무 연결 포인트를 좁히기 어렵습니다.",
                suggested_check="지원하려는 직무군을 입력합니다. 예: 정보보호, 전산, 사업관리",
            )
        )

    return InstitutionStrategyReport(
        institution_name=analysis_input.institution_name,
        normalized_name=analysis_input.normalized_name,
        year=year,
        job_family=job_family,
        strategy_signals=strategy_signals,
        verification_notes=verification_notes,
    )


def _signals_from_candidates(
    signals: list[InstitutionSignalCandidate],
    *,
    job_family: str | None,
) -> list[InstitutionStrategySignal]:
    strategy_signals: list[InstitutionStrategySignal] = []
    for signal in signals:
        if signal.category not in _STRATEGY_CATEGORIES:
            continue
        if not signal.evidence:
            continue
        summary = signal.summary or signal.title
        strategy_signals.append(
            InstitutionStrategySignal(
                category=signal.category,
                summary=summary,
                job_connection=_job_connection(summary, job_family),
                evidence=signal.evidence,
            )
        )
    return strategy_signals


def _signal_from_evidence(
    evidence: InstitutionEvidence,
    *,
    job_family: str | None,
) -> InstitutionStrategySignal:
    summary = evidence.excerpt or evidence.title
    return InstitutionStrategySignal(
        category="business_direction",
        summary=summary,
        job_connection=_job_connection(summary, job_family),
        evidence=[evidence],
    )


def _job_connection(summary: str, job_family: str | None) -> str | None:
    if job_family is None:
        return None
    return (
        f"{job_family} 직무 준비에서는 이 사업 방향을 지원자의 경험, 기술 역량, "
        "기관 이해 근거와 연결해 설명할 수 있습니다."
    )


def _has_usable_text(evidence: InstitutionEvidence) -> bool:
    return bool((evidence.excerpt or evidence.title).strip())
