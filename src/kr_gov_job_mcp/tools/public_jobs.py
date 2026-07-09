"""MCP-style tools for public job posting search."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import date
from typing import Any

from kr_gov_job_mcp.analysis import generate_job_fit_report
from kr_gov_job_mcp.clients.job_alio_web_client import JobAlioWebClient
from kr_gov_job_mcp.codes import resolve_region_code
from kr_gov_job_mcp.schemas.job import (
    JobAlioAttachment,
    JobAlioDetail,
    JobAlioSearchResult,
    JobAlioStep,
    JobAlioSummary,
)
from kr_gov_job_mcp.schemas.job_fit import ApplicantReadinessInput, JobFitPreparationReport
from kr_gov_job_mcp.tools.registry import ToolDefinition, read_only_tool_annotations


SearchJobsRunner = Callable[..., JobAlioSearchResult]
FetchJobDetailRunner = Callable[[str], JobAlioDetail]

SEARCH_PUBLIC_JOBS_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "keyword": {
            "type": "string",
            "description": "잡알리오 채용공고 제목 검색어입니다.",
        },
        "page": {
            "type": "integer",
            "minimum": 1,
            "default": 1,
            "description": "조회할 결과 페이지입니다. 1부터 시작합니다.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "default": 20,
            "description": "한 페이지에 가져올 공고 수입니다.",
        },
        "ongoing_only": {
            "type": "boolean",
            "default": True,
            "description": "잡알리오 기준 현재 접수 중인 공고만 포함할지 여부입니다.",
        },
        "institution_code": {
            "type": "string",
            "description": (
                "잡알리오 기관 코드입니다. 자연어 기관명이나 약칭은 먼저 "
                "`lookup_job_alio_codes`로 조회하고, 코드가 확인된 후보만 입력합니다."
            ),
        },
        "ncs_code": {
            "type": "string",
            "description": (
                "잡알리오 NCS 코드 필터입니다. 자연어 직무명이나 NCS명은 먼저 "
                "`lookup_job_alio_codes`로 조회한 뒤 확인된 코드를 입력합니다."
            ),
        },
        "region_code": {
            "type": "string",
            "description": "잡알리오 근무지역 코드 필터입니다.",
        },
        "region": {
            "type": "string",
            "description": "자연어 근무지역명입니다. 예: 서울, 서울특별시",
        },
        "academic_condition_code": {
            "type": "string",
            "description": "잡알리오 학력 조건 코드 필터입니다.",
        },
        "employment_type_code": {
            "type": "string",
            "description": "잡알리오 고용형태 코드 필터입니다.",
        },
        "recruitment_type": {
            "type": "string",
            "description": "잡알리오 채용구분 코드 필터입니다.",
        },
        "replacement_only": {
            "type": "boolean",
            "description": "true이면 대체인력 채용 공고만 포함합니다.",
        },
        "announcement_start_date": {
            "type": "string",
            "description": "공고 시작일 필터입니다. YYYY-MM-DD 또는 YYYYMMDD 형식입니다.",
        },
        "announcement_end_date": {
            "type": "string",
            "description": "공고 종료일 필터입니다. YYYY-MM-DD 또는 YYYYMMDD 형식입니다.",
        },
        "institution_type": {
            "type": "string",
            "description": "잡알리오 기관 유형 코드 필터입니다.",
        },
        "institution_classification": {
            "type": "string",
            "description": "잡알리오 기관 분류 코드 필터입니다.",
        },
    },
    "additionalProperties": False,
}

FETCH_JOB_DETAIL_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_id": {
            "type": "string",
            "description": "search_public_jobs가 반환한 잡알리오 채용공고 ID입니다.",
        },
        "source_job_id": {
            "type": "string",
            "description": "search_public_jobs의 source_job_id를 그대로 넘길 때 쓰는 job_id 별칭입니다.",
        },
        "recruitment_notice_sn": {
            "type": "string",
            "description": "잡알리오 채용공고 일련번호(recrutPblntSn)입니다.",
        },
    },
    "additionalProperties": False,
}

ANALYZE_JOB_FIT_REPORT_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_id": {
            "type": "string",
            "description": "search_public_jobs가 반환한 잡알리오 채용공고 ID입니다.",
        },
        "source_job_id": {
            "type": "string",
            "description": "search_public_jobs의 source_job_id를 그대로 넘길 때 쓰는 job_id 별칭입니다.",
        },
        "recruitment_notice_sn": {
            "type": "string",
            "description": "잡알리오 채용공고 일련번호(recrutPblntSn)입니다.",
        },
        "target_role": {
            "type": "string",
            "description": "지원자가 목표로 하는 직무 또는 준비 방향입니다.",
        },
        "known_skills": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "지원자가 이미 보유한 기술, 자격증, 경험입니다.",
        },
        "preparation_notes": {
            "type": "string",
            "description": "준비 리포트에 반영할 지원자 메모입니다.",
        },
    },
    "additionalProperties": False,
}

_SUPPORTED_ARGUMENTS = set(SEARCH_PUBLIC_JOBS_INPUT_SCHEMA["properties"])
_FETCH_DETAIL_SUPPORTED_ARGUMENTS = set(FETCH_JOB_DETAIL_INPUT_SCHEMA["properties"])
_ANALYZE_JOB_FIT_SUPPORTED_ARGUMENTS = set(ANALYZE_JOB_FIT_REPORT_INPUT_SCHEMA["properties"])
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
            "kr-gov-job-mcp 서비스에서 잡알리오 공공기관 채용공고를 검색하고 정규화된 "
            "공고 요약과 NCS 매핑 후보를 반환합니다. 기관명, 기관 약칭, NCS명, "
            "직무 키워드처럼 자연어 코드 후보가 필요한 경우 먼저 `lookup_job_alio_codes`를 호출합니다. 기관명 후보는 "
            "`code`가 있는 경우에만 `institution_code`로 전달하고, `code`가 없으면 "
            "`fallback_search.arguments.keyword`의 기관명으로 검색합니다."
        ),
        input_schema=SEARCH_PUBLIC_JOBS_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Search Public Jobs", open_world=True),
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
            "kr-gov-job-mcp 서비스에서 잡알리오 공고 ID로 상세 공고를 조회하고 지원자격, "
            "첨부파일, 전형 단계, NCS 매핑 후보를 반환합니다."
        ),
        input_schema=FETCH_JOB_DETAIL_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Fetch Job Detail", open_world=True),
        handler=handler,
    )


def create_analyze_job_fit_report_tool(
    fetch_job_detail: FetchJobDetailRunner | None = None,
) -> ToolDefinition:
    """Create the MVP job preparation report tool from one Job-ALIO posting."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _ANALYZE_JOB_FIT_SUPPORTED_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported analyze_job_fit_report arguments: " + ", ".join(unknown))

        job_id = _normalize_detail_id(arguments, tool_name="analyze_job_fit_report")
        applicant = ApplicantReadinessInput(
            target_role=_to_text(arguments.get("target_role")),
            known_skills=_to_text_list(arguments.get("known_skills")),
            preparation_notes=_to_text(arguments.get("preparation_notes")),
        )
        detail = (
            fetch_job_detail(job_id)
            if fetch_job_detail is not None
            else _run_async("analyze_job_fit_report", lambda: _fetch_job_alio_detail(job_id))
        )
        report = generate_job_fit_report(detail, applicant=applicant)
        return _serialize_job_fit_report(
            report,
            query={
                "job_id": job_id,
                "target_role": applicant.target_role,
                "known_skills": applicant.known_skills,
            },
        )

    return ToolDefinition(
        name="analyze_job_fit_report",
        description=(
            "kr-gov-job-mcp 서비스에서 잡알리오 상세 공고를 바탕으로 준비 항목, 보완할 지식, "
            "근거 링크, 검증 필요 사항을 포함한 보수적인 MVP 준비 리포트를 생성합니다."
        ),
        input_schema=ANALYZE_JOB_FIT_REPORT_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Analyze Job Fit Report", open_world=True),
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
    if kwargs["ongoing_only"] is False:
        warnings.append(
            "ongoing_only=false disables the current-open filter; results may include both open and closed postings."
        )

    return kwargs, warnings, resolved_filters


def _normalize_detail_arguments(arguments: Mapping[str, Any]) -> str:
    unknown = sorted(set(arguments) - _FETCH_DETAIL_SUPPORTED_ARGUMENTS)
    if unknown:
        raise ValueError("unsupported fetch_job_detail arguments: " + ", ".join(unknown))

    return _normalize_detail_id(arguments, tool_name="fetch_job_detail")


def _normalize_detail_id(arguments: Mapping[str, Any], *, tool_name: str) -> str:
    values = {
        key: _to_text(arguments.get(key))
        for key in ("job_id", "source_job_id", "recruitment_notice_sn")
    }
    provided = {key: value for key, value in values.items() if value is not None}
    if not provided:
        raise ValueError(f"{tool_name} requires job_id")

    unique_values = set(provided.values())
    if len(unique_values) > 1:
        parts = ", ".join(f"{key}={value}" for key, value in provided.items())
        raise ValueError(f"conflicting {tool_name} ids: " + parts)
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
        "requested_filters": _requested_filter_metadata(query),
        "filter_notes": _filter_notes(query),
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


def _serialize_job_fit_report(
    report: JobFitPreparationReport,
    *,
    query: Mapping[str, Any],
) -> dict[str, Any]:
    payload = report.model_dump(mode="json")
    return {
        "source": "job_alio",
        "query": dict(query),
        **payload,
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
        "status_label": _job_status_label(job),
        "status_source": _job_status_source(job),
        "employment_types": job.employment_types,
        "recruitment_type": job.recruitment_type,
        "headcount": job.headcount,
        "work_regions": job.work_regions,
        "source_url": job.source_url,
        "ncs_mappings": _ncs_mappings(job),
    }


def _requested_filter_metadata(query: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ongoing_only": query.get("ongoing_only", True),
    }


def _filter_notes(query: Mapping[str, Any]) -> list[dict[str, Any]]:
    ongoing_only = query.get("ongoing_only", True)
    if ongoing_only is False:
        return [
            {
                "field": "ongoing_only",
                "value": False,
                "meaning": (
                    "잡알리오의 현재 접수 중 필터를 끈 상태입니다. "
                    "결과에는 진행 중 공고와 마감 공고가 함께 포함될 수 있습니다."
                ),
            }
        ]
    return [
        {
            "field": "ongoing_only",
            "value": True,
            "meaning": "잡알리오 기준 현재 접수 중인 공고만 요청합니다.",
        }
    ]


def _job_status_label(job: JobAlioSummary) -> str:
    if job.is_ongoing is True:
        return "open"
    if job.is_ongoing is False:
        return "closed"

    today = date.today()
    start_date = _parse_iso_date(job.start_date)
    end_date = _parse_iso_date(job.end_date)
    if end_date is not None and today > end_date:
        return "closed"
    if start_date is not None and today < start_date:
        return "upcoming"
    if end_date is not None and today <= end_date:
        return "open"
    return "unknown"


def _job_status_source(job: JobAlioSummary) -> str:
    if job.is_ongoing is not None:
        return "job_alio_ongoingYn"
    if _parse_iso_date(job.start_date) is not None or _parse_iso_date(job.end_date) is not None:
        return "date_range"
    return "unknown"


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


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


def _to_text_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value: {value}")
    return [text for item in value if (text := _to_text(item)) is not None]


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
