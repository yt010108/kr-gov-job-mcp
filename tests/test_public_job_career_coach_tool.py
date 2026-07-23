import pytest

from kr_gov_job_mcp.tools import (
    create_default_registry,
    create_public_job_career_coach_tool,
)
from kr_gov_job_mcp.tools.public_job_career_coach import (
    PUBLIC_JOB_CAREER_COACH_INPUT_SCHEMA,
)


def _tool_names(result: dict) -> list[str]:
    return [step["tool"] for step in result["workflow_steps"]]


def test_public_job_career_coach_schema_starts_without_required_input() -> None:
    schema = PUBLIC_JOB_CAREER_COACH_INPUT_SCHEMA

    assert "required" not in schema
    assert schema["additionalProperties"] is False
    assert schema["properties"]["support_mode"]["enum"] == [
        "beginner",
        "job_search",
        "application",
        "interview",
    ]
    assert schema["properties"]["career_level"]["enum"] == [
        "entry",
        "experienced",
        "any",
    ]
    assert schema["properties"]["job_id"]["pattern"] == r"\S"
    assert schema["properties"]["source_job_id"]["pattern"] == r"\S"
    assert schema["properties"]["recruitment_notice_sn"]["pattern"] == r"\S"
    assert schema["properties"]["auto_execute"]["default"] is True
    assert schema["properties"]["max_results"]["maximum"] == 3
    assert schema["properties"]["user_experiences"]["maxItems"] == 10
    assert schema["properties"]["user_experiences"]["items"]["maxLength"] == 2_000
    assert schema["properties"]["preparation_notes"]["maxLength"] == 4_000


def test_public_job_career_coach_empty_input_returns_korean_user_type_menu() -> None:
    tool = create_public_job_career_coach_tool()

    result = tool.handler({})

    assert result["status"] == "needs_user_selection"
    assert "공공기관 취업 준비 상태를 선택" in result["menu"]
    assert [choice["id"] for choice in result["choices"]] == [
        "beginner",
        "job_search",
        "application",
        "interview",
    ]
    assert [choice["number"] for choice in result["choices"]] == [1, 2, 3, 4]
    assert result["next_call"] == {
        "tool": "public_job_career_coach",
        "required_field": "support_mode",
    }


@pytest.mark.parametrize(
    ("arguments", "missing_fields"),
    [
        ({"support_mode": "beginner"}, ["career_level", "interests"]),
        (
            {
                "support_mode": "beginner",
                "career_level": "entry",
                "interests": ["정보통신"],
            },
            [],
        ),
        ({"support_mode": "job_search"}, ["target_role", "career_level"]),
        (
            {
                "support_mode": "job_search",
                "target_role": "전산",
                "career_level": "entry",
            },
            [],
        ),
        ({"support_mode": "application"}, ["job_id"]),
        ({"support_mode": "application", "source_job_id": "302324"}, []),
        ({"support_mode": "interview"}, ["institution_name", "target_role"]),
        (
            {
                "support_mode": "interview",
                "institution_name": "한국인터넷진흥원",
                "target_role": "정보통신",
            },
            [],
        ),
    ],
)
def test_public_job_career_coach_checks_only_selected_mode_requirements(
    arguments: dict,
    missing_fields: list[str],
) -> None:
    tool = create_public_job_career_coach_tool()

    plan_arguments = {**arguments, "auto_execute": False}
    result = tool.handler(plan_arguments)

    if missing_fields:
        assert result["status"] == "needs_more_information"
        assert result["missing_fields"] == missing_fields
        assert [question["field"] for question in result["questions"]] == missing_fields
        assert result["preserved_arguments"] == plan_arguments
        assert result["next_call"] == {
            "tool": "public_job_career_coach",
            "arguments": plan_arguments,
            "fields_to_add": missing_fields,
        }
        assert "menu" not in result
    else:
        assert result["status"] == "workflow_ready"
        assert result["preserved_arguments"] == plan_arguments
        assert result["next_call"] is None
        assert "menu" not in result


def test_public_job_career_coach_preserves_explicit_empty_lists_for_next_call() -> None:
    tool = create_public_job_career_coach_tool()

    result = tool.handler(
        {
            "support_mode": "beginner",
            "career_level": "entry",
            "interests": [],
            "known_skills": [],
            "auto_execute": False,
        }
    )

    assert result["status"] == "needs_more_information"
    assert result["missing_fields"] == ["interests"]
    assert result["preserved_arguments"] == {
        "support_mode": "beginner",
        "career_level": "entry",
        "interests": [],
        "known_skills": [],
        "auto_execute": False,
    }


