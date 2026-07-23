"""Build conservative STAR answer frameworks from user-provided experience text."""

from __future__ import annotations

import re
from collections.abc import Iterable

from kr_gov_job_mcp.schemas.star_answer import (
    StarAnswerFramework,
    StarAnswerMode,
    StarCoverLetterDraft,
    StarInstitutionConnection,
    StarInterviewAnswer,
    StarJobConnection,
    StarMissingEvidence,
    StarRiskFlag,
    StarSection,
)


_SECTION_ORDER = ("situation", "task", "action", "result")
_SECTION_NAMES = {
    "situation": "Situation",
    "task": "Task",
    "action": "Action",
    "result": "Result",
}
_SECTION_GUIDANCE = {
    "situation": "경험이 발생한 배경, 문제, 제약을 사용자 원문으로 한 문장에 정리합니다.",
    "task": "사용자가 맡은 역할, 해결해야 한 문제, 목표를 사용자 원문으로 분리합니다.",
    "action": "사용자가 실제로 수행한 행동과 판단을 사용자 원문으로 분리합니다.",
    "result": "검증 가능한 결과, 배운 점, 개선 효과를 사용자 원문으로 분리합니다.",
}
_FOLLOW_UP_QUESTIONS = {
    "situation": "이 경험이 시작된 배경과 당시의 문제 또는 제약은 무엇이었나요?",
    "task": "본인이 맡은 역할과 해결해야 했던 목표를 구체적으로 적어주세요.",
    "action": "본인이 직접 취한 행동, 사용한 방법, 협업 방식은 무엇이었나요?",
    "result": "행동 뒤 확인한 결과, 변화, 배운 점은 무엇이며 어떻게 확인했나요?",
}
_LABEL_ALIASES = {
    "situation": {"s", "situation", "상황", "배경"},
    "task": {"t", "task", "과제", "역할", "문제", "목표"},
    "action": {"a", "action", "행동", "실행", "조치"},
    "result": {"r", "result", "결과", "성과", "배움", "배운점", "개선효과"},
}
_EXPLICIT_SECTION = re.compile(
    r"^\s*(?P<label>[A-Za-z가-힣 ]+?)\s*(?::|：|-|—)\s*(?P<excerpt>.+?)\s*$"
)
_METRIC_EXPRESSION = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|배|명|건|회|시간|분|초|일|주|개월|년|점|개|(?:천|만|억|조)+\s*원|원)"
)
_ACTION_STEMS = r"분석|설계|구현|개발|개선|조율|협업|자동화|검토|수집|작성|제안|운영|실행|수행"
_ACTION_EXPRESSION = re.compile(rf"(?:{_ACTION_STEMS})(?:했|하|해|하여|하고|함|한)")
_ACTION_NON_EVIDENCE = re.compile(
    rf"(?:{_ACTION_STEMS})(?:해야|하(?:지(?:는|도|만)?|진)\s*(?:못|않)|"
    r"할\s+(?:필요|계획|예정)|이\s+필요|할\s+수\s+없)"
)


def generate_star_answer_framework(
    *,
    question: str,
    user_experience: str,
    target_job: str,
    institution_name: str | None = None,
    ncs_competencies: Iterable[str] = (),
    mode: StarAnswerMode = "both",
) -> StarAnswerFramework:
    """Return STAR evidence, gaps, and safe output templates without inventing claims."""

    normalized_competencies = _dedupe_text(ncs_competencies)
    excerpts, unclassified_excerpts = _extract_star_excerpts(user_experience)
    risk_flags = _risk_flags([*_all_excerpts(excerpts), *unclassified_excerpts])
    risky_expressions = {flag.expression for flag in risk_flags}
    missing_evidence = _missing_evidence(excerpts)
    missing_fields = [item.field for item in missing_evidence]

    star = {
        section: StarSection(
            status="supported" if excerpts[section] else "missing",
            source_excerpts=excerpts[section],
            guidance=_SECTION_GUIDANCE[section],
        )
        for section in _SECTION_ORDER
    }
    supporting_excerpts = _all_excerpts(excerpts)
    drafts_ready = not missing_evidence and not risk_flags
    interview_answer = _interview_answer(
        mode=mode,
        excerpts=excerpts,
        target_job=target_job,
        supporting_excerpts=supporting_excerpts,
        missing_fields=missing_fields,
        drafts_ready=drafts_ready,
    )
    cover_letter_draft = _cover_letter_draft(
        mode=mode,
        question=question,
        excerpts=excerpts,
        target_job=target_job,
        supporting_excerpts=supporting_excerpts,
        missing_fields=missing_fields,
        drafts_ready=drafts_ready,
    )

    verification_notes: list[str] = []
    if missing_evidence:
        verification_notes.append("누락된 STAR 항목은 답변 본문에 임의로 채우지 않았습니다.")
    if risk_flags:
        verification_notes.append("과장 위험 표현은 검증 전 면접·자기소개서 문장에 넣지 않았습니다.")
    if normalized_competencies:
        verification_notes.append("NCS 후보는 사용자의 보유 역량으로 확정하지 않고 연결 검토 항목으로만 표시했습니다.")
    if institution_name:
        verification_notes.append("기관 관련 사실은 별도 공고·기관 자료로 확인한 뒤 연결해야 합니다.")
    if unclassified_excerpts:
        verification_notes.append(
            "STAR 항목을 하나로 확인하기 어려운 문장은 임의 분류하지 않고 별도로 보존했습니다."
        )

    return StarAnswerFramework(
        question=question,
        target_job=target_job,
        institution_name=institution_name,
        ncs_competencies=normalized_competencies,
        mode=mode,
        star=star,
        unclassified_excerpts=unclassified_excerpts,
        job_connections=_job_connections(
            target_job=target_job,
            competencies=normalized_competencies,
            source_excerpts=[excerpt for excerpt in supporting_excerpts if excerpt not in risky_expressions],
        ),
        institution_connection=_institution_connection(institution_name, target_job),
        missing_evidence=missing_evidence,
        follow_up_questions=[item.follow_up_question for item in missing_evidence],
        risk_flags=risk_flags,
        interview_answer=interview_answer,
        cover_letter_draft=cover_letter_draft,
        verification_notes=verification_notes,
    )


