"""MCP tool for conservative STAR answer frameworks."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from kr_gov_job_mcp.analysis import generate_star_answer_framework
from kr_gov_job_mcp.schemas.star_answer import StarAnswerMode
from kr_gov_job_mcp.tools.registry import (
    ToolDefinition,
    non_blank_string_schema,
    read_only_tool_annotations,
)


GENERATE_STAR_ANSWER_FRAMEWORK_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": non_blank_string_schema("자기소개서 문항 또는 면접 질문입니다."),
        "user_experience": non_blank_string_schema(
            "지원자가 직접 제공한 경험 원문입니다. 제공되지 않은 성과·수치·역할은 생성하지 않습니다."
        ),
        "target_job": non_blank_string_schema("지원 대상 직무입니다."),
        "institution_name": non_blank_string_schema("지원 기관명입니다. 기관 사실 연결은 별도 근거가 필요합니다."),
        "ncs_competencies": {
            "type": "array",
            "items": non_blank_string_schema("공고 또는 직무기술서에서 확인한 NCS 역량 후보입니다."),
            "default": [],
            "description": "사용자의 보유 역량으로 단정하지 않는 NCS 연결 검토 후보입니다.",
        },
        "mode": {
            "type": "string",
            "enum": ["cover_letter", "interview", "both"],
            "default": "both",
            "description": "cover_letter, interview, both 중 하나입니다. PREP/AUTO는 지원하지 않습니다.",
        },
    },
    "required": ["question", "user_experience", "target_job"],
    "additionalProperties": False,
}

_SUPPORTED_ARGUMENTS = set(GENERATE_STAR_ANSWER_FRAMEWORK_INPUT_SCHEMA["properties"])
_VALID_MODES = {"cover_letter", "interview", "both"}


def create_generate_star_answer_framework_tool() -> ToolDefinition:
    """Create the user-evidence-only STAR framework tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _SUPPORTED_ARGUMENTS)
        if unknown:
            raise ValueError(
                "unsupported generate_star_answer_framework arguments: " + ", ".join(unknown)
            )

        question = _required_text(arguments.get("question"), "question")
        user_experience = _required_text(arguments.get("user_experience"), "user_experience")
        target_job = _required_text(arguments.get("target_job"), "target_job")
        institution_name = _optional_text(arguments, "institution_name")
        ncs_competencies = _text_list(arguments.get("ncs_competencies"), "ncs_competencies")
        mode = _mode(arguments.get("mode"))
        framework = generate_star_answer_framework(
            question=question,
            user_experience=user_experience,
            target_job=target_job,
            institution_name=institution_name,
            ncs_competencies=ncs_competencies,
            mode=mode,
        )
        return {
            "source": "star_answer_framework",
            "query": {
                "question": question,
                "target_job": target_job,
                "institution_name": institution_name,
                "ncs_competencies": ncs_competencies,
                "mode": mode,
            },
            **framework.model_dump(mode="json"),
        }

    return ToolDefinition(
        name="generate_star_answer_framework",
        description=(
            "kr-gov-job-mcp 서비스에서 사용자 제공 경험만으로 STAR 근거, 보완 질문, 과장 위험, "
            "면접·자기소개서용 답변 프레임을 생성합니다."
        ),
        input_schema=GENERATE_STAR_ANSWER_FRAMEWORK_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Generate STAR Answer Framework", open_world=False),
        handler=handler,
    )


def _required_text(value: Any, field: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _optional_text(arguments: Mapping[str, Any], field: str) -> str | None:
    if field not in arguments or arguments[field] is None:
        return None
    text = str(arguments[field]).strip()
    if not text:
        raise ValueError(f"{field} must be non-blank when provided")
    return text


def _text_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    values: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            raise ValueError(f"{field} items must be non-blank")
        if text not in values:
            values.append(text)
    return values


def _mode(value: Any) -> StarAnswerMode:
    mode = "both" if value is None else str(value).strip()
    if mode not in _VALID_MODES:
        raise ValueError("mode must be one of: cover_letter, interview, both")
    return cast(StarAnswerMode, mode)