def test_public_job_career_coach_returns_ordered_beginner_workflow_plan() -> None:
    tool = create_public_job_career_coach_tool()

    result = tool.handler(
        {
            "support_mode": "beginner",
            "career_level": "entry",
            "interests": ["디지털 서비스", "정보통신"],
            "auto_execute": False,
        }
    )

    assert result["status"] == "workflow_ready"
    assert _tool_names(result) == [
        "resolve_ncs_code",
        "search_public_jobs",
        "fetch_job_detail",
        "get_institution_average_salary",
        "analyze_job_fit_report",
    ]
    assert [step["order"] for step in result["workflow_steps"]] == [1, 2, 3, 4, 5]


def test_public_job_career_coach_adds_region_lookup_to_job_search_plan() -> None:
    tool = create_public_job_career_coach_tool()

    result = tool.handler(
        {
            "support_mode": "job_search",
            "target_role": "정보통신",
            "career_level": "entry",
            "known_skills": ["정보보안기사", "정보보안기사"],
            "regions": ["서울"],
            "auto_execute": False,
        }
    )

    assert result["status"] == "workflow_ready"
    assert result["preserved_arguments"]["known_skills"] == ["정보보안기사"]
    assert _tool_names(result) == [
        "resolve_ncs_code",
        "lookup_region_codes",
        "search_public_jobs",
        "fetch_job_detail",
        "get_institution_average_salary",
        "analyze_job_fit_report",
    ]


def test_public_job_career_coach_application_accepts_each_job_id_alias() -> None:
    tool = create_public_job_career_coach_tool()

    for field in ("job_id", "source_job_id", "recruitment_notice_sn"):
        result = tool.handler(
            {
                "support_mode": "application",
                field: "302324",
                "user_experiences": ["반복 오류의 원인을 로그로 분석한 경험"],
                "auto_execute": False,
            }
        )

        assert result["status"] == "workflow_ready"
        assert _tool_names(result) == [
            "fetch_job_detail",
            "get_institution_average_salary",
            "analyze_job_fit_report",
            "generate_star_answer_framework",
        ]


def test_public_job_career_coach_interview_uses_optional_inputs_safely() -> None:
    tool = create_public_job_career_coach_tool()
    required = {
        "support_mode": "interview",
        "institution_name": "한국인터넷진흥원",
        "target_role": "정보통신",
        "auto_execute": False,
    }

    basic_result = tool.handler(required)
    detailed_result = tool.handler(
        {
            **required,
            "job_id": "302324",
            "user_experiences": ["보안 점검 절차를 개선한 경험"],
        }
    )

    assert _tool_names(basic_result) == [
        "resolve_ncs_code",
        "analyze_institution_strategy",
        "analyze_institution_weakness",
        "prepare_institution_interview",
        "get_institution_average_salary",
    ]
    assert _tool_names(detailed_result) == [
        "fetch_job_detail",
        "resolve_ncs_code",
        "analyze_institution_strategy",
        "analyze_institution_weakness",
        "prepare_institution_interview",
        "get_institution_average_salary",
        "generate_star_answer_framework",
    ]


def test_public_job_career_coach_rejects_invalid_arguments() -> None:
    tool = create_public_job_career_coach_tool()

    with pytest.raises(ValueError, match="unsupported public_job_career_coach arguments"):
        tool.handler({"unknown": True})
    with pytest.raises(ValueError, match="support_mode must be one of"):
        tool.handler({"support_mode": "other"})
    with pytest.raises(ValueError, match="career_level must be one of"):
        tool.handler({"support_mode": "beginner", "career_level": "junior"})
    with pytest.raises(ValueError, match="expected list value for interests"):
        tool.handler(
            {
                "support_mode": "beginner",
                "career_level": "entry",
                "interests": "정보통신",
            }
        )
    with pytest.raises(ValueError, match="conflicting public_job_career_coach job ids"):
        tool.handler(
            {
                "support_mode": "application",
                "job_id": "302324",
                "source_job_id": "999999",
            }
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("target_role", "가" * 301, "target_role must be at most 300 characters"),
        (
            "user_experiences",
            [f"경험 {index}" for index in range(11)],
            "user_experiences must contain at most 10 items",
        ),
        (
            "user_experiences",
            ["가" * 2_001],
            "user_experiences items must be at most 2000 characters",
        ),
    ],
)
def test_public_job_career_coach_limits_free_form_input_size(
    field: str,
    value: object,
    message: str,
) -> None:
    tool = create_public_job_career_coach_tool()

    with pytest.raises(ValueError, match=message):
        tool.handler(
            {
                "support_mode": "application",
                "job_id": "302324",
                "auto_execute": False,
                field: value,
            }
        )


def test_default_registry_exposes_public_job_career_coach() -> None:
    registry = create_default_registry()

    tool = registry.get("public_job_career_coach")

    assert tool.input_schema == PUBLIC_JOB_CAREER_COACH_INPUT_SCHEMA
    assert tool.annotations["readOnlyHint"] is True
    assert tool.annotations["openWorldHint"] is True
