"""Lookup tools for source-specific code tables."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.codes import (
    find_institution_codes,
    find_region_codes,
    institution_match_confidence,
)
from kr_gov_job_mcp.tools.registry import ToolDefinition


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
LOOKUP_INSTITUTION_CODES_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "자연어 기관명, 약칭, 또는 잡알리오 기관 코드입니다.",
        },
    },
    "additionalProperties": False,
}


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
        description="자연어 지역명으로 잡알리오 근무지역 코드를 조회합니다.",
        input_schema=LOOKUP_REGION_CODES_INPUT_SCHEMA,
        handler=handler,
    )


def create_lookup_institution_codes_tool() -> ToolDefinition:
    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - {"query"})
        if unknown:
            raise ValueError(
                "unsupported lookup_institution_codes arguments: " + ", ".join(unknown)
            )

        query = _to_text(arguments.get("query"))
        matches = find_institution_codes(query)
        return {
            "source": "job_alio",
            "code_type": "pblntInstCd",
            "query": query,
            "result_count": len(matches),
            "matches": [
                {
                    **institution.public_dict(),
                    "confidence": institution_match_confidence(institution, query),
                }
                for institution in matches
            ],
        }

    return ToolDefinition(
        name="lookup_institution_codes",
        description="자연어 기관명 또는 약칭으로 잡알리오 기관 코드를 조회합니다.",
        input_schema=LOOKUP_INSTITUTION_CODES_INPUT_SCHEMA,
        handler=handler,
    )


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
