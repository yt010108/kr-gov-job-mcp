"""Lookup tools for source-specific code tables."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.codes import (
    JobAlioCodeType,
    find_job_alio_codes,
    find_region_codes,
    resolve_ncs_code,
)
from kr_gov_job_mcp.tools.registry import (
    ToolDefinition,
    non_blank_string_schema,
    read_only_tool_annotations,
)


LOOKUP_JOB_ALIO_CODES_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "code_type": {
            "type": "string",
            "enum": ["institution", "ncs"],
            "description": "조회할 Job-ALIO 코드 유형입니다. institution 또는 ncs를 지원합니다.",
        },
        "query": {
            "type": "string",
            "description": "기관명, 기관 약칭, NCS명, 직무 키워드 또는 코드입니다.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 50,
            "default": 20,
            "description": "반환할 최대 후보 수입니다.",
        },
    },
    "required": ["code_type", "query"],
    "additionalProperties": False,
}

LOOKUP_REGION_CODES_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "자연어 지역명 또는 잡알리오 근무지역 코드입니다.",
        },
    },
    "additionalProperties": False,
}

RESOLVE_NCS_CODE_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": non_blank_string_schema("자연어 직무명, NCS명, 약칭 또는 별칭입니다."),
        "target_role": non_blank_string_schema(
            "면접 또는 준비 리포트에서 사용한 원문 목표 직무명입니다."
        ),
        "job_family": non_blank_string_schema(
            "기관 분석 또는 준비 리포트에서 사용한 원문 직무군입니다."
        ),
        "known_skills": {
            "type": "array",
            "items": non_blank_string_schema("지원자의 보유 기술 또는 경험입니다."),
            "minItems": 1,
            "description": "직무명 입력이 없을 때 보조적으로 해석할 보유 기술 또는 경험 목록입니다.",
        },
        "preparation_notes": non_blank_string_schema(
            "직무 단서가 포함될 수 있는 지원자 준비 메모입니다."
        ),
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 25,
            "default": 5,
            "description": "반환할 최대 NCS 후보 수입니다.",
        },
    },
    "anyOf": [
        {"required": ["query"]},
        {"required": ["target_role"]},
        {"required": ["job_family"]},
        {"required": ["known_skills"]},
        {"required": ["preparation_notes"]},
    ],
    "additionalProperties": False,
}


def create_lookup_job_alio_codes_tool() -> ToolDefinition:
    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - {"code_type", "query", "limit"})
        if unknown:
            raise ValueError("unsupported lookup_job_alio_codes arguments: " + ", ".join(unknown))

        code_type = _code_type(arguments.get("code_type"))
        query = _required_text(arguments.get("query"), field="query")
        limit = _to_int(arguments.get("limit"), default=20, minimum=1, maximum=50)
        matches = find_job_alio_codes(code_type=code_type, query=query, limit=limit)
        warnings = []
        if not matches:
            warnings.append(
                "일치하는 Job-ALIO 코드 후보가 없습니다. 더 일반적인 기관명 또는 직무 키워드로 다시 조회하세요."
            )
        return {
            "source": "job_alio",
            "code_type": code_type,
            "query": query,
            "result_count": len(matches),
            "codes": [candidate.public_dict(score=score) for candidate, score in matches],
            "warnings": warnings,
        }

    return ToolDefinition(
        name="lookup_job_alio_codes",
        description=(
            "kr-gov-job-mcp 서비스에서 자연어 기관명, 기관 약칭, NCS명, 직무 키워드를 Job-ALIO 검색 후보로 "
            "조회합니다. NCS와 기관명 모두 Job-ALIO 검색 필터에 바로 사용할 수 있는 코드를 반환합니다."
        ),
        input_schema=LOOKUP_JOB_ALIO_CODES_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Lookup Job-ALIO Codes", open_world=False),
        handler=handler,
    )


def create_lookup_region_codes_tool() -> ToolDefinition:
    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - {"query"})
        if unknown:
            raise ValueError("unsupported lookup_region_codes arguments: " + ", ".join(unknown))

        query = _to_text(arguments.get("query"))
        matches = find_region_codes(query)
        return {
            "source": "job_alio",
            "code_type": "workRgnLst",
            "query": query,
            "result_count": len(matches),
            "matches": [region.public_dict() for region in matches],
        }

    return ToolDefinition(
        name="lookup_region_codes",
        description="kr-gov-job-mcp 서비스에서 자연어 지역명으로 잡알리오 근무지역 코드를 조회합니다.",
        input_schema=LOOKUP_REGION_CODES_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Lookup Region Codes", open_world=False),
        handler=handler,
    )


def create_resolve_ncs_code_tool() -> ToolDefinition:
    """Create the natural-language Job-ALIO NCS resolver tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - set(RESOLVE_NCS_CODE_INPUT_SCHEMA["properties"]))
        if unknown:
            raise ValueError("unsupported resolve_ncs_code arguments: " + ", ".join(unknown))

        query = _to_text(arguments.get("query"))
        target_role = _to_text(arguments.get("target_role"))
        job_family = _to_text(arguments.get("job_family"))
        known_skills = _text_list(arguments.get("known_skills"), field="known_skills")
        preparation_notes = _to_text(arguments.get("preparation_notes"))
        resolution_query = _resolution_query(
            query=query,
            target_role=target_role,
            job_family=job_family,
            known_skills=known_skills,
            preparation_notes=preparation_notes,
        )
        if resolution_query is None:
            raise ValueError(
                "resolve_ncs_code requires query, target_role, job_family, known_skills, or preparation_notes"
            )

        limit = _to_int(arguments.get("limit"), default=5, minimum=1, maximum=25)
        resolution = resolve_ncs_code(query=resolution_query, limit=limit)
        selected = resolution.selected
        report_context = _report_context(
            query=query,
            target_role=target_role,
            job_family=job_family,
            selected_code=selected.code if selected is not None else None,
            selected_name=selected.name if selected is not None else None,
        )
        return {
            "source": "job_alio",
            "original_query": query,
            "original_target_role": target_role,
            "original_job_family": job_family,
            "resolved_query": resolution.query,
            "candidates": [candidate.public_dict() for candidate in resolution.candidates],
            "selected_ncs_code": selected.code if selected is not None else None,
            "selected_ncs_name": selected.name if selected is not None else None,
            "matched_aliases": list(selected.matched_aliases) if selected is not None else [],
            "confidence": resolution.confidence,
            "search_public_jobs_arguments": (
                {"ncs_code": selected.code} if selected is not None else {}
            ),
            "report_context": report_context,
            "recommended_next_calls": _recommended_next_calls(
                query=resolution.query,
                selected=selected is not None,
            ),
            "warnings": list(resolution.warnings),
        }

    return ToolDefinition(
        name="resolve_ncs_code",
        description=(
            "kr-gov-job-mcp 서비스에서 자연어 직무명, NCS명, 약칭, 별칭을 Job-ALIO NCS 코드 후보로 "
            "해석합니다. 확정된 코드만 search_public_jobs.ncs_code에 전달하고, 면접·분석용 원문 직무명은 "
            "report_context에 보존합니다."
        ),
        input_schema=RESOLVE_NCS_CODE_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Resolve NCS Code", open_world=False),
        handler=handler,
    )