def _extract_star_excerpts(
    user_experience: str,
) -> tuple[dict[str, list[str]], list[str]]:
    excerpts = {section: [] for section in _SECTION_ORDER}
    unclassified: list[str] = []

    for fragment in _experience_fragments(user_experience):
        explicit_section, excerpt = _explicit_section(fragment)
        if explicit_section is None or (
            explicit_section == "action" and _ACTION_NON_EVIDENCE.search(excerpt)
        ):
            unclassified.append(excerpt)
        else:
            _append_unique(excerpts[explicit_section], excerpt)

    remaining_unclassified: list[str] = []
    for excerpt in unclassified:
        section = _classify_excerpt(excerpt)
        if section is None:
            _append_unique(remaining_unclassified, excerpt)
            continue
        _append_unique(excerpts[section], excerpt)

    return excerpts, remaining_unclassified


def _experience_fragments(user_experience: str) -> list[str]:
    fragments: list[str] = []
    for line in re.split(r"[\r\n]+", user_experience):
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if not line:
            continue
        for fragment in re.split(r"(?<=[.!?])\s+", line):
            text = fragment.strip()
            if text:
                fragments.append(text)
    return fragments


def _explicit_section(fragment: str) -> tuple[str | None, str]:
    match = _EXPLICIT_SECTION.match(fragment)
    if match is None:
        return None, fragment
    label = re.sub(r"\s+", "", match.group("label")).lower()
    for section, aliases in _LABEL_ALIASES.items():
        if label in aliases:
            return section, match.group("excerpt").strip()
    return None, fragment


def _classify_excerpt(excerpt: str) -> str | None:
    text = excerpt.lower()
    cues = (
        ("result", ("결과", "성과", "달성", "향상", "감소", "증가", "배웠", "배움", "효과", "없앴")),
        ("task", ("역할", "담당", "책임", "목표", "과제", "문제", "요구")),
        ("situation", ("당시", "상황", "배경", "프로젝트", "팀", "인턴", "공모전", "동아리")),
    )
    matched_sections = [
        section for section, keywords in cues if any(keyword in text for keyword in keywords)
    ]
    if _ACTION_EXPRESSION.search(text) and not _ACTION_NON_EVIDENCE.search(text):
        matched_sections.append("action")
    if len(matched_sections) == 1:
        return matched_sections[0]
    return None


def _missing_evidence(excerpts: dict[str, list[str]]) -> list[StarMissingEvidence]:
    return [
        StarMissingEvidence(
            field=f"star.{section}",
            reason=f"{_SECTION_NAMES[section]}에 연결할 사용자 제공 경험 근거가 없습니다.",
            follow_up_question=_FOLLOW_UP_QUESTIONS[section],
        )
        for section in _SECTION_ORDER
        if not excerpts[section]
    ]


def _risk_flags(excerpts: Iterable[str]) -> list[StarRiskFlag]:
    flags: list[StarRiskFlag] = []
    for excerpt in excerpts:
        if any(term in excerpt for term in ("완전히", "완벽", "전혀", "100%", "없앴")):
            flags.append(
                StarRiskFlag(
                    category="absolute_claim",
                    expression=excerpt,
                    reason="절대적 결과 표현은 적용 범위와 검증 기준이 없으면 과장으로 보일 수 있습니다.",
                    safer_framing="대상, 기간, 확인 방법을 제시하고 절대 표현은 검증 가능한 범위로 바꾸세요.",
                )
            )
        if any(term in excerpt for term in ("혼자", "단독", "전부")):
            flags.append(
                StarRiskFlag(
                    category="exclusive_claim",
                    expression=excerpt,
                    reason="단독 수행 표현은 실제 협업 범위와 책임 구분을 확인해야 합니다.",
                    safer_framing="본인 기여와 협업자의 역할을 나눠서 설명하세요.",
                )
            )
        if any(term in excerpt for term in ("전사", "전체 조직", "모든 부서")):
            flags.append(
                StarRiskFlag(
                    category="scope_claim",
                    expression=excerpt,
                    reason="조직 전체 효과 주장은 적용 대상과 승인 범위를 확인해야 합니다.",
                    safer_framing="적용한 시스템, 팀, 기간을 실제 확인 가능한 범위로 제한하세요.",
                )
            )
        if _METRIC_EXPRESSION.search(excerpt):
            flags.append(
                StarRiskFlag(
                    category="unverified_metric",
                    expression=excerpt,
                    reason="정량 성과는 계산 기준과 확인 근거가 없으면 검증이 필요합니다.",
                    safer_framing="수치의 기준 기간, 비교 대상, 측정 방법을 함께 제시하세요.",
                )
            )
    return _dedupe_flags(flags)


