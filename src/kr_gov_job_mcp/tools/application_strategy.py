"""Integrated public-sector application strategy orchestration tool."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from kr_gov_job_mcp.tools.code_lookup import (
    create_lookup_job_alio_codes_tool,
    create_resolve_ncs_code_tool,
)
from kr_gov_job_mcp.tools.institution_analysis import (
    create_analyze_institution_strategy_tool,
    create_analyze_institution_weakness_tool,
    create_prepare_institution_interview_tool,
)
from kr_gov_job_mcp.tools.ncs_mapping import create_map_ncs_competencies_tool
from kr_gov_job_mcp.tools.public_jobs import (
    create_analyze_job_fit_report_tool,
    create_search_public_jobs_tool,
)
from kr_gov_job_mcp.tools.registry import (
    ToolDefinition,
    non_blank_string_schema,
    read_only_tool_annotations,
)


ToolRunner = Callable[[Mapping[str, Any]], Mapping[str, Any]]

PREPARE_APPLICATION_STRATEGY_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": non_blank_string_schema("지원할 공공기관 이름 또는 약칭입니다."),
        "target_role": non_blank_string_schema("지원자가 목표로 하는 자연어 직무입니다."),
        "region": {"type": "string", "description": "선택적인 근무지역명입니다."},
        "known_skills": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "지원자가 보유한 기술, 자격, 경험입니다.",
        },
        "preparation_notes": {
            "type": "string",
            "description": "지원 준비 상태나 경험에 대한 추가 메모입니다.",
        },
        "ongoing_only": {
            "type": "boolean",
            "default": True,
            "description": "현재 접수 중인 공고만 검색할지 여부입니다.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "default": 3,
            "description": "검색하고 개별 분석할 최대 공고 후보 수입니다.",
        },
        "year": {"type": "integer", "description": "기관 분석 기준 연도입니다."},
        "include_ncs_competencies": {
            "type": "boolean",
            "default": True,
            "description": "공고별 NCS/KSA 매핑 결과를 포함할지 여부입니다.",
        },
        "include_institution_analysis": {
            "type": "boolean",
            "default": True,
            "description": "기관 전략과 개선 과제 분석을 포함할지 여부입니다.",
        },
        "include_interview_cards": {
            "type": "boolean",
            "default": True,
            "description": "기관 근거 기반 면접 준비 카드를 포함할지 여부입니다.",
        },
        "fetch_live_alio": {
            "type": "boolean",
            "default": True,
            "description": "기관 분석에 ALIO 실시간 조회를 허용할지 여부입니다.",
        },
    },
    "required": ["institution_name", "target_role"],
    "additionalProperties": False,
}

_SUPPORTED_ARGUMENTS = set(PREPARE_APPLICATION_STRATEGY_INPUT_SCHEMA["properties"])


def create_prepare_application_strategy_tool(
    *,
    lookup_institution: ToolRunner | None = None,
    resolve_ncs: ToolRunner | None = None,
    search_jobs: ToolRunner | None = None,
    analyze_job_fit: ToolRunner | None = None,
    map_ncs: ToolRunner | None = None,
    analyze_strategy: ToolRunner | None = None,
    analyze_weakness: ToolRunner | None = None,
    prepare_interview: ToolRunner | None = None,
) -> ToolDefinition:
    lookup_institution = lookup_institution or _handler(create_lookup_job_alio_codes_tool())
    resolve_ncs = resolve_ncs or _handler(create_resolve_ncs_code_tool())
    search_jobs = search_jobs or _handler(create_search_public_jobs_tool())
    analyze_job_fit = analyze_job_fit or _handler(create_analyze_job_fit_report_tool())
    map_ncs = map_ncs or _handler(create_map_ncs_competencies_tool())
    analyze_strategy = analyze_strategy or _handler(create_analyze_institution_strategy_tool())
    analyze_weakness = analyze_weakness or _handler(create_analyze_institution_weakness_tool())
    prepare_interview = prepare_interview or _handler(create_prepare_institution_interview_tool())

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _SUPPORTED_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported prepare_application_strategy arguments: " + ", ".join(unknown))

        institution_name = _required_text(arguments.get("institution_name"), "institution_name")
        target_role = _required_text(arguments.get("target_role"), "target_role")
        known_skills = _text_list(arguments.get("known_skills"), field="known_skills")
        preparation_notes = _to_text(arguments.get("preparation_notes"))
        limit = _to_int(arguments.get("limit"), default=3, minimum=1, maximum=5)
        ongoing_only = _to_bool(arguments.get("ongoing_only"), default=True)
        include_ncs = _to_bool(arguments.get("include_ncs_competencies"), default=True)
        include_institution = _to_bool(
            arguments.get("include_institution_analysis"), default=True
        )
        include_interview = _to_bool(arguments.get("include_interview_cards"), default=True)
        fetch_live_alio = _to_bool(arguments.get("fetch_live_alio"), default=True)
        year = _optional_int(arguments.get("year"), field="year")
        region = _to_text(arguments.get("region"))

        warnings: list[str] = []
        verification_notes: list[dict[str, str]] = []
        institution_resolution = _safe_call(
            lookup_institution,
            {"code_type": "institution", "query": institution_name, "limit": 5},
            stage="institution_resolution",
            warnings=warnings,
        )
        ncs_resolution = _safe_call(
            resolve_ncs,
            {"target_role": target_role, "known_skills": known_skills, "limit": 5},
            stage="ncs_resolution",
            warnings=warnings,
        )
        institution_code = _selected_institution_code(institution_resolution)
        ncs_code = _to_text(ncs_resolution.get("selected_ncs_code"))
        ncs_name = _to_text(ncs_resolution.get("selected_ncs_name"))

        if institution_code is None:
            verification_notes.append(
                _note(
                    "institution_code",
                    "기관명을 하나의 Job-ALIO 기관 코드로 확정하지 못했습니다.",
                    "institution_resolution 후보를 확인한 뒤 다시 호출합니다.",
                )
            )
        if ncs_code is None:
            verification_notes.append(
                _note(
                    "ncs_code",
                    "직무를 하나의 Job-ALIO NCS 코드로 확정하지 못했습니다.",
                    "ncs_resolution 후보를 확인한 뒤 다시 호출합니다.",
                )
            )

        query = {
            "institution_name": institution_name,
            "institution_code": institution_code,
            "target_role": target_role,
            "ncs_code": ncs_code,
            "ncs_name": ncs_name,
            "region": region,
            "known_skills": known_skills,
            "ongoing_only": ongoing_only,
            "limit": limit,
            "year": year,
        }
        if institution_code is None or ncs_code is None:
            return _result(
                query=query,
                institution_resolution=institution_resolution,
                ncs_resolution=ncs_resolution,
                verification_notes=verification_notes,
                warnings=warnings,
            )

        search_arguments: dict[str, Any] = {
            "institution_code": institution_code,
            "ncs_code": ncs_code,
            "ongoing_only": ongoing_only,
            "limit": limit,
        }
        if region:
            search_arguments["region"] = region
        search_result = _safe_call(
            search_jobs,
            search_arguments,
            stage="job_search",
            warnings=warnings,
        )
        jobs = list(search_result.get("jobs") or [])
        job_reports: list[dict[str, Any]] = []
        for job in jobs:
            job_id = _to_text(job.get("id") or job.get("source_job_id"))
            if job_id is None:
                warnings.append("job_analysis: 공고 ID가 없는 후보는 분석에서 제외했습니다.")
                continue
            fit_report = _safe_call(
                analyze_job_fit,
                {
                    "job_id": job_id,
                    "target_role": target_role,
                    "known_skills": known_skills,
                    "preparation_notes": preparation_notes,
                },
                stage=f"job_fit:{job_id}",
                warnings=warnings,
            )
            ncs_mapping = (
                _safe_call(
                    map_ncs,
                    {"job_id": job_id},
                    stage=f"ncs_mapping:{job_id}",
                    warnings=warnings,
                )
                if include_ncs
                else None
            )
            job_reports.append(
                {"job_id": job_id, "job": job, "fit_report": fit_report, "ncs": ncs_mapping}
            )

        institution_arguments: dict[str, Any] = {
            "institution_name": institution_name,
            "job_family": ncs_name or target_role,
            "target_role": target_role,
            "ncs_code": ncs_code,
            "fetch_live_alio": fetch_live_alio,
        }
        if year is not None:
            institution_arguments["year"] = year
        institution_strategy = None
        institution_weakness = None
        if include_institution:
            institution_strategy = _safe_call(
                analyze_strategy,
                institution_arguments,
                stage="institution_strategy",
                warnings=warnings,
            )
            weakness_arguments = {
                key: value
                for key, value in institution_arguments.items()
                if key in {"institution_name", "year", "fetch_live_alio"}
            }
            institution_weakness = _safe_call(
                analyze_weakness,
                weakness_arguments,
                stage="institution_weakness",
                warnings=warnings,
            )
        interview_cards = None
        if include_interview:
            interview_cards = _safe_call(
                prepare_interview,
                institution_arguments,
                stage="interview_cards",
                warnings=warnings,
            )

        if len(jobs) > 1:
            verification_notes.append(
                _note(
                    "recommended_job_ids",
                    "여러 공고 후보를 모두 분석했으며 하나를 최종 선택하지 않았습니다.",
                    "마감일, 고용형태, 근무지역과 공고별 준비 항목을 비교해 선택합니다.",
                )
            )
        if not jobs and search_result.get("diagnostics"):
            verification_notes.append(
                _note(
                    "job_candidates",
                    "검색 조건에 맞는 공고가 없습니다.",
                    "diagnostics의 recommended_next_calls를 확인합니다.",
                )
            )

        payload = _result(
            query=query,
            institution_resolution=institution_resolution,
            ncs_resolution=ncs_resolution,
            search_result=search_result,
            job_reports=job_reports,
            institution_strategy=institution_strategy,
            institution_weakness=institution_weakness,
            interview_cards=interview_cards,
            verification_notes=verification_notes,
            warnings=warnings,
        )
        payload["evidence_links"] = _collect_evidence_links(payload)
        return payload

    return ToolDefinition(
        name="prepare_application_strategy",
        description=(
            "kr-gov-job-mcp 서비스에서 기관명과 자연어 직무를 코드로 해석하고 Job-ALIO 공고 후보, "
            "공고별 적합도·NCS 역량, 기관 분석, 면접 카드를 근거와 확인 사항을 보존해 통합합니다."
        ),
        input_schema=PREPARE_APPLICATION_STRATEGY_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Prepare Application Strategy", open_world=True),
        handler=handler,
    )


def _result(
    *,
    query: Mapping[str, Any],
    institution_resolution: Mapping[str, Any],
    ncs_resolution: Mapping[str, Any],
    search_result: Mapping[str, Any] | None = None,
    job_reports: list[dict[str, Any]] | None = None,
    institution_strategy: Mapping[str, Any] | None = None,
    institution_weakness: Mapping[str, Any] | None = None,
    interview_cards: Mapping[str, Any] | None = None,
    verification_notes: list[dict[str, str]],
    warnings: list[str],
) -> dict[str, Any]:
    jobs = list((search_result or {}).get("jobs") or [])
    return {
        "source": "application_strategy",
        "query": dict(query),
        "institution_resolution": dict(institution_resolution),
        "ncs_resolution": dict(ncs_resolution),
        "job_candidates": jobs,
        "recommended_job_ids": [job.get("id") for job in jobs if job.get("id")],
        "application_strategy": {
            "job_reports": job_reports or [],
            "institution_strategy": institution_strategy,
            "institution_weakness": institution_weakness,
            "interview_cards": interview_cards,
        },
        "diagnostics": (search_result or {}).get("diagnostics"),
        "evidence_links": [],
        "verification_notes": verification_notes,
        "warnings": [*warnings, *list((search_result or {}).get("warnings") or [])],
    }


def _selected_institution_code(resolution: Mapping[str, Any]) -> str | None:
    strong = [
        item
        for item in resolution.get("codes") or []
        if isinstance(item, Mapping) and float(item.get("score") or 0) >= 0.92
    ]
    return _to_text(strong[0].get("code")) if len(strong) == 1 else None


def _safe_call(
    runner: ToolRunner,
    arguments: Mapping[str, Any],
    *,
    stage: str,
    warnings: list[str],
) -> dict[str, Any]:
    try:
        return dict(runner(arguments))
    except Exception as exc:
        warnings.append(f"{stage}: {exc}")
        return {}


def _collect_evidence_links(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    links: dict[str, dict[str, Any]] = {}

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            url = _to_text(value.get("url") or value.get("source_url"))
            if url and url.lower().startswith(("http://", "https://")):
                links.setdefault(
                    url,
                    {
                        "url": url,
                        "title": _to_text(value.get("title") or value.get("job_title")),
                    },
                )
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return list(links.values())


def _handler(tool: ToolDefinition) -> ToolRunner:
    if tool.handler is None:
        raise ValueError(f"tool is not callable: {tool.name}")
    return tool.handler


def _note(field: str, reason: str, suggested_check: str) -> dict[str, str]:
    return {"field": field, "reason": reason, "suggested_check": suggested_check}


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


def _text_list(value: Any, *, field: str) -> list[str]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    return [text for item in value if (text := _to_text(item)) is not None]


def _to_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    if value is None or value == "":
        return default
    try:
        number = int(str(value))
    except ValueError as exc:
        raise ValueError(f"expected integer value: {value}") from exc
    if number < minimum:
        raise ValueError(f"expected integer >= {minimum}: {value}")
    return min(number, maximum)


def _optional_int(value: Any, *, field: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except ValueError as exc:
        raise ValueError(f"expected integer value for {field}: {value}") from exc


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
