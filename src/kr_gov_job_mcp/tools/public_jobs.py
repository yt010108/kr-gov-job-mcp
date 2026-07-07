"""MCP-style tools for public job posting search."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
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
from kr_gov_job_mcp.tools.registry import ToolDefinition


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
            "description": "잡알리오 기관 코드입니다. 예: B552909",
        },
        "ncs_code": {
            "type": "string",
            "description": "잡알리오 NCS 코드 필터입니다.",
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

ANALYZE_PUBLIC_JOB_QUERY_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "사용자의 자연어 공공기관 채용 질문 원문입니다.",
        },
        "institution_name": {
            "type": "string",
            "description": "질문에서 분리된 기관명입니다. 명시하면 query 추정보다 우선합니다.",
        },
        "keyword": {
            "type": "string",
            "description": "직무, 공고, NCS 관련 검색 키워드입니다.",
        },
        "region": {
            "type": "string",
            "description": "자연어 근무지역명입니다. 예: 서울, 서울특별시",
        },
        "ongoing_only": {
            "type": "boolean",
            "description": "진행 중 공고만 우선 조회할지 여부입니다. 생략하면 query에서 추정합니다.",
        },
        "analysis_depth": {
            "type": "string",
            "enum": ["search_only", "detail", "fit_report"],
            "description": "검색만 할지, 상세 조회나 준비 리포트까지 이어갈지 지정합니다.",
        },
        "target_role": {
            "type": "string",
            "description": "준비 리포트에서 사용할 목표 직무입니다.",
        },
        "known_skills": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "지원자가 이미 보유한 기술, 자격증, 경험입니다.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "default": 3,
            "description": "선택할 공고 수입니다. 상세/리포트 자동 연결은 최대 5개까지 수행합니다.",
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}

_SUPPORTED_ARGUMENTS = set(SEARCH_PUBLIC_JOBS_INPUT_SCHEMA["properties"])
_FETCH_DETAIL_SUPPORTED_ARGUMENTS = set(FETCH_JOB_DETAIL_INPUT_SCHEMA["properties"])
_ANALYZE_JOB_FIT_SUPPORTED_ARGUMENTS = set(ANALYZE_JOB_FIT_REPORT_INPUT_SCHEMA["properties"])
_ANALYZE_QUERY_SUPPORTED_ARGUMENTS = set(ANALYZE_PUBLIC_JOB_QUERY_INPUT_SCHEMA["properties"])
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
_INSTITUTION_HINTS = {
    "한국인터넷진흥원": "한국인터넷진흥원",
    "kisa": "한국인터넷진흥원",
    "전남대병원": "전남대학교병원",
    "전남대 병원": "전남대학교병원",
    "전남대학교병원": "전남대학교병원",
    "한국농수산식품유통공사": "한국농수산식품유통공사",
    "농수산식품유통공사": "한국농수산식품유통공사",
    "한전": "한국전력공사",
    "한국전력공사": "한국전력공사",
}
_ROLE_HINTS = [
    "정보보호",
    "정보통신",
    "전산",
    "데이터",
    "보안",
    "행정",
    "사무",
    "사업관리",
]


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
            "잡알리오 공공기관 채용공고를 검색하고 정규화된 공고 요약과 NCS 매핑 후보를 "
            "반환합니다."
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
            "잡알리오 공고 ID로 상세 공고를 조회하고 지원자격, 첨부파일, 전형 단계, "
            "NCS 매핑 후보를 반환합니다."
        ),
        input_schema=FETCH_JOB_DETAIL_INPUT_SCHEMA,
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
            "잡알리오 상세 공고를 바탕으로 준비 항목, 보완할 지식, 근거 링크, "
            "검증 필요 사항을 포함한 보수적인 MVP 준비 리포트를 생성합니다."
        ),
        input_schema=ANALYZE_JOB_FIT_REPORT_INPUT_SCHEMA,
        handler=handler,
    )


def create_analyze_public_job_query_tool(
    search_jobs: SearchJobsRunner | None = None,
    fetch_job_detail: FetchJobDetailRunner | None = None,
) -> ToolDefinition:
    """Create a chat-oriented public job search orchestration tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _ANALYZE_QUERY_SUPPORTED_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported analyze_public_job_query arguments: " + ", ".join(unknown))

        query = _required_text(arguments.get("query"), field="query")
        limit = _to_int(arguments.get("limit"), default=3, minimum=1, maximum=5)
        institution_name = _to_text(arguments.get("institution_name")) or _extract_institution(query)
        target_role = _to_text(arguments.get("target_role")) or _extract_role(query)
        keyword = _to_text(arguments.get("keyword")) or target_role
        region = _to_text(arguments.get("region"))
        ongoing_only = (
            _to_bool(arguments.get("ongoing_only"), default=True)
            if "ongoing_only" in arguments
            else _infer_ongoing_only(query)
        )
        analysis_depth = _analysis_depth(arguments.get("analysis_depth"), query)
        known_skills = _to_text_list(arguments.get("known_skills"))
        warnings: list[str] = []

        selected_jobs: list[JobAlioSummary] = []
        search_attempts: list[dict[str, Any]] = []
        for attempt in _query_search_plan(
            institution_name=institution_name,
            keyword=keyword,
            region=region,
            ongoing_only=ongoing_only,
            limit=limit,
        ):
            result = (
                search_jobs(**attempt["arguments"])
                if search_jobs is not None
                else _run_async(
                    "analyze_public_job_query",
                    lambda attempt=attempt: _search_job_alio(**attempt["arguments"]),
                )
            )
            search_attempts.append(
                {
                    "reason": attempt["reason"],
                    "arguments": attempt["arguments"],
                    "total_count": result.total_count,
                    "result_count": len(result.jobs),
                }
            )
            if result.jobs:
                selected_jobs = result.jobs[:limit]
                break

        job_details: list[dict[str, Any]] = []
        fit_reports: list[dict[str, Any]] = []
        if selected_jobs and analysis_depth in {"detail", "fit_report"}:
            for job in selected_jobs:
                detail = _load_detail(job.id, fetch_job_detail)
                detail_payload = _serialize_detail_result(detail, query={"job_id": job.id})
                job_details.append(detail_payload["job"])
                if analysis_depth == "fit_report":
                    applicant = ApplicantReadinessInput(
                        target_role=target_role or keyword,
                        known_skills=known_skills,
                        preparation_notes=query,
                    )
                    report = generate_job_fit_report(detail, applicant=applicant)
                    fit_reports.append(
                        _serialize_job_fit_report(
                            report,
                            query={
                                "job_id": job.id,
                                "target_role": applicant.target_role,
                                "known_skills": applicant.known_skills,
                            },
                        )
                    )

        if not selected_jobs:
            warnings.append("검색 결과가 없거나 현재 검색 방식으로 찾지 못했습니다.")

        return {
            "source": "public_job_query_orchestration",
            "interpreted_query": {
                "query": query,
                "institution_name": institution_name,
                "keyword": keyword,
                "region": region,
                "ongoing_only": ongoing_only,
                "analysis_depth": analysis_depth,
                "target_role": target_role,
            },
            "search_attempts": search_attempts,
            "selected_jobs": [_serialize_job(job) for job in selected_jobs],
            "job_details": job_details,
            "fit_reports": fit_reports,
            "institution_analysis_status": _institution_analysis_status(query),
            "no_result_diagnostics": _no_result_diagnostics(
                selected_jobs=selected_jobs,
                institution_name=institution_name,
                keyword=keyword,
                ongoing_only=ongoing_only,
            ),
            "next_actions": _next_actions(
                selected_jobs=selected_jobs,
                analysis_depth=analysis_depth,
                institution_name=institution_name,
            ),
            "warnings": warnings,
        }

    return ToolDefinition(
        name="analyze_public_job_query",
        description=(
            "사용자의 자연어 공공기관 채용 질문을 해석해 공고 검색, 상세 조회, 준비 리포트 생성을 "
            "한 응답으로 묶고 검색 시도와 다음 액션을 반환합니다."
        ),
        input_schema=ANALYZE_PUBLIC_JOB_QUERY_INPUT_SCHEMA,
        handler=handler,
    )


