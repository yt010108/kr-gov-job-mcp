"""Generate conservative institution improvement reports from evidence candidates."""

from __future__ import annotations

from dataclasses import dataclass
import re

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
_SOURCE_WEIGHTS = {
    "alio_disclosure": 40,
    "cleaneye": 35,
    "institution_homepage": 25,
    "job_alio": 20,
    "manual": 15,
}
_RISK_TAXONOMY = {
    "감사 지적": ["감사", "감사원", "감사결과", "시정", "주의", "처분"],
    "국회 지적": ["국회", "국정감사", "지적", "질의", "시정요구"],
    "경영평가 개선 필요": ["경영평가", "평가등급", "평가", "성과"],
    "재무/부채 리스크": ["부채", "재무", "손실", "채무", "자본", "수익", "적자"],
    "내부통제": ["내부통제", "통제", "절차", "점검", "준법", "리스크관리"],
    "보안/개인정보/정보보호": ["보안", "개인정보", "정보보호", "침해", "인증", "접근권한"],
    "사업성과/운영 효율": ["사업성과", "운영", "효율", "집행률", "성과관리", "프로세스"],
    "대국민 서비스 품질": ["서비스", "민원", "고객", "이용자", "품질", "접근성"],
    "조달/계약/외주 관리": ["조달", "계약", "외주", "용역", "입찰", "하도급"],
    "조직문화/인력 운영": ["조직문화", "인력", "채용", "교육", "근무", "노무"],
}


