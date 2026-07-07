"""Generate conservative institution strategy reports from evidence candidates."""

from __future__ import annotations

from dataclasses import dataclass

from kr_gov_job_mcp.schemas.institution import (
    InstitutionAnalysisInput,
    InstitutionEvidence,
    InstitutionSignalCandidate,
    InstitutionStrategyReport,
    InstitutionStrategySignal,
    InstitutionVerificationNote,
)


_STRATEGY_CATEGORIES = {"business_direction", "job_connection"}
_SOURCE_WEIGHTS = {
    "alio_disclosure": 40,
    "institution_homepage": 35,
    "cleaneye": 30,
    "job_alio": 25,
    "manual": 20,
}
_STRATEGY_TAXONOMY = {
    "핵심사업 유지/확대": [
        "주요사업",
        "핵심사업",
        "고유사업",
        "확대",
        "강화",
        "추진",
        "운영",
    ],
    "디지털 전환": [
        "디지털",
        "데이터",
        "플랫폼",
        "ai",
        "인공지능",
        "클라우드",
        "자동화",
        "온라인",
        "ict",
    ],
    "정보보호/안전/규제 대응": [
        "정보보호",
        "보안",
        "개인정보",
        "침해",
        "안전",
        "규제",
        "인증",
        "isms",
        "신뢰",
    ],
    "지역/산업 지원": [
        "지역",
        "산업",
        "기업",
        "중소기업",
        "수출",
        "농수산",
        "식품",
        "창업",
        "생태계",
    ],
    "대국민 서비스 개선": [
        "국민",
        "대국민",
        "민원",
        "서비스",
        "고객",
        "이용자",
        "편의",
        "접근성",
    ],
    "정책 집행/공공성 강화": [
        "정책",
        "공공",
        "지원",
        "제도",
        "집행",
        "위탁",
        "기반",
        "안정",
    ],
    "연구개발/기술 고도화": [
        "연구",
        "r&d",
        "기술",
        "고도화",
        "혁신",
        "표준",
    ],
    "ESG/상생/사회적 가치": [
        "esg",
        "상생",
        "사회적",
        "지속가능",
        "탄소",
        "환경",
        "동반성장",
    ],
}
_JOB_FAMILY_KEYWORDS = {
    "정보보호": ["정보보호", "보안", "개인정보", "침해", "isms", "인증", "위험"],
    "전산": ["전산", "시스템", "데이터", "서비스", "자동화", "클라우드", "플랫폼"],
    "사업관리": ["사업관리", "정책", "성과", "이해관계자", "조율", "집행", "운영"],
}


