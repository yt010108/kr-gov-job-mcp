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
_SOURCE_CONTEXTS = {
    "major_business": "주요사업",
    "business_report": "사업보고서",
    "homepage_business": "기관 홈페이지 사업 소개",
    "policy_research": "연구/정책 자료",
    "job_notice": "채용공고",
}


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
                job_connection=_job_connection(job_family, signal.evidence),
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
        category=_category_from_evidence(evidence),
        summary=summary,
        job_connection=_job_connection(job_family, [evidence]),
        evidence=[evidence],
    )


def _category_from_evidence(evidence: InstitutionEvidence) -> str:
    category = evidence.fields.get("signal_category")
    if category in _STRATEGY_CATEGORIES:
        return str(category)
    return "business_direction"


def _job_connection(job_family: str | None, evidence: list[InstitutionEvidence]) -> str | None:
    if job_family is None:
        return None
    source_context = _source_context(evidence)
    return (
        f"{job_family} 관점에서는 이 signal을 {source_context} 근거로 삼아 기관이 중점 추진하는 "
        "문제, 필요한 역량, 지원 직무의 기여 가능성을 분리해 검토합니다."
    )


def _source_context(evidence: list[InstitutionEvidence]) -> str:
    for item in evidence:
        source_hint = item.fields.get("source_type") or item.fields.get("source_category")
        if isinstance(source_hint, str) and source_hint in _SOURCE_CONTEXTS:
            return _SOURCE_CONTEXTS[source_hint]
    return "원문 evidence"


def _has_usable_text(evidence: InstitutionEvidence) -> bool:
    return bool((evidence.excerpt or evidence.title).strip())
