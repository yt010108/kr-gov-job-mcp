import pytest

from kr_gov_job_mcp.tools.star_answer import (
    GENERATE_STAR_ANSWER_FRAMEWORK_INPUT_SCHEMA,
    create_generate_star_answer_framework_tool,
)


_COMPLETE_ARGUMENTS = {
    "question": "문제를 해결한 경험을 설명해 주세요.",
    "user_experience": """
Situation: 동아리 시스템에서 제출 누락이 반복됐다.
Task: 나는 점검 절차 정리와 오류 원인 파악을 맡았다.
Action: 로그를 분석하고 팀원과 검증 체크리스트를 만들었다.
Result: 검토 누락을 줄이고 재사용 가능한 점검 절차를 만들었다.
""",
    "target_job": "전산직",
}


def test_generate_star_answer_framework_tool_has_strict_star_only_schema() -> None:
    schema = GENERATE_STAR_ANSWER_FRAMEWORK_INPUT_SCHEMA

    assert schema["required"] == ["question", "user_experience", "target_job"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["question"]["pattern"] == r"\S"
    assert schema["properties"]["user_experience"]["pattern"] == r"\S"
    assert schema["properties"]["target_job"]["pattern"] == r"\S"
    assert schema["properties"]["mode"]["enum"] == ["cover_letter", "interview", "both"]
    assert "PREP" not in schema["properties"]
    assert "AUTO" not in schema["properties"]


def test_generate_star_answer_framework_tool_serializes_framework() -> None:
    tool = create_generate_star_answer_framework_tool()

    result = tool.handler(
        {
            **_COMPLETE_ARGUMENTS,
            "institution_name": "한국인터넷진흥원",
            "ncs_competencies": ["문제해결능력", "문제해결능력"],
            "mode": "both",
        }
    )

    assert result["source"] == "star_answer_framework"
    assert result["query"] == {
        "question": "문제를 해결한 경험을 설명해 주세요.",
        "target_job": "전산직",
        "institution_name": "한국인터넷진흥원",
        "ncs_competencies": ["문제해결능력"],
        "mode": "both",
    }
    assert result["star"]["action"]["status"] == "supported"
    assert result["unclassified_excerpts"] == []
    assert result["institution_connection"]["needs_verification"] is True
    assert result["interview_answer"]["status"] == "ready"
    assert result["cover_letter_draft"]["status"] == "ready"


def test_generate_star_answer_framework_tool_rejects_invalid_arguments_and_modes() -> None:
    tool = create_generate_star_answer_framework_tool()

    with pytest.raises(ValueError, match="unsupported generate_star_answer_framework arguments"):
        tool.handler({**_COMPLETE_ARGUMENTS, "unknown": True})
    with pytest.raises(ValueError, match="question is required"):
        tool.handler({**_COMPLETE_ARGUMENTS, "question": "   "})
    with pytest.raises(ValueError, match="expected list value for ncs_competencies"):
        tool.handler({**_COMPLETE_ARGUMENTS, "ncs_competencies": "문제해결능력"})
    for unsupported_mode in ("PREP", "AUTO", "other"):
        with pytest.raises(ValueError, match="mode must be one of"):
            tool.handler({**_COMPLETE_ARGUMENTS, "mode": unsupported_mode})