@dataclass(frozen=True)
class _SignalAnalysis:
    strategy_type: str
    keywords: list[str]
    confidence: str
    source_reason: str
    job_relevance: str | None
    interview_talking_point: str | None
    resume_angle: str | None
    needs_verification: bool


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

    strategy_signals = _prioritized(strategy_signals)

    if not strategy_signals:
        verification_notes.append(
            InstitutionVerificationNote(
                field="strategy_signals",
                reason="기관 사업 방향을 확정할 수 있는 evidence 기반 signal이 없습니다.",
                suggested_check="ALIO 주요사업, 기관 홈페이지 사업 소개, Cleaneye 사업보고서 evidence를 연결합니다.",
            )
        )
    elif any(signal.needs_verification for signal in strategy_signals):
        verification_notes.append(
            InstitutionVerificationNote(
                field="strategy_signals.needs_verification",
                reason="일부 사업 방향 signal은 출처 구체성, 최신성 또는 직무 연결 근거가 약합니다.",
                suggested_check="원문 URL, 기준 연도, 기관 공식 자료 excerpt를 보강합니다.",
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
        analysis = _analyze_signal(summary, signal.evidence, job_family, signal.matched_keywords)
        strategy_signals.append(
            InstitutionStrategySignal(
                category=signal.category,
                summary=summary,
                strategy_type=analysis.strategy_type,
                confidence=analysis.confidence,  # type: ignore[arg-type]
                source_reason=analysis.source_reason,
                job_connection=_job_connection(analysis.strategy_type, job_family),
                job_relevance=analysis.job_relevance,
                interview_talking_point=analysis.interview_talking_point,
                resume_angle=analysis.resume_angle,
                keywords=analysis.keywords,
                needs_verification=analysis.needs_verification,
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
    analysis = _analyze_signal(summary, [evidence], job_family)
    return InstitutionStrategySignal(
        category="business_direction",
        summary=summary,
        strategy_type=analysis.strategy_type,
        confidence=analysis.confidence,  # type: ignore[arg-type]
        source_reason=analysis.source_reason,
        job_connection=_job_connection(analysis.strategy_type, job_family),
        job_relevance=analysis.job_relevance,
        interview_talking_point=analysis.interview_talking_point,
        resume_angle=analysis.resume_angle,
        keywords=analysis.keywords,
        needs_verification=analysis.needs_verification,
        evidence=[evidence],
    )


def _prioritized(signals: list[InstitutionStrategySignal]) -> list[InstitutionStrategySignal]:
    ordered = sorted(
        signals,
        key=lambda signal: (
            _confidence_rank(signal.confidence),
            len(signal.keywords),
            _source_weight(signal.evidence),
        ),
        reverse=True,
    )
    for index, signal in enumerate(ordered, start=1):
        signal.priority = index
    return ordered


def _analyze_signal(
    summary: str,
    evidence: list[InstitutionEvidence],
    job_family: str | None,
    extra_keywords: list[str] | None = None,
) -> _SignalAnalysis:
    text = _combined_text(summary, evidence)
    strategy_type, taxonomy_keywords = _classify_strategy(text)
    job_keywords = _matched_job_keywords(text, job_family)
    keywords = _unique_preserve_order([*(extra_keywords or []), *taxonomy_keywords, *job_keywords])
    score = _score_evidence(text, evidence, job_keywords, taxonomy_keywords)
    confidence = _confidence(score)
    source_reason = _source_reason(evidence, taxonomy_keywords)
    job_relevance = _job_relevance(strategy_type, job_family)
    interview_talking_point = _interview_talking_point(strategy_type, summary, job_family)
    resume_angle = _resume_angle(strategy_type, job_family)
    needs_verification = confidence == "low" or _needs_source_verification(evidence, job_keywords, job_family)
    return _SignalAnalysis(
        strategy_type=strategy_type,
        keywords=keywords,
        confidence=confidence,
        source_reason=source_reason,
        job_relevance=job_relevance,
        interview_talking_point=interview_talking_point,
        resume_angle=resume_angle,
        needs_verification=needs_verification,
    )


def _classify_strategy(text: str) -> tuple[str, list[str]]:
    lowered = text.lower()
    best_type = "정책 집행/공공성 강화"
    best_keywords: list[str] = []
    all_keywords: list[str] = []
    for strategy_type, keywords in _STRATEGY_TAXONOMY.items():
        matched = [keyword for keyword in keywords if keyword.lower() in lowered]
        all_keywords.extend(matched)
        if len(matched) > len(best_keywords):
            best_type = strategy_type
            best_keywords = matched
    return best_type, _unique_preserve_order(all_keywords)


def _score_evidence(
    text: str,
    evidence: list[InstitutionEvidence],
    job_keywords: list[str],
    taxonomy_keywords: list[str],
) -> int:
    score = max((_SOURCE_WEIGHTS.get(item.source_type, 15) for item in evidence), default=0)
    if any(item.collected_at or item.fields.get("year") or item.fields.get("base_year") for item in evidence):
        score += 10
    if len(text.strip()) >= 40:
        score += 10
    if len(text.strip()) >= 90:
        score += 10
    if job_keywords:
        score += 10
    score += min(len(taxonomy_keywords) * 3, 15)
    return min(score, 100)


def _confidence(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _confidence_rank(confidence: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(confidence, 0)


def _source_weight(evidence: list[InstitutionEvidence]) -> int:
    return max((_SOURCE_WEIGHTS.get(item.source_type, 15) for item in evidence), default=0)


def _source_reason(
    evidence: list[InstitutionEvidence],
    taxonomy_keywords: list[str],
) -> str:
    if not evidence:
        return "연결된 원문 근거가 없어 우선순위를 낮게 산정했습니다."
    best = max(evidence, key=lambda item: _SOURCE_WEIGHTS.get(item.source_type, 15))
    keyword_text = ", ".join(taxonomy_keywords[:4]) if taxonomy_keywords else "명시 키워드 부족"
    return (
        f"{best.source_type} 출처의 '{best.title}' 근거를 우선 반영했고, "
        f"분류 키워드({keyword_text})와 구체성을 기준으로 신뢰도를 산정했습니다."
    )


def _needs_source_verification(
    evidence: list[InstitutionEvidence],
    job_keywords: list[str],
    job_family: str | None,
) -> bool:
    if not evidence:
        return True
    if any(item.source_type == "manual" for item in evidence):
        return True
    if any(not _has_usable_text(item) for item in evidence):
        return True
    return bool(job_family and not job_keywords)


def _matched_job_keywords(text: str, job_family: str | None) -> list[str]:
    if job_family is None:
        return []
    lowered = text.lower()
    normalized_family = job_family.strip().lower()
    keywords = _JOB_FAMILY_KEYWORDS.get(job_family.strip(), [normalized_family])
    return [keyword for keyword in keywords if keyword.lower() in lowered]


def _job_connection(strategy_type: str, job_family: str | None) -> str | None:
    if job_family is None:
        return None
    relevance = _job_relevance(strategy_type, job_family)
    if relevance:
        return relevance
    return (
        f"{job_family} 직무 준비에서는 이 사업 방향을 지원자의 경험, 기술 역량, "
        "기관 이해 근거와 연결해 설명할 수 있습니다."
    )


def _job_relevance(strategy_type: str, job_family: str | None) -> str | None:
    if job_family is None:
        return None
    normalized = job_family.strip()
    if normalized == "정보보호":
        return (
            f"{strategy_type} 방향을 개인정보 보호, 침해 대응, 보안 거버넌스, "
            "ISMS-P 운영 관점의 기여와 연결할 수 있습니다."
        )
    if normalized == "전산":
        return (
            f"{strategy_type} 방향을 시스템 안정성, 데이터 활용, 자동화, 클라우드 운영 "
            "역량과 연결할 수 있습니다."
        )
    if normalized == "사업관리":
        return (
            f"{strategy_type} 방향을 정책 집행, 성과관리, 이해관계자 조율, 일정과 리스크 "
            "관리 경험과 연결할 수 있습니다."
        )
    return (
        f"{normalized} 직무에서는 {strategy_type} 방향을 지원자의 실무 경험과 기관 이해 "
        "근거에 맞춰 연결할 수 있습니다."
    )


def _interview_talking_point(
    strategy_type: str,
    summary: str,
    job_family: str | None,
) -> str | None:
    if job_family is None:
        return None
    return (
        f"면접에서는 '{_shorten(summary)}' 근거를 바탕으로 기관의 {strategy_type} 흐름을 "
        f"이해했고, {job_family} 직무에서 어떤 방식으로 실행력을 보탤지 말할 수 있습니다."
    )


def _resume_angle(strategy_type: str, job_family: str | None) -> str | None:
    if job_family is None:
        return None
    return (
        f"자기소개서에서는 {strategy_type}에 맞춰 {job_family} 관련 경험의 문제 상황, "
        "구체적 행동, 공공서비스 기여 결과를 연결하는 구성이 안전합니다."
    )


def _combined_text(summary: str, evidence: list[InstitutionEvidence]) -> str:
    parts = [summary]
    for item in evidence:
        parts.extend([item.title, item.excerpt or ""])
        parts.extend(str(value) for value in item.fields.values() if value is not None)
    return " ".join(parts)


def _shorten(text: str, limit: int = 48) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _has_usable_text(evidence: InstitutionEvidence) -> bool:
    return bool((evidence.excerpt or evidence.title).strip())


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique
