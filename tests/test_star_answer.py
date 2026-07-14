import pytest

from kr_gov_job_mcp.analysis import generate_star_answer_framework
from kr_gov_job_mcp.schemas.star_answer import StarAnswerFramework


_COMPLETE_EXPERIENCE = """
Situation: 동아리 시스템에서 제출 누락이 반복됐다.
Task: 나는 점검 절차를 정리하고 오류 원인을 파악하는 역할을 맡았다.
Action: 로그를 분석하고 팀원과 검증 체크리스트를 만들었다.
Result: 검토 누락을 줄이고 재사용 가능한 점검 절차를 만들었다.
"""


def test_generate_star_answer_framework_uses_only_complete_user_evidence() -> None:
    framework = generate_star_answer_framework(
        question="문제를 해결한 경험을 설명해 주세요.",
        user_experience=_COMPLETE_EXPERIENCE,
        target_job="전산직",
        ncs_competencies=["문제해결능력"],
    )

    assert StarAnswerFramework.model_validate(framework.model_dump())
    assert framework.missing_evidence == []
    assert framework.risk_flags == []
    assert framework.star["situation"].source_excerpts == ["동아리 시스템에서 제출 누락이 반복됐다."]
    assert framework.star["task"].source_excerpts == [
        "나는 점검 절차를 정리하고 오류 원인을 파악하는 역할을 맡았다."
    ]
    assert framework.star["action"].source_excerpts == [
        "로그를 분석하고 팀원과 검증 체크리스트를 만들었다."
    ]
    assert framework.star["result"].source_excerpts == [
        "검토 누락을 줄이고 재사용 가능한 점검 절차를 만들었다."
    ]
    assert framework.interview_answer.status == "ready"
    assert framework.cover_letter_draft.status == "ready"
    assert framework.interview_answer.short_answer
    assert framework.cover_letter_draft.sentence_draft
    assert framework.interview_answer.short_answer != framework.cover_letter_draft.sentence_draft
    assert "제출 누락" in framework.interview_answer.short_answer
    assert "전산직" in framework.cover_letter_draft.sentence_draft


def test_generate_star_answer_framework_returns_gaps_without_inventing_result() -> None:
    framework = generate_star_answer_framework(
        question="문제 해결 경험을 설명해 주세요.",
        user_experience="Action: 오류 로그를 분류했다.",
        target_job="전산직",
    )

    fields = {item.field for item in framework.missing_evidence}
    assert fields == {"star.situation", "star.task", "star.result"}
    assert framework.follow_up_questions
    assert framework.star["result"].source_excerpts == []
    assert framework.interview_answer.status == "needs_evidence"
    assert framework.interview_answer.short_answer is None
    assert framework.cover_letter_draft.status == "needs_evidence"
    assert framework.cover_letter_draft.sentence_draft is None


def test_generate_star_answer_framework_does_not_fill_sections_by_sentence_order() -> None:
    framework = generate_star_answer_framework(
        question="경험을 설명해 주세요.",
        user_experience="첫 번째 문장이다. 두 번째 문장이다. 세 번째 문장이다. 네 번째 문장이다.",
        target_job="전산직",
    )

    assert all(section.status == "missing" for section in framework.star.values())
    assert framework.unclassified_excerpts == [
        "첫 번째 문장이다.",
        "두 번째 문장이다.",
        "세 번째 문장이다.",
        "네 번째 문장이다.",
    ]
    assert framework.interview_answer.status == "needs_evidence"
    assert framework.cover_letter_draft.status == "needs_evidence"


def test_generate_star_answer_framework_keeps_ambiguous_excerpt_unclassified() -> None:
    framework = generate_star_answer_framework(
        question="문제 해결 경험을 설명해 주세요.",
        user_experience="프로젝트 결과를 개선하기 위해 로그를 분석했다.",
        target_job="전산직",
    )

    assert framework.unclassified_excerpts == [
        "프로젝트 결과를 개선하기 위해 로그를 분석했다."
    ]
    assert framework.star["action"].source_excerpts == []
    assert framework.star["result"].source_excerpts == []


def test_generate_star_answer_framework_classifies_single_cue_without_label() -> None:
    framework = generate_star_answer_framework(
        question="행동을 설명해 주세요.",
        user_experience="로그를 분석하고 체크리스트를 작성했다.",
        target_job="전산직",
    )

    assert framework.star["action"].source_excerpts == [
        "로그를 분석하고 체크리스트를 작성했다."
    ]
    assert framework.unclassified_excerpts == []


