import pytest

from kr_gov_job_mcp.analysis import normalize_job_role
from kr_gov_job_mcp.tools.job_role import create_normalize_job_role_tool


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
            "target_role": "정보통신",
            "job_family": "정보통신",
            "original_target_role": case,
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
        "target_role": "정보통신",
        "job_family": "정보통신",
        "original_target_role": "정보보호",
    }
    assert "payload_generation" in normalized["safe_context"]["disallowed_outputs"]


def test_non_security_job_role_is_kept_as_is() -> None:
    normalized = normalize_job_role(target_role="사업관리")

    assert normalized["normalized_job_family"] == "사업관리"
    assert normalized["normalized_target_role"] == "사업관리"
    assert normalized["is_security_role"] is False
    assert normalized["matched_aliases"] == []
    assert normalized["recommended_next_arguments"] == {
        "target_role": "사업관리",
        "job_family": "사업관리",
    }


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
