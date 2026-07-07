"""MCP-style tools for public job posting search."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from typing import Any

from kr_gov_job_mcp.clients.job_alio_web_client import JobAlioWebClient
from kr_gov_job_mcp.codes import resolve_region_code
from kr_gov_job_mcp.schemas.job import (
    JobAlioAttachment,
    JobAlioDetail,
    JobAlioSearchResult,
    JobAlioStep,
    JobAlioSummary,
)
from kr_gov_job_mcp.tools.registry import ToolDefinition


SearchJobsRunner = Callable[..., JobAlioSearchResult]
FetchJobDetailRunner = Callable[[str], JobAlioDetail]

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

FETCH_JOB_DETAIL_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_id": {
            "type": "string",
            "description": "Job-ALIO recruitment notice id returned by search_public_jobs.",
        },
        "source_job_id": {
            "type": "string",
            "description": "Alias for job_id when passing search_public_jobs source_job_id.",
        },
        "recruitment_notice_sn": {
            "type": "string",
            "description": "Job-ALIO recrutPblntSn value.",
        },
    },
    "additionalProperties": False,
}

_SUPPORTED_ARGUMENTS = set(SEARCH_PUBLIC_JOBS_INPUT_SCHEMA["properties"])
_FETCH_DETAIL_SUPPORTED_ARGUMENTS = set(FETCH_JOB_DETAIL_INPUT_SCHEMA["properties"])
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
            else _run_async("search_public_jobs", lambda: _search_job_alio(**search_kwargs))
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


def create_fetch_job_detail_tool(
    fetch_job_detail: FetchJobDetailRunner | None = None,
) -> ToolDefinition:
    """Create the Job-ALIO posting detail tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        job_id = _normalize_detail_arguments(arguments)
        detail = (
            fetch_job_detail(job_id)
            if fetch_job_detail is not None
            else _run_async("fetch_job_detail", lambda: _fetch_job_alio_detail(job_id))
        )
        return _serialize_detail_result(detail, query={"job_id": job_id})

    return ToolDefinition(
        name="fetch_job_detail",
        description=(
            "Fetch one Job-ALIO posting detail by id and return normalized fields, "
            "attachments, screening steps, and NCS mapping candidates."
        ),
        input_schema=FETCH_JOB_DETAIL_INPUT_SCHEMA,
        handler=handler,
    )


async def _search_job_alio(**kwargs: Any) -> JobAlioSearchResult:
    async with JobAlioWebClient() as client:
        return await client.search_jobs(**kwargs)


async def _fetch_job_alio_detail(job_id: str) -> JobAlioDetail:
    async with JobAlioWebClient() as client:
        return await client.fetch_job_detail(job_id)


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


def _normalize_detail_arguments(arguments: Mapping[str, Any]) -> str:
    unknown = sorted(set(arguments) - _FETCH_DETAIL_SUPPORTED_ARGUMENTS)
    if unknown:
        raise ValueError("unsupported fetch_job_detail arguments: " + ", ".join(unknown))

    values = {
        key: _to_text(arguments.get(key))
        for key in ("job_id", "source_job_id", "recruitment_notice_sn")
    }
    provided = {key: value for key, value in values.items() if value is not None}
    if not provided:
        raise ValueError("fetch_job_detail requires job_id")

    unique_values = set(provided.values())
    if len(unique_values) > 1:
        parts = ", ".join(f"{key}={value}" for key, value in provided.items())
        raise ValueError("conflicting fetch_job_detail ids: " + parts)
    return next(iter(unique_values))


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


def _serialize_detail_result(
    detail: JobAlioDetail,
    *,
    query: Mapping[str, Any],
) -> dict[str, Any]:
    job = _serialize_job(detail)
    job.update(
        {
            "qualification": detail.qualification,
            "preferred_conditions": detail.preferred_conditions,
            "preference": detail.preference,
            "disqualification_reason": detail.disqualification_reason,
            "screening_procedure": detail.screening_procedure,
            "replacement_recruitment": detail.replacement_recruitment,
            "attachments": [_serialize_attachment(attachment) for attachment in detail.attachments],
            "steps": [_serialize_step(step) for step in detail.steps],
        }
    )
    return {
        "source": "job_alio",
        "query": dict(query),
        "job": job,
        "warnings": [],
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


def _serialize_attachment(attachment: JobAlioAttachment) -> dict[str, Any]:
    return {
        "sort_no": attachment.sort_no,
        "file_no": attachment.file_no,
        "name": attachment.name,
        "file_type": attachment.file_type,
        "url": attachment.url,
        "duty_description_candidate": _is_duty_description_candidate(attachment),
    }


def _serialize_step(step: JobAlioStep) -> dict[str, Any]:
    return {
        "sort_no": step.sort_no,
        "title": step.title,
        "step_sn": step.step_sn,
        "min_step_sn": step.min_step_sn,
        "max_step_sn": step.max_step_sn,
        "headcount": step.headcount,
        "applicant_count": step.applicant_count,
        "competition_rate": step.competition_rate,
        "occurrence_date": step.occurrence_date,
    }


def _is_duty_description_candidate(attachment: JobAlioAttachment) -> bool:
    if attachment.file_type == "C":
        return True
    name = attachment.name or ""
    return any(keyword in name for keyword in ("직무기술서", "직무설명", "NCS"))


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


def _run_async(tool_name: str, coro_factory: Callable[[], Any]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())
    raise ValueError(f"{tool_name} cannot run inside an active event loop")


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