@dataclass(frozen=True)
class _WeaknessAnalysis:
    risk_area: str
    severity: str
    evidence_strength: str
    careful_wording: str
    do_not_say: list[str]
    interview_safe_answer: str
    applicant_connection: str
    follow_up_checks: list[str]
    needs_verification: bool


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

    weakness_signals = _prioritized(weakness_signals)

    if not weakness_signals:
        verification_notes.append(
            InstitutionVerificationNote(
                field="weakness_signals",
                reason="개선 과제를 확정할 수 있는 evidence 기반 signal이 없습니다.",
                suggested_check="ALIO 국회 지적사항, 경영평가, 감사 자료, Cleaneye 평가 evidence를 연결합니다.",
            )
        )
    elif any(signal.needs_verification for signal in weakness_signals):
        verification_notes.append(
            InstitutionVerificationNote(
                field="weakness_signals.needs_verification",
                reason="일부 개선 과제는 원문 수치, 기준 연도, 출처 유형 또는 표현 수위 확인이 더 필요합니다.",
                suggested_check="원문 URL, 기준 연도, 수치 근거, 지적사항 원문을 대조합니다.",
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
        summary = signal.summary or signal.title
        analysis = _analyze_signal(summary, signal.evidence)
        weakness_signals.append(
            InstitutionWeaknessSignal(
                category=signal.category,
                summary=summary,
                risk_area=analysis.risk_area,
                severity=analysis.severity,  # type: ignore[arg-type]
                evidence_strength=analysis.evidence_strength,  # type: ignore[arg-type]
                careful_wording=analysis.careful_wording,
                do_not_say=analysis.do_not_say,
                interview_safe_answer=analysis.interview_safe_answer,
                applicant_connection=analysis.applicant_connection,
                follow_up_checks=analysis.follow_up_checks,
                needs_verification=analysis.needs_verification,
                evidence=signal.evidence,
            )
        )
    return weakness_signals


def _signal_from_evidence(evidence: InstitutionEvidence) -> InstitutionWeaknessSignal:
    summary = evidence.excerpt or evidence.title
    analysis = _analyze_signal(summary, [evidence])
    return InstitutionWeaknessSignal(
        category="improvement_task",
        summary=summary,
        risk_area=analysis.risk_area,
        severity=analysis.severity,  # type: ignore[arg-type]
        evidence_strength=analysis.evidence_strength,  # type: ignore[arg-type]
        careful_wording=analysis.careful_wording,
        do_not_say=analysis.do_not_say,
        interview_safe_answer=analysis.interview_safe_answer,
        applicant_connection=analysis.applicant_connection,
        follow_up_checks=analysis.follow_up_checks,
        needs_verification=analysis.needs_verification,
        evidence=[evidence],
    )


def _prioritized(signals: list[InstitutionWeaknessSignal]) -> list[InstitutionWeaknessSignal]:
    ordered = sorted(
        signals,
        key=lambda signal: (
            _severity_rank(signal.severity),
            _strength_rank(signal.evidence_strength),
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
) -> _WeaknessAnalysis:
    text = _combined_text(summary, evidence)
    risk_area, _keywords = _classify_risk(text)
    evidence_strength = _evidence_strength(text, evidence)
    severity = _severity(risk_area, text, evidence_strength)
    financial_without_numbers = risk_area == "재무/부채 리스크" and not _has_number_or_year(text, evidence)
    needs_verification = (
        evidence_strength == "low"
        or financial_without_numbers
        or any(item.source_type == "manual" for item in evidence)
    )
    careful_wording = _careful_wording(risk_area, financial_without_numbers)
    do_not_say = _do_not_say(risk_area, financial_without_numbers)
    follow_up_checks = _follow_up_checks(risk_area, evidence, financial_without_numbers)
    return _WeaknessAnalysis(
        risk_area=risk_area,
        severity=severity,
        evidence_strength=evidence_strength,
        careful_wording=careful_wording,
        do_not_say=do_not_say,
        interview_safe_answer=_interview_safe_answer(risk_area, summary),
        applicant_connection=_applicant_connection(risk_area),
        follow_up_checks=follow_up_checks,
        needs_verification=needs_verification,
    )


def _classify_risk(text: str) -> tuple[str, list[str]]:
    lowered = text.lower()
    best_area = "사업성과/운영 효율"
    best_keywords: list[str] = []
    all_keywords: list[str] = []
    for risk_area, keywords in _RISK_TAXONOMY.items():
        matched = [keyword for keyword in keywords if keyword.lower() in lowered]
        all_keywords.extend(matched)
        if len(matched) > len(best_keywords):
            best_area = risk_area
            best_keywords = matched
    return best_area, _unique_preserve_order(all_keywords)


def _evidence_strength(text: str, evidence: list[InstitutionEvidence]) -> str:
    score = max((_SOURCE_WEIGHTS.get(item.source_type, 10) for item in evidence), default=0)
    if any(item.url for item in evidence):
        score += 10
    if any(item.collected_at or item.fields.get("year") or item.fields.get("base_year") for item in evidence):
        score += 10
    if len(text.strip()) >= 60:
        score += 10
    if _has_number_or_year(text, evidence):
        score += 10
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _severity(risk_area: str, text: str, evidence_strength: str) -> str:
    if risk_area in {"감사 지적", "국회 지적", "보안/개인정보/정보보호"}:
        return "high" if evidence_strength != "low" else "medium"
    if risk_area == "재무/부채 리스크":
        return "high" if _has_number_like_text(text) and evidence_strength != "low" else "medium"
    if risk_area in {"경영평가 개선 필요", "내부통제", "조달/계약/외주 관리"}:
        return "medium"
    return "low" if evidence_strength == "low" else "medium"


def _careful_wording(risk_area: str, financial_without_numbers: bool) -> str:
    if risk_area in {"감사 지적", "국회 지적"}:
        return (
            "기관을 단정적으로 비판하지 않고, 원문에서 확인되는 개선 필요 영역과 후속 관리 "
            "관점으로 표현합니다."
        )
    if risk_area == "경영평가 개선 필요":
        return (
            "평가등급 자체를 과장하지 않고, 평가 근거에서 확인되는 개선 방향과 성과관리 "
            "관점으로 표현합니다."
        )
    if risk_area == "재무/부채 리스크":
        if financial_without_numbers:
            return "원문 수치와 기준 연도가 확인되기 전에는 재무 상태를 단정하지 않습니다."
        return "확인된 수치와 기준 연도 범위 안에서 재무 관리 필요성을 신중하게 표현합니다."
    if risk_area == "보안/개인정보/정보보호":
        return "사고 발생을 단정하지 않고, 예방적 통제와 운영 체계 개선 필요성으로 표현합니다."
    return "기관을 단정적으로 비판하지 않고, 원문 근거가 있는 개선 필요 영역으로 표현합니다."


def _do_not_say(risk_area: str, financial_without_numbers: bool) -> list[str]:
    phrases = ["기관에 문제가 많다", "운영이 부실하다", "비리가 있다"]
    if risk_area in {"감사 지적", "국회 지적"}:
        phrases.extend(["반드시 잘못했다", "심각한 책임 문제가 있다"])
    if risk_area == "경영평가 개선 필요":
        phrases.extend(["평가가 나쁘다", "기관 역량이 부족하다"])
    if risk_area == "재무/부채 리스크" or financial_without_numbers:
        phrases.extend(["재무 상태가 나쁘다", "부채가 심각하다"])
    if risk_area == "보안/개인정보/정보보호":
        phrases.extend(["보안 사고가 발생했다", "개인정보 유출이 있었다"])
    return _unique_preserve_order(phrases)


def _interview_safe_answer(risk_area: str, summary: str) -> str:
    return (
        f"면접에서는 '{_shorten(summary)}'를 기관 비판으로 말하기보다, "
        f"{risk_area} 영역에서 운영 안정성, 투명성, 예방적 관리 수준을 높이는 기여로 연결합니다."
    )


def _applicant_connection(risk_area: str) -> str:
    if risk_area == "보안/개인정보/정보보호":
        return (
            "지원자는 접근권한 관리, 개인정보 보호, 보안 점검 자동화, 사고 예방 프로세스 경험을 "
            "개선 기여 포인트로 연결할 수 있습니다."
        )
    if risk_area in {"감사 지적", "국회 지적", "내부통제"}:
        return (
            "지원자는 절차 준수, 기록 관리, 리스크 사전 점검, 이해관계자 보고 체계 개선 경험을 "
            "기여 포인트로 연결할 수 있습니다."
        )
    if risk_area == "경영평가 개선 필요":
        return (
            "지원자는 성과지표 관리, 실행 일정 추적, 결과 환류 경험을 개선 기여 포인트로 "
            "연결할 수 있습니다."
        )
    if risk_area == "재무/부채 리스크":
        return (
            "지원자는 수치 기반 현황 파악, 예산 집행 점검, 비용 구조 개선 지원 경험을 신중한 "
            "기여 포인트로 연결할 수 있습니다."
        )
    return (
        "지원자는 문제를 단정하지 않고 업무 정확성, 협업, 프로세스 개선, 공공서비스 품질 향상 "
        "경험을 기여 포인트로 연결할 수 있습니다."
    )


def _follow_up_checks(
    risk_area: str,
    evidence: list[InstitutionEvidence],
    financial_without_numbers: bool,
) -> list[str]:
    checks: list[str] = []
    if not any(item.url for item in evidence):
        checks.append("원문 URL 또는 공시 항목 경로 확인")
    if not any(item.collected_at or item.fields.get("year") or item.fields.get("base_year") for item in evidence):
        checks.append("기준 연도 또는 수집 시점 확인")
    if risk_area in {"감사 지적", "국회 지적"}:
        checks.append("원문 지적사항의 조치 결과와 후속 개선 여부 확인")
    if risk_area == "경영평가 개선 필요":
        checks.append("평가등급보다 세부 평가 항목과 개선 권고 내용 확인")
    if financial_without_numbers:
        checks.append("재무/부채 관련 수치와 기준 연도 확인")
    if risk_area == "보안/개인정보/정보보호":
        checks.append("사고 발생 여부가 아니라 통제 체계 개선 근거인지 확인")
    return _unique_preserve_order(checks)


def _combined_text(summary: str, evidence: list[InstitutionEvidence]) -> str:
    parts = [summary]
    for item in evidence:
        parts.extend([item.title, item.excerpt or ""])
        parts.extend(str(value) for value in item.fields.values() if value is not None)
    return " ".join(parts)


def _has_number_or_year(text: str, evidence: list[InstitutionEvidence]) -> bool:
    if _has_number_like_text(text):
        return True
    return any(item.fields.get("year") or item.fields.get("base_year") for item in evidence)


def _has_number_like_text(text: str) -> bool:
    return bool(re.search(r"\d|[0-9]+(?:\.[0-9]+)?%|억원|백만원|천원", text))


def _severity_rank(severity: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(severity, 0)


def _strength_rank(strength: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(strength, 0)


def _source_weight(evidence: list[InstitutionEvidence]) -> int:
    return max((_SOURCE_WEIGHTS.get(item.source_type, 10) for item in evidence), default=0)


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
