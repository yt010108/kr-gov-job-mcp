"""MCP-style tools for public job posting search."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from typing import Any

from kr_gov_job_mcp.clients.job_alio_web_client import JobAlioWebClient
from kr_gov_job_mcp.codes import resolve_region_code
from kr_gov_job_mcp.schemas.job import JobAlioSearchResult, JobAlioSummary
from kr_gov_job_mcp.tools.registry import ToolDefinition


SearchJobsRunner = Callable[..., JobAlioSearchResult]

SEARCH_PUBLIC_JOBS_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "keyword": {
            "type": "string",
            "description": "Search keyword for the Job-ALIO posting title.",
        },
        "page": {
            "type": "integer",
            "minimum": 1,
            "default": 1,
            "description": "1-based result page.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "default": 20,
            "description": "Rows per page.",
        },
        "ongoing_only": {
            "type": "boolean",
            "default": True,
            "description": "Only include postings currently open in Job-ALIO.",
        },
        "institution_code": {
            "type": "string",
            "description": "Job-ALIO institution code, for example B552909.",
        },
        "ncs_code": {
            "type": "string",
            "description": "Job-ALIO NCS code filter.",
        },
        "region_code": {
            "type": "string",
            "description": "Job-ALIO work region code filter.",
        },
        "region": {
            "type": "string",
            "description": "Natural-language work region name, for example 서울 or 서울특별시.",
        },
        "academic_condition_code": {
            "type": "string",
            "description": "Job-ALIO academic condition code filter.",
        },
        "employment_type_code": {
            "type": "string",
            "description": "Job-ALIO employment type code filter.",
        },
        "recruitment_type": {
            "type": "string",
            "description": "Job-ALIO recruitment type code filter.",
        },
        "replacement_only": {
            "type": "boolean",
            "description": "Only include replacement recruitment postings when true.",
        },
        "announcement_start_date": {
            "type": "string",
            "description": "Announcement start date filter, YYYY-MM-DD or YYYYMMDD.",
        },
        "announcement_end_date": {
            "type": "string",
            "description": "Announcement end date filter, YYYY-MM-DD or YYYYMMDD.",
        },
        "institution_type": {
            "type": "string",
            "description": "Job-ALIO institution type code filter.",
        },
        "institution_classification": {
            "type": "string",
            "description": "Job-ALIO institution classification code filter.",
        },
    },
    "additionalProperties": False,
}

_SUPPORTED_ARGUMENTS = set(SEARCH_PUBLIC_JOBS_INPUT_SCHEMA["properties"])
_TEXT_ARGUMENTS = {
    "keyword",
    "institution_code",
    "ncs_code",
    "academic_condition_code",
    "employment_type_code",
    "recruitment_type",
    "institution_type",
    "institution_classification",
}


def create_search_public_jobs_tool(search_jobs: SearchJobsRunner | None = None) -> ToolDefinition:
    """Create the first public job search tool.

    ``search_jobs`` is injectable so tests can verify tool behavior without touching the
    public Job-ALIO endpoint.
    """

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        search_kwargs, warnings, resolved_filters = _normalize_search_arguments(arguments)
        result = (
            search_jobs(**search_kwargs)
            if search_jobs is not None
            else _run_async(lambda: _search_job_alio(**search_kwargs))
        )
        return _serialize_search_result(
            result,
            query=search_kwargs,
            warnings=warnings,
            resolved_filters=resolved_filters,
        )

    return ToolDefinition(
        name="search_public_jobs",
        description=(
            "Search public-sector job postings from Job-ALIO and return normalized posting "
            "summaries with NCS mapping candidates."
        ),
        input_schema=SEARCH_PUBLIC_JOBS_INPUT_SCHEMA,
        handler=handler,
    )


async def _search_job_alio(**kwargs: Any) -> JobAlioSearchResult:
    async with JobAlioWebClient() as client:
        return await client.search_jobs(**kwargs)


def _normalize_search_arguments(
    arguments: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    unknown = sorted(set(arguments) - _SUPPORTED_ARGUMENTS)
    if unknown:
        raise ValueError("unsupported search_public_jobs arguments: " + ", ".join(unknown))

    warnings: list[str] = []
    resolved_filters: dict[str, Any] = {}
    kwargs: dict[str, Any] = {
        "page": _to_int(arguments.get("page"), default=1, minimum=1),
        "limit": _to_int(arguments.get("limit"), default=20, minimum=1, maximum=100),
        "ongoing_only": _to_bool(arguments.get("ongoing_only"), default=True),
    }

    for key in _TEXT_ARGUMENTS:
        value = _to_text(arguments.get(key))
        if value is not None:
            kwargs[key] = value

    region_code = _to_text(arguments.get("region_code"))
    region = _to_text(arguments.get("region"))
    if region:
        resolved_region = resolve_region_code(region)
        if region_code and region_code != resolved_region.code:
            raise ValueError(
                "region and region_code conflict: "
                f"{region} resolves to {resolved_region.code}, got {region_code}"
            )
        kwargs["region_code"] = resolved_region.code
        resolved_filters["region"] = resolved_region.public_dict()
    elif region_code:
        kwargs["region_code"] = region_code

    if "replacement_only" in arguments:
        kwargs["replacement_only"] = _to_bool(arguments.get("replacement_only"), default=False)

    for key in ("announcement_start_date", "announcement_end_date"):
        value = _to_query_date(arguments.get(key))
        if value is not None:
            kwargs[key] = value

    if kwargs["limit"] == 100:
        warnings.append("limit is capped at 100 for one Job-ALIO request.")

    return kwargs, warnings, resolved_filters


def _serialize_search_result(
    result: JobAlioSearchResult,
    *,
    query: Mapping[str, Any],
    warnings: list[str],
    resolved_filters: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "source": "job_alio",
        "query": dict(query),
        "resolved_filters": dict(resolved_filters),
        "page": result.page,
        "limit": result.limit,
        "total_count": result.total_count,
        "result_count": len(result.jobs),
        "jobs": [_serialize_job(job) for job in result.jobs],
        "warnings": warnings,
    }


def _serialize_job(job: JobAlioSummary) -> dict[str, Any]:
    return {
        "id": job.id,
        "source": "job_alio",
        "source_job_id": job.id,
        "institution_name": job.institution_name,
        "institution_code": job.institution_code,
        "title": job.title,
        "start_date": job.start_date,
        "end_date": job.end_date,
        "is_ongoing": job.is_ongoing,
        "employment_types": job.employment_types,
        "recruitment_type": job.recruitment_type,
        "headcount": job.headcount,
        "work_regions": job.work_regions,
        "source_url": job.source_url,
        "ncs_mappings": _ncs_mappings(job),
    }


def _ncs_mappings(job: JobAlioSummary) -> list[dict[str, Any]]:
    count = max(len(job.ncs_codes), len(job.ncs_categories))
    mappings: list[dict[str, Any]] = []
    for index in range(count):
        code = job.ncs_codes[index] if index < len(job.ncs_codes) else None
        display_name = job.ncs_categories[index] if index < len(job.ncs_categories) else None
        mappings.append(
            {
                "code": code,
                "display_name": display_name,
                "source_field": "ncsCdLst/ncsCdNmLst",
                "needs_verification": code is None or display_name is None,
            }
        )
    return mappings


def _run_async(coro_factory: Callable[[], Any]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())
    raise ValueError("search_public_jobs cannot run inside an active event loop")


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_int(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    if value is None or value == "":
        return default
    try:
        number = int(str(value))
    except ValueError as exc:
        raise ValueError(f"expected integer value: {value}") from exc
    if number < minimum:
        raise ValueError(f"expected integer >= {minimum}: {value}")
    if maximum is not None and number > maximum:
        return maximum
    return number


def _to_bool(value: Any, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "y", "yes"}:
        return True
    if text in {"0", "false", "n", "no"}:
        return False
    raise ValueError(f"expected boolean value: {value}")


def _to_query_date(value: Any) -> str | None:
    text = _to_text(value)
    if text is None:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) != 8:
        raise ValueError(f"expected date as YYYY-MM-DD or YYYYMMDD: {value}")
    return digits