@pytest.mark.parametrize(
    "unperformed_action",
    ["로그 분석이 필요했다.", "로그를 분석해야 했다.", "로그를 분석하지 못했다."],
)
def test_generate_star_answer_framework_does_not_treat_unperformed_action_as_performed(
    unperformed_action: str,
) -> None:
    framework = generate_star_answer_framework(
        question="문제 해결 경험을 설명해 주세요.",
        user_experience=f"""
Situation: 서비스 오류가 반복됐다.
Task: 원인 파악을 맡았다.
{unperformed_action}
Result: 점검 기준을 정리했다.
""",
        target_job="전산직",
    )

    assert framework.star["action"].status == "missing"
    assert framework.star["action"].source_excerpts == []
    assert framework.unclassified_excerpts == [unperformed_action]
    assert framework.interview_answer.status == "needs_evidence"


def test_generate_star_answer_framework_links_ncs_without_claiming_possession() -> None:
    framework = generate_star_answer_framework(
        question="직무 역량을 설명해 주세요.",
        user_experience=_COMPLETE_EXPERIENCE,
        target_job="정보통신 전산직",
        ncs_competencies=["문제해결능력", "정보기술능력"],
    )

    assert [connection.competency for connection in framework.job_connections] == [
        "문제해결능력",
        "정보기술능력",
    ]
    for connection in framework.job_connections:
        assert "정보통신 전산직" in connection.connection_sentence
        assert "보유 역량으로 단정하지 않고" in connection.connection_sentence
        assert connection.needs_verification is True


def test_generate_star_answer_framework_flags_risky_expressions_and_withholds_drafts() -> None:
    framework = generate_star_answer_framework(
        question="성과를 설명해 주세요.",
        user_experience="""
Situation: 장애 대응 요청이 들어온 상황이었다.
Task: 나는 대응 절차 정리를 맡았다.
Action: 원인을 분석하고 대응 순서를 문서화했다.
Result: 혼자 전사 시스템을 완전히 개선해 장애를 100% 없앴다.
""",
        target_job="전산직",
    )

    categories = {flag.category for flag in framework.risk_flags}
    assert categories >= {
        "absolute_claim",
        "exclusive_claim",
        "scope_claim",
        "unverified_metric",
    }
    assert framework.star["result"].source_excerpts == [
        "혼자 전사 시스템을 완전히 개선해 장애를 100% 없앴다."
    ]
    assert framework.interview_answer.status == "needs_evidence"
    assert framework.interview_answer.short_answer is None
    assert framework.cover_letter_draft.status == "needs_evidence"
    assert framework.cover_letter_draft.sentence_draft is None


def test_generate_star_answer_framework_flags_risk_in_unclassified_excerpt() -> None:
    framework = generate_star_answer_framework(
        question="문제 해결 경험을 설명해 주세요.",
        user_experience=(
            _COMPLETE_EXPERIENCE + "\n이후 오류가 전혀 발생하지 않았다."
        ),
        target_job="전산직",
    )

    assert framework.missing_evidence == []
    assert framework.unclassified_excerpts == ["이후 오류가 전혀 발생하지 않았다."]
    assert {flag.category for flag in framework.risk_flags} == {"absolute_claim"}
    assert framework.interview_answer.status == "needs_evidence"
    assert framework.cover_letter_draft.status == "needs_evidence"


def test_generate_star_answer_framework_distinguishes_requested_modes() -> None:
    interview_only = generate_star_answer_framework(
        question="문제를 해결한 경험을 설명해 주세요.",
        user_experience=_COMPLETE_EXPERIENCE,
        target_job="전산직",
        mode="interview",
    )
    cover_letter_only = generate_star_answer_framework(
        question="문제를 해결한 경험을 설명해 주세요.",
        user_experience=_COMPLETE_EXPERIENCE,
        target_job="전산직",
        mode="cover_letter",
    )

    assert interview_only.interview_answer.status == "ready"
    assert interview_only.cover_letter_draft.status == "not_requested"
    assert cover_letter_only.interview_answer.status == "not_requested"
    assert cover_letter_only.cover_letter_draft.status == "ready"
