"""Prepare interview-ready cards from institution analysis signals."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from kr_gov_job_mcp.analysis.institution_strategy import generate_institution_strategy_report
from kr_gov_job_mcp.analysis.institution_weakness import generate_institution_weakness_report
from kr_gov_job_mcp.schemas.institution import (
    InstitutionAnalysisInput,
    InstitutionEvidence,
    InstitutionInterviewCard,
    InstitutionInterviewReport,
    InstitutionStrategySignal,
    InstitutionVerificationNote,
    InstitutionWeaknessSignal,
)


DEFAULT_FOCUS_AREAS = ("지원동기", "기관이해", "개선과제", "입사후포부")
MATERIALS_TO_CHECK = ["주요사업", "연구/정책 자료", "국회 지적사항"]
EXCLUDED_FOR_NOW = ["감사/경영평가 자료", "채용공고", "직무기술서", "NCS 정보"]

_FOCUS_ALIASES = {
    "지원동기": "지원동기",
    "기관이해": "기관 현안 이해",
    "기관 이해": "기관 현안 이해",
    "기관 현안 이해": "기관 현안 이해",
    "현안이해": "기관 현안 이해",
    "현안 이해": "기관 현안 이해",
    "개선과제": "개선과제",
    "개선 과제": "개선과제",
    "입사후포부": "입사후포부",
    "입사 후 포부": "입사후포부",
    "직무 관심도": "직무 관심도",
    "전문성 어필": "전문성 어필",
}


def generate_institution_interview_report(
    analysis_input: InstitutionAnalysisInput,
    *,
    target_role: str,
    year: int | None = None,
    focus_areas: Iterable[str] | None = None,
) -> InstitutionInterviewReport:
    """Build interview cards from the reusable strategy and weakness reports."""

    normalized_focus_areas = _normalize_focus_areas(focus_areas)
    strategy_report = generate_institution_strategy_report(
        analysis_input,
        year=year,
        job_family=target_role,
    )
    weakness_report = generate_institution_weakness_report(analysis_input, year=year)

    cards: list[InstitutionInterviewCard] = []
    verification_notes = _dedupe_notes(
        [
            *strategy_report.verification_notes,
            *weakness_report.verification_notes,
        ]
    )

    for focus_area in normalized_focus_areas:
        card, notes = _build_card(
            focus_area,
            institution_name=analysis_input.normalized_name,
            target_role=target_role,
            strategy_signals=strategy_report.strategy_signals,
            weakness_signals=weakness_report.weakness_signals,
        )
        cards.append(card)
        verification_notes.extend(notes)

    return InstitutionInterviewReport(
        institution_name=analysis_input.institution_name,
        normalized_name=analysis_input.normalized_name,
        year=year,
        target_role=target_role,
        interview_cards=cards,
        materials_to_check=list(MATERIALS_TO_CHECK),
        excluded_for_now=list(EXCLUDED_FOR_NOW),
        verification_notes=_dedupe_notes(verification_notes),
    )


def _normalize_focus_areas(focus_areas: Iterable[str] | None) -> list[str]:
    raw_values = list(focus_areas or DEFAULT_FOCUS_AREAS)
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        text = str(raw_value).strip()
        if not text:
            continue
        canonical = _FOCUS_ALIASES.get(text, text)
        if canonical in seen:
            continue
        seen.add(canonical)
        normalized.append(canonical)
    return normalized or list(DEFAULT_FOCUS_AREAS)


def _build_card(
    focus_area: str,
    *,
    institution_name: str,
    target_role: str,
    strategy_signals: Sequence[InstitutionStrategySignal],
    weakness_signals: Sequence[InstitutionWeaknessSignal],
) -> tuple[InstitutionInterviewCard, list[InstitutionVerificationNote]]:
    if focus_area == "지원동기":
        return _motivation_card(institution_name, target_role, strategy_signals)
    if focus_area == "기관 현안 이해":
        return _issue_understanding_card(institution_name, target_role, strategy_signals)
    if focus_area == "개선과제":
        return _improvement_card(institution_name, target_role, weakness_signals)
    if focus_area == "입사후포부":
        return _future_contribution_card(institution_name, target_role, strategy_signals)
    if focus_area in {"직무 관심도", "전문성 어필"}:
        return _professional_interest_card(focus_area, institution_name, target_role, strategy_signals)
    return _unsupported_focus_card(focus_area)


def _motivation_card(
    institution_name: str,
    target_role: str,
    strategy_signals: Sequence[InstitutionStrategySignal],
) -> tuple[InstitutionInterviewCard, list[InstitutionVerificationNote]]:
    signal = _first_strategy_signal(strategy_signals, preferred_sources=("major_business",))
    if signal is None:
        return _missing_evidence_card(
            question_type="지원동기",
            likely_question=f"왜 {institution_name}에 지원했나요?",
            answer_strategy="주요사업 근거를 확인한 뒤 지원자의 직무 관심과 연결합니다.",
            required_material="주요사업",
        )
    summary = _trim(signal.summary, limit=180)
    return (
        InstitutionInterviewCard(
            question_type="지원동기",
            likely_question=f"왜 {institution_name}에 지원했나요?",
            answer_strategy="ALIO 주요사업에서 확인한 사업 규모나 성장 흐름을 지원 직무 관심과 연결합니다.",
            answer_points=[
                f"주요사업 근거: {summary}",
                f"{target_role} 경험은 위 사업 방향에 필요한 실행 역량 사례 1개와 연결합니다.",
            ],
            sample_answer_sentence=(
                f"ALIO 주요사업에서 확인한 '{summary}'를 보고, {target_role} 직무로 이 흐름에 필요한 "
                "실행 역량을 보태고 싶다고 설명하겠습니다."
            ),
            evidence=signal.evidence,
            caution="공시 근거를 넘어 기관 전체 성과나 내부 우선순위를 단정하지 않습니다.",
        ),
        [],
    )


def _issue_understanding_card(
    institution_name: str,
    target_role: str,
    strategy_signals: Sequence[InstitutionStrategySignal],
) -> tuple[InstitutionInterviewCard, list[InstitutionVerificationNote]]:
    signal = _first_strategy_signal(
        strategy_signals,
        preferred_sources=("policy_research", "major_business"),
    )
    if signal is None:
        return _missing_evidence_card(
            question_type="기관 현안 이해",
            likely_question=f"최근 {institution_name}의 주요 이슈를 어떻게 보고 있나요?",
            answer_strategy="연구/정책 자료 또는 주요사업 근거를 확인한 뒤 기관 현안을 설명합니다.",
            required_material="연구/정책 자료",
        )
    summary = _trim(signal.summary, limit=180)
    return (
        InstitutionInterviewCard(
            question_type="기관 현안 이해",
            likely_question=f"최근 {institution_name}의 주요 이슈를 어떻게 보고 있나요?",
            answer_strategy=(
                "연구/정책 자료나 주요사업 근거를 바탕으로 기관이 실제로 다루는 정책 방향을 설명합니다."
            ),
            answer_points=[
                f"확인된 자료: {summary}",
                f"{target_role} 관점에서는 이 자료가 요구하는 업무 이해도와 기여 방향을 분리해 답합니다.",
            ],
            sample_answer_sentence=(
                f"최근 자료에서는 '{summary}'가 확인되어, {target_role} 직무 관점에서 관련 과제를 먼저 "
                "이해하고 필요한 실행 역할을 찾겠습니다."
            ),
            evidence=signal.evidence,
            caution="자료 제목이나 공시 문구에 없는 정책 효과를 새로 만들어 말하지 않습니다.",
        ),
        [],
    )


def _improvement_card(
    institution_name: str,
    target_role: str,
    weakness_signals: Sequence[InstitutionWeaknessSignal],
) -> tuple[InstitutionInterviewCard, list[InstitutionVerificationNote]]:
    signal = weakness_signals[0] if weakness_signals else None
    if signal is None:
        return _missing_evidence_card(
            question_type="개선과제",
            likely_question=f"{institution_name}이 보완해야 할 점은 무엇이라고 보나요?",
            answer_strategy="국회 지적사항 근거를 확인한 뒤 비판보다 개선 방향 중심으로 답합니다.",
            required_material="국회 지적사항",
        )
    summary = _trim(signal.summary, limit=180)
    safe_framing = (
        f"'{summary}'를 기관의 단정적 문제로 말하기보다, 공개 지적사항에서 확인된 개선 필요 영역으로 "
        f"보고 {target_role} 관점의 보완 방향을 제안합니다."
    )
    return (
        InstitutionInterviewCard(
            question_type="개선과제",
            likely_question=f"{institution_name}이 보완해야 할 점은 무엇이라고 보나요?",
            answer_strategy="국회 지적사항을 근거로 삼되, 기관 비판이 아니라 개선 방향과 지원 직무의 기여로 전환합니다.",
            answer_points=[
                f"지적사항 근거: {summary}",
                f"{target_role} 직무로는 점검, 기준 정비, 실행 관리 같은 보완 방향을 조심스럽게 제안합니다.",
            ],
            sample_answer_sentence=(
                f"공개 지적사항에서 '{summary}'가 확인된 만큼, 이를 비판으로 단정하기보다 관리 체계를 "
                f"보완하는 과제로 보고 {target_role} 직무에서 기여할 수 있는 부분을 찾겠습니다."
            ),
            evidence=signal.evidence,
            caution=signal.careful_wording,
            safe_framing=safe_framing,
        ),
        [],
    )


def _future_contribution_card(
    institution_name: str,
    target_role: str,
    strategy_signals: Sequence[InstitutionStrategySignal],
) -> tuple[InstitutionInterviewCard, list[InstitutionVerificationNote]]:
    signal = _first_strategy_signal(
        strategy_signals,
        preferred_sources=("major_business", "policy_research"),
    )
    if signal is None:
        return _missing_evidence_card(
            question_type="입사후포부",
            likely_question=f"{institution_name}에 입사하면 무엇을 해보고 싶나요?",
            answer_strategy="주요사업 또는 연구/정책 자료 근거를 확인한 뒤 입사 후 기여 방향을 정합니다.",
            required_material="주요사업",
        )
    summary = _trim(signal.summary, limit=180)
    return (
        InstitutionInterviewCard(
            question_type="입사후포부",
            likely_question=f"{institution_name}에 입사하면 무엇을 해보고 싶나요?",
            answer_strategy="주요사업이나 연구 자료에서 확인한 기관 과제와 지원 직무의 실행 역할을 연결합니다.",
            answer_points=[
                f"기여 방향의 근거: {summary}",
                f"{target_role} 직무 역량은 신규 사업을 단정하지 말고 기존 공시 과제의 실행 보완으로 표현합니다.",
            ],
            sample_answer_sentence=(
                f"입사 후에는 '{summary}'와 연결되는 업무를 먼저 이해하고, {target_role} 직무 역량으로 "
                "실행 품질을 높이는 데 기여하고 싶습니다."
            ),
            evidence=signal.evidence,
            caution="아직 확인하지 않은 신규 사업, 내부 계획, 채용 직무 범위를 확정적으로 말하지 않습니다.",
        ),
        [],
    )


def _professional_interest_card(
    focus_area: str,
    institution_name: str,
    target_role: str,
    strategy_signals: Sequence[InstitutionStrategySignal],
) -> tuple[InstitutionInterviewCard, list[InstitutionVerificationNote]]:
    signal = _first_strategy_signal(strategy_signals, preferred_sources=("policy_research",))
    if signal is None:
        return _missing_evidence_card(
            question_type=focus_area,
            likely_question=f"{institution_name}의 어떤 업무에 관심이 있나요?",
            answer_strategy="연구/정책 자료 근거를 확인한 뒤 직무 관심과 전문성 어필 포인트를 정합니다.",
            required_material="연구/정책 자료",
        )
    summary = _trim(signal.summary, limit=180)
    return (
        InstitutionInterviewCard(
            question_type=focus_area,
            likely_question=f"{institution_name}의 어떤 업무에 관심이 있나요?",
            answer_strategy="연구/정책 자료 제목과 공개 근거를 직무 관심도, 학습 경험, 전문성 어필로 연결합니다.",
            answer_points=[
                f"관심 근거: {summary}",
                f"{target_role} 관련 경험은 연구/정책 자료의 주제와 직접 맞닿은 부분만 사용합니다.",
            ],
            sample_answer_sentence=(
                f"공개 연구/정책 자료에서 '{summary}'를 확인했고, 이 주제와 맞닿은 {target_role} 역량을 "
                "더 깊게 다뤄보고 싶습니다."
            ),
            evidence=signal.evidence,
            caution="자료 제목만 보고 연구 내용 전체를 읽은 것처럼 말하지 않습니다.",
        ),
        [],
    )


def _missing_evidence_card(
    *,
    question_type: str,
    likely_question: str,
    answer_strategy: str,
    required_material: str,
) -> tuple[InstitutionInterviewCard, list[InstitutionVerificationNote]]:
    return (
        InstitutionInterviewCard(
            question_type=question_type,
            likely_question=likely_question,
            answer_strategy=answer_strategy,
            answer_points=[],
            sample_answer_sentence=None,
            evidence=[],
            caution="근거가 없어 답변 본문을 확정하지 않습니다. 먼저 공개 자료를 확인해야 합니다.",
            safe_framing=(
                "확인된 근거가 없는 상태에서는 면접 답변에 기관 사실처럼 넣지 않고 추가 확인 대상으로 둡니다."
            ),
        ),
        [
            InstitutionVerificationNote(
                field=f"interview_cards.{question_type}.evidence",
                reason=f"{question_type} 카드에 사용할 {required_material} 근거가 없습니다.",
                suggested_check=f"ALIO {required_material} 자료를 조회한 뒤 카드 본문을 확정합니다.",
            )
        ],
    )


def _unsupported_focus_card(
    focus_area: str,
) -> tuple[InstitutionInterviewCard, list[InstitutionVerificationNote]]:
    return (
        InstitutionInterviewCard(
            question_type=focus_area,
            likely_question=f"{focus_area} 관련 질문",
            answer_strategy="이번 MVP에서 지원하는 focus area로 변환할 수 없어 추가 설계가 필요합니다.",
            answer_points=[],
            sample_answer_sentence=None,
            evidence=[],
            caution="지원하지 않는 focus area는 근거 기반 답변으로 확정하지 않습니다.",
        ),
        [
            InstitutionVerificationNote(
                field=f"focus_areas.{focus_area}",
                reason=f"{focus_area}는 이번 MVP의 기본 카드 유형이 아닙니다.",
                suggested_check="지원동기, 기관이해, 개선과제, 입사후포부, 직무 관심도, 전문성 어필 중 하나로 지정합니다.",
            )
        ],
    )


def _first_strategy_signal(
    signals: Sequence[InstitutionStrategySignal],
    *,
    preferred_sources: Sequence[str],
) -> InstitutionStrategySignal | None:
    for source_type in preferred_sources:
        for signal in signals:
            if _has_source(signal.evidence, {source_type}):
                return signal
    return signals[0] if signals else None


def _has_source(evidence: Sequence[InstitutionEvidence], source_types: set[str]) -> bool:
    return any(_source_type(item) in source_types for item in evidence)


def _source_type(evidence: InstitutionEvidence) -> str | None:
    source_hint = evidence.fields.get("source_type") or evidence.fields.get("source_category")
    return str(source_hint) if source_hint else None


def _dedupe_notes(
    notes: Iterable[InstitutionVerificationNote],
) -> list[InstitutionVerificationNote]:
    unique: list[InstitutionVerificationNote] = []
    seen: set[tuple[str, str, str]] = set()
    for note in notes:
        key = (note.field, note.reason, note.suggested_check)
        if key in seen:
            continue
        seen.add(key)
        unique.append(note)
    return unique


def _trim(value: str, *, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."
