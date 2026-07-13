import pytest

from kr_gov_job_mcp.analysis import normalize_job_role
from kr_gov_job_mcp.tools.institution_analysis import PREPARE_INSTITUTION_INTERVIEW_INPUT_SCHEMA
from kr_gov_job_mcp.tools.job_role import create_normalize_job_role_tool
from kr_gov_job_mcp.tools.public_jobs import ANALYZE_JOB_FIT_REPORT_INPUT_SCHEMA


def test_security_job_aliases_are_normalized_to_information_communication() -> None:
    cases = [
        "정보보안",
        "정보보호",
        "침해사고 대응",
        "취약점 분석",
        "개인정보보호",
        "정보통신 보안",
    ]

    for case in cases:
        normalized = normalize_job_role(target_role=case)

        assert normalized["normalized_job_family"] == "정보통신"
        assert normalized["normalized_target_role"] == "정보통신"
        assert normalized["original_target_role"] == case
        assert normalized["is_security_role"] is True
        assert case in normalized["matched_aliases"]
        assert normalized["recommended_next_arguments"] == {
            "prepare_institution_interview": {
                "target_role": "정보통신",
                "job_family": "정보통신",
                "original_target_role": case,
            },
            "analyze_job_fit_report": {"target_role": "정보통신"},
        }


def test_security_job_aliases_are_detected_from_query_and_known_skills() -> None:
    normalized = normalize_job_role(
        query="KISA 정보보호 직무 면접 준비",
        known_skills=["웹 보안", "정보보안기사"],
        preparation_notes="개인정보보호 업무 경험을 면접 답변으로 정리하고 싶다.",
    )

    assert normalized["is_security_role"] is True
    assert normalized["normalized_job_family"] == "정보통신"
    assert normalized["normalized_target_role"] == "정보통신"
    assert normalized["matched_fields"] == {
        "query": ["정보보호"],
        "known_skills": ["웹 보안", "정보보안"],
        "preparation_notes": ["개인정보보호"],
    }
    assert normalized["recommended_next_arguments"] == {
        "prepare_institution_interview": {
            "target_role": "정보통신",
            "job_family": "정보통신",
            "original_target_role": "정보보호",
        },
        "analyze_job_fit_report": {"target_role": "정보통신"},
    }
    assert "payload_generation" in normalized["safe_context"]["disallowed_outputs"]


def test_non_security_job_role_is_kept_as_is() -> None:
    normalized = normalize_job_role(target_role="사업관리")

    assert normalized["normalized_job_family"] == "사업관리"
    assert normalized["normalized_target_role"] == "사업관리"
    assert normalized["is_security_role"] is False
    assert normalized["matched_aliases"] == []
    assert normalized["recommended_next_arguments"] == {
        "prepare_institution_interview": {
            "target_role": "사업관리",
            "job_family": "사업관리",
        },
        "analyze_job_fit_report": {"target_role": "사업관리"},
    }


def test_explicit_non_security_role_is_not_overridden_by_security_skills() -> None:
    normalized = normalize_job_role(
        target_role="회계",
        known_skills=["정보보안기사"],
        preparation_notes="개인정보보호 교육 이수 경험이 있다.",
    )

    assert normalized["normalized_job_family"] == "회계"
    assert normalized["normalized_target_role"] == "회계"
    assert normalized["is_security_role"] is False
    assert normalized["matched_fields"] == {
        "known_skills": ["정보보안"],
        "preparation_notes": ["개인정보보호"],
    }
    assert normalized["recommended_next_arguments"] == {
        "prepare_institution_interview": {"target_role": "회계", "job_family": "회계"},
        "analyze_job_fit_report": {"target_role": "회계"},
    }
    assert "보조 입력" in normalized["normalization_reason"]


@pytest.mark.parametrize("target_role", ["보안요원", "보안검색", "시설보안", "시설 보안"])
def test_physical_security_roles_are_not_normalized_to_information_communication(
    target_role: str,
) -> None:
    normalized = normalize_job_role(target_role=target_role)

    assert normalized["is_security_role"] is False
    assert normalized["normalized_target_role"] == target_role
    assert normalized["matched_aliases"] == []


def test_standalone_security_alias_uses_token_boundaries() -> None:
    normalized = normalize_job_role(query="공공기관 보안 직무 면접 준비")

    assert normalized["is_security_role"] is True
    assert normalized["matched_aliases"] == ["보안"]


def test_recommended_arguments_follow_each_downstream_tool_schema() -> None:
    normalized = normalize_job_role(target_role="정보보안")
    recommendations = normalized["recommended_next_arguments"]

    interview_arguments = recommendations["prepare_institution_interview"]
    job_fit_arguments = recommendations["analyze_job_fit_report"]
    assert set(interview_arguments) == {
        "target_role",
        "job_family",
        "original_target_role",
    }
    assert set(job_fit_arguments) == {"target_role"}
    assert set(interview_arguments) <= set(PREPARE_INSTITUTION_INTERVIEW_INPUT_SCHEMA["properties"])
    assert set(job_fit_arguments) <= set(ANALYZE_JOB_FIT_REPORT_INPUT_SCHEMA["properties"])


def test_normalize_job_role_tool_validates_arguments() -> None:
    tool = create_normalize_job_role_tool()

    result = tool.handler(
        {
            "target_role": "정보보안",
            "job_family": "정보보호",
            "known_skills": ["네트워크 보안"],
        }
    )

    assert result["original_target_role"] == "정보보안"
    assert result["original_job_family"] == "정보보호"
    assert result["normalized_job_family"] == "정보통신"

    with pytest.raises(ValueError, match="requires at least one input field"):
        tool.handler({})

    with pytest.raises(ValueError, match="unsupported normalize_job_role arguments"):
        tool.handler({"target_role": "정보보안", "extra": True})

    with pytest.raises(ValueError, match="expected list value for known_skills"):
        tool.handler({"target_role": "정보보안", "known_skills": "웹 보안"})

    with pytest.raises(ValueError, match="expected string value for target_role"):
        tool.handler({"target_role": 7})

    assert len(tool.input_schema["anyOf"]) == 5
    assert tool.annotations["readOnlyHint"] is True
