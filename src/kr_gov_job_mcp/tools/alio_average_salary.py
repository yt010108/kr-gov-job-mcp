"""MCP tool for ALIO employee average compensation disclosures."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from kr_gov_job_mcp.analysis.alio_average_salary import (
    AlioAverageSalaryResult,
    fetch_alio_average_salary_sync,
)
from kr_gov_job_mcp.tools.registry import (
    ToolDefinition,
    non_blank_string_schema,
    read_only_tool_annotations,
)


GET_INSTITUTION_AVERAGE_SALARY_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": non_blank_string_schema("조회할 공공기관명입니다."),
        "alio_id": {
            "type": "string",
            "description": "ALIO 기관 코드(apbaId)입니다. 예: C1304",
        },
        "apba_id": {
            "type": "string",
            "description": "alio_id의 별칭입니다.",
        },
        "year": {
            "type": "integer",
            "description": "조회할 평균보수 연도입니다. 생략하면 가장 최근 결산값을 반환합니다.",
        },
    },
    "required": ["institution_name"],
    "additionalProperties": False,
}

_SUPPORTED_ARGUMENTS = set(GET_INSTITUTION_AVERAGE_SALARY_INPUT_SCHEMA["properties"])
AverageSalaryFetcher = Callable[..., AlioAverageSalaryResult]


def create_get_institution_average_salary_tool(
    fetch_average_salary: AverageSalaryFetcher | None = None,
) -> ToolDefinition:
    """Create the ALIO regular-disclosure average salary tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _SUPPORTED_ARGUMENTS)
        if unknown:
            raise ValueError(
                "unsupported get_institution_average_salary arguments: " + ", ".join(unknown)
            )

        institution_name = _required_text(arguments.get("institution_name"), "institution_name")
        alio_id = _optional_text(arguments.get("alio_id") or arguments.get("apba_id"))
        year = _optional_year(arguments.get("year"))
        result = (fetch_average_salary or fetch_alio_average_salary_sync)(
            institution_name=institution_name,
            alio_id=alio_id,
            year=year,
        )
        return result.as_dict()

    return ToolDefinition(
        name="get_institution_average_salary",
        description=(
            "kr-gov-job-mcp 서비스에서 ALIO 정기공시의 직원 평균보수(1인당 평균 보수액)를 "
            "기관별·연도별로 조회합니다. 기본값은 가장 최근 결산값이며, 예산값은 결산값과 구분해 반환합니다."
        ),
        input_schema=GET_INSTITUTION_AVERAGE_SALARY_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Get Institution Average Salary", open_world=True),
        handler=handler,
    )


def _required_text(value: Any, field: str) -> str:
    text = _optional_text(value)
    if text is None:
        raise ValueError(f"{field} is required")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_year(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except ValueError as exc:
        raise ValueError(f"expected integer value for year: {value}") from exc
