"""Lookup tools for source-specific code tables."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.codes import find_region_codes
from kr_gov_job_mcp.tools.registry import ToolDefinition


LOOKUP_REGION_CODES_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Natural-language region name or Job-ALIO region code.",
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
        description="Look up Job-ALIO work region codes by natural-language region name.",
        input_schema=LOOKUP_REGION_CODES_INPUT_SCHEMA,
        handler=handler,
    )


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