async def _search_job_alio(**kwargs: Any) -> JobAlioSearchResult:
    async with JobAlioWebClient() as client:
        return await client.search_jobs(**kwargs)


async def _fetch_job_alio_detail(job_id: str) -> JobAlioDetail:
    async with JobAlioWebClient() as client:
        return await client.fetch_job_detail(job_id)


def _load_detail(
    job_id: str,
    fetch_job_detail: FetchJobDetailRunner | None,
) -> JobAlioDetail:
    if fetch_job_detail is not None:
        return fetch_job_detail(job_id)
    return _run_async("analyze_public_job_query", lambda: _fetch_job_alio_detail(job_id))


def _query_search_plan(
    *,
    institution_name: str | None,
    keyword: str | None,
    region: str | None,
    ongoing_only: bool,
    limit: int,
) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []

    def add(reason: str, **kwargs: Any) -> None:
        normalized = {
            key: value
            for key, value in {
                "page": 1,
                "limit": limit,
                "ongoing_only": ongoing_only,
                "region": region,
                **kwargs,
            }.items()
            if value is not None
        }
        signature = tuple(sorted(normalized.items()))
        if any(tuple(sorted(attempt["arguments"].items())) == signature for attempt in attempts):
            return
        attempts.append({"reason": reason, "arguments": normalized})

    if institution_name:
        add("기관명으로 공고 제목 검색", keyword=institution_name)
        compact = institution_name.replace(" ", "")
        if compact != institution_name:
            add("기관명 공백 제거 후 재검색", keyword=compact)
    if keyword and keyword != institution_name:
        add("직무/키워드로 공고 제목 검색", keyword=keyword)
    if not attempts:
        add("필터 없이 최신 공고 검색")
    if ongoing_only:
        for attempt in list(attempts):
            retry_arguments = dict(attempt["arguments"])
            retry_arguments["ongoing_only"] = False
            signature = tuple(sorted(retry_arguments.items()))
            if any(tuple(sorted(item["arguments"].items())) == signature for item in attempts):
                continue
            attempts.append(
                {
                    "reason": attempt["reason"] + " 후 진행 중 제한 해제",
                    "arguments": retry_arguments,
                }
            )
    return attempts


