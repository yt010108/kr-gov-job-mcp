"""MCP-style job role normalization tools."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.analysis import normalize_job_role
from kr_gov_job_mcp.tools.registry import ToolDefinition, read_only_tool_annotations


_NON_BLANK_STRING_SCHEMA = {"type": "string", "minLength": 1, "pattern": r"\S"}

NORMALIZE_JOB_ROLE_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target_role": {
            **_NON_BLANK_STRING_SCHEMA,
            "description": "지원자가 입력한 원문 목표 직무입니다. 예: 정보보안, 정보보호",
        },
        "job_family": {
            **_NON_BLANK_STRING_SCHEMA,
            "description": "지원자가 입력한 원문 직무군입니다.",
        },
        "query": {
            **_NON_BLANK_STRING_SCHEMA,
            "description": "사용자의 자연어 요청 전체입니다. 예: KISA 정보보안 면접준비",
        },
        "known_skills": {
            "type": "array",
            "items": _NON_BLANK_STRING_SCHEMA,
            "minItems": 1,
            "description": "지원자가 보유한 기술, 자격, 경험 표현입니다.",
        },
        "preparation_notes": {
            **_NON_BLANK_STRING_SCHEMA,
            "description": "지원자 준비 상태 또는 요청 메모입니다.",
        },
    },
    "anyOf": [
        {"required": ["target_role"]},
        {"required": ["job_family"]},
        {"required": ["query"]},
        {"required": ["known_skills"]},
        {"required": ["preparation_notes"]},
    ],
    "additionalProperties": False,
}

_NORMALIZE_JOB_ROLE_ARGUMENTS = set(NORMALIZE_JOB_ROLE_INPUT_SCHEMA["properties"])


def create_normalize_job_role_tool() -> ToolDefinition:
    """Create the job role normalization tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _NORMALIZE_JOB_ROLE_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported normalize_job_role arguments: " + ", ".join(unknown))

        target_role = _to_text(arguments.get("target_role"), field="target_role")
        job_family = _to_text(arguments.get("job_family"), field="job_family")
        query = _to_text(arguments.get("query"), field="query")
        known_skills = _text_list(arguments.get("known_skills"), field="known_skills")
        preparation_notes = _to_text(arguments.get("preparation_notes"), field="preparation_notes")
        if not any((target_role, job_family, query, known_skills, preparation_notes)):
            raise ValueError("normalize_job_role requires at least one input field")

        return normalize_job_role(
            target_role=target_role,
            job_family=job_family,
            query=query,
            known_skills=known_skills,
            preparation_notes=preparation_notes,
        )

    return ToolDefinition(
        name="normalize_job_role",
        description=(
            "kr-gov-job-mcp 서비스에서 직무명과 자연어 요청을 채용/NCS 맥락으로 정규화합니다. "
            "`정보보안`, `정보보호`, `보안`, "
            "`침해대응`, `침해사고 대응`, `취약점 분석`, `개인정보보호`, `정보통신 보안` 같은 "
            "보안 직무 표현이 있으면 `prepare_institution_interview` 또는 `analyze_job_fit_report` "
            "호출 전에 먼저 이 도구를 호출하고, `recommended_next_arguments`에서 호출할 후속 "
            "도구 이름에 해당하는 인자만 넘깁니다. "
            "이 도구는 면접/적합도 준비 범위만 안내하며 공격 절차, 페이로드, 무단 접근 방법은 "
            "출력 범위에서 제외합니다."
        ),
        input_schema=NORMALIZE_JOB_ROLE_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Normalize Job Role", open_world=False),
        handler=handler,
    )


def _text_list(value: Any, *, field: str) -> list[str]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    values: list[str] = []
    for item in value:
        text = _to_text(item, field=field)
        if text:
            values.append(text)
    return values


def _to_text(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"expected string value for {field}: {value}")
    text = value.strip()
    return text or None
