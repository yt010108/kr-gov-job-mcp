"""Lookup tools for source-specific code tables."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.codes import JobAlioCodeType, find_job_alio_codes, find_region_codes
from kr_gov_job_mcp.tools.registry import ToolDefinition, read_only_tool_annotations


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