def _analysis_depth(value: Any, query: str) -> str:
    explicit = _to_text(value)
    if explicit is not None:
        if explicit not in {"search_only", "detail", "fit_report"}:
            raise ValueError(f"unsupported analysis_depth: {explicit}")
        return explicit
    if any(keyword in query for keyword in ("분석", "요구 역량", "우대", "준비", "포인트")):
        return "fit_report"
    if any(keyword in query for keyword in ("상세", "봐줘", "알려줘")):
        return "detail"
    return "search_only"


def _infer_ongoing_only(query: str) -> bool:
    if any(keyword in query for keyword in ("진행중인거 말고", "진행 중인거 말고", "마감", "최근 공고")):
        return False
    return True


def _extract_institution(query: str) -> str | None:
    lowered = query.lower()
    for hint, institution_name in _INSTITUTION_HINTS.items():
        if hint.lower() in lowered:
            return institution_name
    return None


def _extract_role(query: str) -> str | None:
    lowered = query.lower()
    for role in _ROLE_HINTS:
        if role.lower() in lowered:
            return role
    return None


def _institution_analysis_status(query: str) -> dict[str, Any]:
    if any(keyword in query for keyword in ("기관 분석", "사업 방향", "약점", "개선 과제")):
        return {
            "status": "needs_evidence",
            "message": (
                "기관 사업 방향이나 개선 과제 분석은 ALIO, 홈페이지, Cleaneye 같은 원문 "
                "evidence를 먼저 연결해야 합니다."
            ),
            "recommended_sources": ["alio_disclosure", "institution_homepage", "cleaneye"],
        }
    return {"status": "not_requested"}


def _no_result_diagnostics(
    *,
    selected_jobs: list[JobAlioSummary],
    institution_name: str | None,
    keyword: str | None,
    ongoing_only: bool,
) -> dict[str, Any] | None:
    if selected_jobs:
        return None
    possible_causes = [
        "Job-ALIO 제목 검색어와 기관명 또는 약칭이 정확히 맞지 않을 수 있습니다.",
        "공고가 접수 중이 아니거나 최근 마감된 공고일 수 있습니다.",
    ]
    if institution_name:
        possible_causes.append("기관명 기반 institution_code 조회가 필요할 수 있습니다.")
    if keyword:
        possible_causes.append("키워드가 제목이 아니라 NCS/우대사항/상세 본문에만 있을 수 있습니다.")
    return {
        "reason": "검색 결과가 없습니다.",
        "ongoing_only": ongoing_only,
        "possible_causes": possible_causes,
        "suggested_next_queries": [
            "기관명 alias 또는 institution_code로 재검색",
            "ongoing_only=false로 마감 공고 포함 재검색",
            "NCS/상세 필드까지 포함하는 키워드 검색",
        ],
    }


def _next_actions(
    *,
    selected_jobs: list[JobAlioSummary],
    analysis_depth: str,
    institution_name: str | None,
) -> list[str]:
    if not selected_jobs:
        actions = [
            "검색어를 공식 기관명 또는 공고 제목 일부로 바꿔 다시 시도합니다.",
            "마감 공고를 포함하려면 ongoing_only=false로 재검색합니다.",
        ]
        if institution_name:
            actions.append("기관명 alias와 institution_code lookup 결과를 연결하면 검색 정확도가 높아집니다.")
        return actions
    if analysis_depth == "search_only":
        return ["선택된 source_job_id로 fetch_job_detail을 호출하면 상세 공고를 볼 수 있습니다."]
    if analysis_depth == "detail":
        return ["선택된 source_job_id로 analyze_job_fit_report를 호출하면 준비 리포트를 만들 수 있습니다."]
    return ["fit_reports의 preparation_items와 knowledge_gaps를 지원자의 경험과 연결해 검토합니다."]


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


def _required_text(value: Any, *, field: str) -> str:
    text = _to_text(value)
    if text is None:
        raise ValueError(f"{field} is required")
    return text


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
