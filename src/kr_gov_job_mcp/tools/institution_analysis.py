"""MCP-style tools for institution analysis reports."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.analysis import (
    generate_institution_strategy_report,
    generate_institution_weakness_report,
    prepare_institution_analysis_input,
)
from kr_gov_job_mcp.schemas.institution import (
    InstitutionEvidence,
    InstitutionSignalCandidate,
)
from kr_gov_job_mcp.tools.registry import ToolDefinition


ANALYZE_INSTITUTION_STRATEGY_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": {
            "type": "string",
            "description": "Institution name to analyze.",
        },
        "year": {
            "type": "integer",
            "description": "Analysis year.",
        },
        "job_family": {
            "type": "string",
            "description": "Target job family, for example 정보보호 or 전산.",
        },
        "evidence": {
            "type": "array",
            "items": {"type": "object"},
            "default": [],
            "description": "Institution evidence candidates from ALIO, Cleaneye, homepage, or manual input.",
        },
        "signals": {
            "type": "array",
            "items": {"type": "object"},
            "default": [],
            "description": "Pre-extracted institution signal candidates with evidence.",
        },
    },
    "additionalProperties": False,
}


_STRATEGY_ARGUMENTS = set(ANALYZE_INSTITUTION_STRATEGY_INPUT_SCHEMA["properties"])

ANALYZE_INSTITUTION_WEAKNESS_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": {
            "type": "string",
            "description": "Institution name to analyze.",
        },
        "year": {
            "type": "integer",
            "description": "Analysis year.",
        },
        "evidence": {
            "type": "array",
            "items": {"type": "object"},
            "default": [],
            "description": "Improvement-task evidence candidates from ALIO, Cleaneye, or manual input.",
        },
        "signals": {
            "type": "array",
            "items": {"type": "object"},
            "default": [],
            "description": "Pre-extracted improvement signal candidates with evidence.",
        },
    },
    "additionalProperties": False,
}

_WEAKNESS_ARGUMENTS = set(ANALYZE_INSTITUTION_WEAKNESS_INPUT_SCHEMA["properties"])


def create_analyze_institution_strategy_tool() -> ToolDefinition:
    """Create the institution business-direction analysis tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _STRATEGY_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported analyze_institution_strategy arguments: " + ", ".join(unknown))

        institution_name = _required_text(arguments.get("institution_name"), "institution_name")
        year = _to_int(arguments.get("year"), field="year")
        job_family = _to_text(arguments.get("job_family"))
        evidence = _model_list(arguments.get("evidence"), InstitutionEvidence, field="evidence")
        signals = _model_list(arguments.get("signals"), InstitutionSignalCandidate, field="signals")
        analysis_input = prepare_institution_analysis_input(
            institution_name=institution_name,
            evidence=evidence,
            signals=signals,
        )
        report = generate_institution_strategy_report(
            analysis_input,
            year=year,
            job_family=job_family,
        )
        return {
            "source": "institution_analysis",
            "query": {
                "institution_name": institution_name,
                "year": year,
                "job_family": job_family,
            },
            **report.model_dump(mode="json"),
            "warnings": [],
        }

    return ToolDefinition(
        name="analyze_institution_strategy",
        description=(
            "Summarize institution business-direction signals and job connection points "
            "from explicit evidence, leaving unsupported claims as verification notes."
        ),
        input_schema=ANALYZE_INSTITUTION_STRATEGY_INPUT_SCHEMA,
        handler=handler,
    )


def create_analyze_institution_weakness_tool() -> ToolDefinition:
    """Create the institution improvement analysis tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _WEAKNESS_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported analyze_institution_weakness arguments: " + ", ".join(unknown))

        institution_name = _required_text(arguments.get("institution_name"), "institution_name")
        year = _to_int(arguments.get("year"), field="year")
        evidence = _model_list(arguments.get("evidence"), InstitutionEvidence, field="evidence")
        signals = _model_list(arguments.get("signals"), InstitutionSignalCandidate, field="signals")
        analysis_input = prepare_institution_analysis_input(
            institution_name=institution_name,
            evidence=evidence,
            signals=signals,
        )
        report = generate_institution_weakness_report(analysis_input, year=year)
        return {
            "source": "institution_analysis",
            "query": {
                "institution_name": institution_name,
                "year": year,
            },
            **report.model_dump(mode="json"),
            "warnings": [],
        }

    return ToolDefinition(
        name="analyze_institution_weakness",
        description=(
            "Summarize institution improvement-task signals from explicit evidence, "
            "using careful wording and verification notes for unsupported claims."
        ),
        input_schema=ANALYZE_INSTITUTION_WEAKNESS_INPUT_SCHEMA,
        handler=handler,
    )


def _model_list(value: Any, model_type: type, *, field: str) -> list[Any]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    return [model_type.model_validate(item) for item in value]


def _required_text(value: Any, field: str) -> str:
    text = _to_text(value)
    if text is None:
        raise ValueError(f"{field} is required")
    return text


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_int(value: Any, *, field: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except ValueError as exc:
        raise ValueError(f"expected integer value for {field}: {value}") from exc