def _code_type(value: Any) -> JobAlioCodeType:
    text = _required_text(value, field="code_type")
    if text not in {"institution", "ncs"}:
        raise ValueError(f"unsupported lookup_job_alio_codes code_type: {text}")
    return text  # type: ignore[return-value]


def _required_text(value: Any, *, field: str) -> str:
    text = _to_text(value)
    if text is None:
        raise ValueError(f"{field} is required")
    return text


def _to_int(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if value is None or value == "":
        return default
    try:
        number = int(str(value))
    except ValueError as exc:
        raise ValueError(f"expected integer value: {value}") from exc
    if number < minimum:
        raise ValueError(f"expected integer >= {minimum}: {value}")
    return min(number, maximum)


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _text_list(value: Any, *, field: str) -> list[str]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    return [text for item in value if (text := _to_text(item)) is not None]


def _resolution_query(
    *,
    query: str | None,
    target_role: str | None,
    job_family: str | None,
    known_skills: list[str],
    preparation_notes: str | None,
) -> str | None:
    return target_role or job_family or query or " ".join([*known_skills, preparation_notes or ""]) or None


def _report_context(
    *,
    query: str | None,
    target_role: str | None,
    job_family: str | None,
    selected_code: str | None,
    selected_name: str | None,
) -> dict[str, str]:
    original_target_role = target_role or query or job_family
    context: dict[str, str] = {}
    if original_target_role is not None:
        context["original_target_role"] = original_target_role
        context["target_role"] = original_target_role
    if job_family is not None:
        context["original_job_family"] = job_family
    if selected_name is not None:
        context["job_family"] = selected_name
    elif job_family is not None:
        context["job_family"] = job_family
    if selected_code is not None:
        context["ncs_code"] = selected_code
    return context


def _recommended_next_calls(*, query: str, selected: bool) -> list[dict[str, Any]]:
    if selected:
        return []
    return [
        {
            "tool": "lookup_job_alio_codes",
            "arguments": {"code_type": "ncs", "query": query},
            "reason": "NCS 후보를 확인한 뒤 하나의 코드를 선택해 search_public_jobs.ncs_code로 전달하세요.",
        }
    ]