def _job_connections(
    *,
    target_job: str,
    competencies: list[str],
    source_excerpts: list[str],
) -> list[StarJobConnection]:
    if not competencies:
        return [
            StarJobConnection(
                connection_sentence=(
                    f"{target_job} 직무의 실제 공고·직무기술서와 사용자 경험 근거를 대조해 연결하세요."
                ),
                source_excerpts=source_excerpts,
            )
        ]
    return [
        StarJobConnection(
            competency=competency,
            connection_sentence=(
                f"NCS 후보 '{competency}'를 사용자의 보유 역량으로 단정하지 않고, 제공된 경험 근거를 "
                f"{target_job} 직무의 해당 NCS 후보와 연결해 설명할 수 있는지 검토하세요."
            ),
            source_excerpts=source_excerpts,
        )
        for competency in competencies
    ]


def _institution_connection(
    institution_name: str | None,
    target_job: str,
) -> StarInstitutionConnection | None:
    if institution_name is None:
        return None
    return StarInstitutionConnection(
        institution_name=institution_name,
        connection_sentence=(
            f"{institution_name} 관련 사실은 이 도구가 생성하지 않습니다. 공개 공고·기관 자료를 확인한 뒤 "
            f"{target_job} 직무와 제공 경험의 연결 근거를 추가하세요."
        ),
    )


def _interview_answer(
    *,
    mode: StarAnswerMode,
    excerpts: dict[str, list[str]],
    target_job: str,
    supporting_excerpts: list[str],
    missing_fields: list[str],
    drafts_ready: bool,
) -> StarInterviewAnswer:
    if mode == "cover_letter":
        return StarInterviewAnswer(status="not_requested")
    if not drafts_ready:
        return StarInterviewAnswer(
            status="needs_evidence",
            supporting_excerpts=supporting_excerpts,
            missing_fields=missing_fields,
        )
    return StarInterviewAnswer(
        status="ready",
        short_answer=(
            "핵심 경험을 다음 STAR 흐름으로 설명할 수 있습니다. "
            f"상황·배경: '{_joined(excerpts['situation'])}' / "
            f"과제·역할: '{_joined(excerpts['task'])}' / "
            f"실제 행동: '{_joined(excerpts['action'])}' / "
            f"결과·배운 점: '{_joined(excerpts['result'])}'. 이 경험을 "
            f"{target_job} 직무의 실제 요구 역량과 대조해 답하겠습니다."
        ),
        supporting_excerpts=supporting_excerpts,
    )


def _cover_letter_draft(
    *,
    mode: StarAnswerMode,
    question: str,
    excerpts: dict[str, list[str]],
    target_job: str,
    supporting_excerpts: list[str],
    missing_fields: list[str],
    drafts_ready: bool,
) -> StarCoverLetterDraft:
    if mode == "interview":
        return StarCoverLetterDraft(status="not_requested")
    if not drafts_ready:
        return StarCoverLetterDraft(
            status="needs_evidence",
            supporting_excerpts=supporting_excerpts,
            missing_fields=missing_fields,
        )
    return StarCoverLetterDraft(
        status="ready",
        sentence_draft=(
            f"'{question}'에 답하기 위한 초안입니다. "
            f"상황·배경: '{_joined(excerpts['situation'])}' / "
            f"과제·역할: '{_joined(excerpts['task'])}' / "
            f"실제 행동: '{_joined(excerpts['action'])}' / "
            f"결과·배운 점: '{_joined(excerpts['result'])}'. 이 경험을 {target_job} 직무의 "
            "실제 요구 역량과 대조해 구체화하겠습니다."
        ),
        supporting_excerpts=supporting_excerpts,
    )


def _all_excerpts(excerpts: dict[str, list[str]]) -> list[str]:
    return [excerpt for section in _SECTION_ORDER for excerpt in excerpts[section]]


def _joined(excerpts: list[str]) -> str:
    return " ".join(excerpts)


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _dedupe_text(values: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            _append_unique(deduped, text)
    return deduped


def _dedupe_flags(flags: list[StarRiskFlag]) -> list[StarRiskFlag]:
    deduped: list[StarRiskFlag] = []
    seen: set[tuple[str, str]] = set()
    for flag in flags:
        key = (flag.category, flag.expression)
        if key not in seen:
            seen.add(key)
            deduped.append(flag)
    return deduped
