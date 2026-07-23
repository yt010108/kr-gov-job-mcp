"""Execute and compact the guided public-job career workflows."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from time import monotonic
from typing import Any


ToolCaller = Callable[[str, Mapping[str, Any] | None], Mapping[str, Any]]
TodayProvider = Callable[[], date]

_AVERAGE_COMPENSATION_CAUTION = (
    "기관 전체 직원 평균보수이며 신입 초봉이나 채용 제시연봉이 아닙니다."
)
_PRIORITY_SCORE_CAUTION = (
    "지원 우선순위를 정하기 위한 근거 점수이며 합격 가능성이나 합격 확률이 아닙니다."
)
_MAX_EXECUTED_RESULTS = 3
_MAX_DETAIL_CANDIDATES = 6
_MAX_SEARCH_CALLS = 3
_MAX_STAR_EXPERIENCES = 3
_MAX_TOOL_CALLS = 21
_MAX_ELAPSED_BEFORE_NEXT_CALL_SECONDS = 20.0


@dataclass
class _ExecutionContext:
    call_tool: ToolCaller
    trace: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    degraded: bool = False
    external_calls: int = 0
    started_at: float = field(default_factory=monotonic)

    def call(
        self,
        *,
        stage: str,
        tool: str,
        arguments: Mapping[str, Any],
        target: str | None = None,
    ) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "order": len(self.trace) + 1,
            "stage": stage,
            "tool": tool,
            "status": "success",
        }
        if target:
            entry["target"] = target
        elapsed_seconds = monotonic() - self.started_at
        if elapsed_seconds >= _MAX_ELAPSED_BEFORE_NEXT_CALL_SECONDS:
            entry.update(
                status="skipped",
                reason=(
                    f"워크플로 경과 시간 {_MAX_ELAPSED_BEFORE_NEXT_CALL_SECONDS:.0f}초를 "
                    "넘어 새 단계를 시작하지 않았습니다."
                ),
            )
            self.trace.append(entry)
            self.mark_partial(f"{stage}: {entry['reason']}")
            return {}
        if self.external_calls >= _MAX_TOOL_CALLS:
            entry.update(
                status="skipped",
                reason=f"워크플로 호출 예산({_MAX_TOOL_CALLS}회)을 모두 사용했습니다.",
            )
            self.trace.append(entry)
            self.mark_partial(
                f"{stage}: 워크플로 호출 예산({_MAX_TOOL_CALLS}회)으로 이 단계를 생략했습니다."
            )
            return {}
        self.external_calls += 1
        try:
            result = dict(self.call_tool(tool, arguments))
        except Exception as exc:
            message = _safe_error(exc)
            entry.update(status="failed", error=message)
            self.trace.append(entry)
            self.mark_partial(f"{stage}: {message}")
            return {}

        self.trace.append(entry)
        for warning in _as_list(result.get("warnings")):
            text = _text(warning)
            if text:
                self.mark_partial(f"{stage}: {text}")
        return result

    def cached(self, *, stage: str, tool: str, target: str) -> None:
        self.trace.append(
            {
                "order": len(self.trace) + 1,
                "stage": stage,
                "tool": tool,
                "status": "cached",
                "target": target,
            }
        )

    def skipped(self, *, stage: str, tool: str, reason: str) -> None:
        self.trace.append(
            {
                "order": len(self.trace) + 1,
                "stage": stage,
                "tool": tool,
                "status": "skipped",
                "reason": reason,
            }
        )

    def mark_partial(self, warning: str) -> None:
        self.degraded = True
        if warning not in self.warnings:
            self.warnings.append(warning)

    def stage_failed(self, prefix: str) -> bool:
        return any(
            entry["status"] == "failed" and str(entry["stage"]).startswith(prefix)
            for entry in self.trace
        )


def execute_public_job_career_workflow(
    *,
    support_mode: str,
    arguments: Mapping[str, Any],
    workflow_steps: Sequence[Mapping[str, Any]],
    call_tool: ToolCaller,
    today_provider: TodayProvider,
) -> dict[str, Any]:
    """Run the selected workflow and return one compact, display-ready payload."""

    context = _ExecutionContext(call_tool=call_tool)
    as_of_date = _parse_date(arguments.get("as_of_date")) or today_provider()

    if support_mode in {"beginner", "job_search"}:
        dashboard, terminal_status = _execute_job_discovery(
            support_mode=support_mode,
            arguments=arguments,
            as_of_date=as_of_date,
            context=context,
        )
    elif support_mode == "application":
        dashboard, terminal_status = _execute_application_package(
            arguments=arguments,
            as_of_date=as_of_date,
            context=context,
        )
    else:
        dashboard, terminal_status = _execute_interview_package(
            arguments=arguments,
            as_of_date=as_of_date,
            context=context,
        )

    status = terminal_status or ("partial_success" if context.degraded else "completed")
    return {
        "status": status,
        "support_mode": support_mode,
        "as_of_date": as_of_date.isoformat(),
        "summary": _status_summary(status, support_mode, dashboard),
        "dashboard": dashboard,
        "workflow_steps": [dict(step) for step in workflow_steps],
        "execution_trace": context.trace,
        "warnings": _deduplicate(context.warnings),
        "input_summary": _input_summary(arguments),
        "next_call": None,
    }


def _execute_job_discovery(
    *,
    support_mode: str,
    arguments: Mapping[str, Any],
    as_of_date: date,
    context: _ExecutionContext,
) -> tuple[dict[str, Any], str | None]:
    known_skills = _text_list(arguments.get("known_skills"))
    career_level = _text(arguments.get("career_level")) or "any"
    all_regions = _text_list(arguments.get("regions"))
    regions = all_regions[:3]
    if len(all_regions) > 3:
        context.mark_partial("희망 지역은 호출 폭주를 막기 위해 앞의 3개만 탐색했습니다.")
    max_results = min(
        _positive_int(arguments.get("max_results"), default=3),
        _MAX_EXECUTED_RESULTS,
    )
    preparation_notes = _text(arguments.get("preparation_notes"))

    if support_mode == "beginner":
        all_targets = _text_list(arguments.get("interests"))
        raw_targets = all_targets[:3]
        display_target = " · ".join(raw_targets)
        if len(all_targets) > 3:
            context.mark_partial("관심 분야는 호출 폭주를 막기 위해 앞의 3개만 탐색했습니다.")
    else:
        target_role = _text(arguments.get("target_role")) or ""
        raw_targets = [target_role]
        display_target = target_role

    resolutions: list[dict[str, Any]] = []
    search_scopes: list[dict[str, str]] = []
    seen_search_scopes: set[str] = set()
    for index, target in enumerate(raw_targets, start=1):
        resolve_arguments: dict[str, Any] = {
            "target_role": target,
            "limit": 5,
        }
        if known_skills:
            resolve_arguments["known_skills"] = known_skills
        if preparation_notes:
            resolve_arguments["preparation_notes"] = preparation_notes
        resolution = context.call(
            stage=f"ncs_resolution:{index}",
            tool="resolve_ncs_code",
            arguments=resolve_arguments,
            target=target,
        )
        ncs_code = _text(resolution.get("selected_ncs_code"))
        ncs_name = _text(resolution.get("selected_ncs_name"))
        resolutions.append(
            {
                "input": target,
                "ncs_code": ncs_code,
                "ncs_name": ncs_name,
                "confidence": resolution.get("confidence"),
            }
        )
        scope = {"target": target}
        if ncs_code:
            scope["ncs_code"] = ncs_code
            scope_key = f"ncs:{_normalized(ncs_code)}"
        else:
            scope["keyword"] = target
            scope_key = f"keyword:{_normalized(target)}"
            context.mark_partial(
                f"'{target}'의 NCS 코드를 확정하지 못해 공고 제목 keyword 검색으로 전환했습니다."
            )
        if scope_key not in seen_search_scopes:
            seen_search_scopes.add(scope_key)
            search_scopes.append(scope)

    region_filters: list[dict[str, str]] = []
    seen_region_codes: set[str] = set()
    for index, region in enumerate(regions, start=1):
        resolution = context.call(
            stage=f"region_resolution:{index}",
            tool="lookup_region_codes",
            arguments={"query": region},
            target=region,
        )
        matches = _mapping_list(resolution.get("matches"))
        code = _text(matches[0].get("code")) if matches else None
        normalized_code = _normalized(code)
        if code:
            if normalized_code not in seen_region_codes:
                seen_region_codes.add(normalized_code)
                region_filters.append({"input": region, "region_code": code})
        else:
            context.mark_partial(
                f"'{region}'의 지역 코드를 확정하지 못해 해당 지역 필터를 적용하지 않았습니다."
            )
    if not region_filters:
        region_filters = [{"input": "", "region_code": ""}]

    search_results: list[dict[str, Any]] = []
    candidate_jobs: dict[str, dict[str, Any]] = {}
    search_limit = max(10, max_results * 3)
    search_requests: list[tuple[dict[str, Any], str]] = []
    seen_search_arguments: set[str] = set()
    pair_order: list[tuple[int, int]] = []
    seen_pairs: set[tuple[int, int]] = set()
    pair_count = len(search_scopes) * len(region_filters)
    for index in range(pair_count):
        pair = (index % len(search_scopes), index % len(region_filters))
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            pair_order.append(pair)
    for region_index in range(len(region_filters)):
        for scope_index in range(len(search_scopes)):
            pair = (scope_index, region_index)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                pair_order.append(pair)

    for scope_index, region_index in pair_order:
        scope = search_scopes[scope_index]
        region_filter = region_filters[region_index]
        search_arguments: dict[str, Any] = {
            "ongoing_only": True,
            "limit": search_limit,
        }
        if scope.get("ncs_code"):
            search_arguments["ncs_code"] = scope["ncs_code"]
        else:
            search_arguments["keyword"] = scope["keyword"]
        if region_filter.get("region_code"):
            search_arguments["region_code"] = region_filter["region_code"]
        fingerprint = json.dumps(
            search_arguments,
            ensure_ascii=False,
            sort_keys=True,
        )
        if fingerprint in seen_search_arguments:
            continue
        seen_search_arguments.add(fingerprint)
        target = " / ".join(part for part in (scope["target"], region_filter.get("input")) if part)
        search_requests.append((search_arguments, target))

    search_scope_truncated = len(search_requests) > _MAX_SEARCH_CALLS
    if search_scope_truncated:
        context.mark_partial(
            f"검색 조합 {len(search_requests)}개 중 호출 예산에 맞춰 "
            f"관심 분야와 지역을 분산한 {_MAX_SEARCH_CALLS}개만 조회했습니다."
        )
    for call_index, (search_arguments, target) in enumerate(
        search_requests[:_MAX_SEARCH_CALLS],
        start=1,
    ):
        result = context.call(
            stage=f"job_search:{call_index}",
            tool="search_public_jobs",
            arguments=search_arguments,
            target=target,
        )
        search_results.append(result)
        for job in _mapping_list(result.get("jobs")):
            job_id = _job_id(job)
            if job_id:
                candidate_jobs.setdefault(job_id, dict(job))

    if not candidate_jobs:
        diagnostics = [
            result["diagnostics"]
            for result in search_results
            if isinstance(result.get("diagnostics"), Mapping)
        ]
        terminal_status = "failed" if context.stage_failed("job_search:") else "no_results"
        dashboard = {
            "view": "job_discovery",
            "title": "공공기관 지원 공고 탐색 결과",
            "scope_interpretation": (
                "호출 예산으로 선택한 일부 직무·지역 조합에서 현재 접수 중인 공고를 "
                "탐색했으며, 전체 입력 조합의 무결과를 뜻하지 않습니다."
                if search_scope_truncated
                else "조회일 현재 접수 중인 공고를 탐색했습니다."
            ),
            "target": display_target,
            "target_resolutions": resolutions,
            "search_coverage": {
                "available_combinations": len(search_requests),
                "queried_combinations": min(len(search_requests), _MAX_SEARCH_CALLS),
                "complete": not search_scope_truncated,
            },
            "job_rankings": [],
            "today_actions": [
                "NCS 후보와 검색 조건을 확인하세요.",
                "현재 접수 중 필터를 풀지 여부를 결정하세요.",
                "희망 기관이나 지역 조건을 한 단계 완화해 보세요.",
            ],
            "diagnostics": diagnostics,
            "source_links": [],
        }
        return dashboard, terminal_status

    ranked_summaries = sorted(
        candidate_jobs.values(),
        key=lambda job: _summary_sort_key(
            job,
            resolutions=resolutions,
            career_level=career_level,
            known_skills=known_skills,
            regions=regions,
            as_of_date=as_of_date,
        ),
    )
    detail_limit = min(
        len(ranked_summaries),
        max(max_results, min(_MAX_DETAIL_CANDIDATES, max_results * 2)),
    )
    detailed_candidates: list[dict[str, Any]] = []
    for job in ranked_summaries[:detail_limit]:
        job_id = _job_id(job)
        if not job_id:
            continue
        detail_result = context.call(
            stage=f"job_detail:{job_id}",
            tool="fetch_job_detail",
            arguments={"job_id": job_id},
            target=job_id,
        )
        detail_job = (
            dict(detail_result["job"]) if isinstance(detail_result.get("job"), Mapping) else {}
        )
        detailed_candidates.append({**dict(job), **detail_job})

    selected_jobs = sorted(
        detailed_candidates,
        key=lambda job: _summary_sort_key(
            job,
            resolutions=resolutions,
            career_level=career_level,
            known_skills=known_skills,
            regions=regions,
            as_of_date=as_of_date,
        ),
    )[:max_results]
    salary_cache: dict[str, dict[str, Any]] = {}
    cards: list[dict[str, Any]] = []
    for job in selected_jobs:
        job_id = _job_id(job)
        if not job_id:
            continue
        institution_name = _text(job.get("institution_name"))
        salary_result = _salary_for_institution(
            institution_name=institution_name,
            year=_optional_int(arguments.get("year")),
            job_id=job_id,
            cache=salary_cache,
            context=context,
        )
        fit_arguments: dict[str, Any] = {
            "job_id": job_id,
            "target_role": display_target,
            "known_skills": known_skills,
        }
        if preparation_notes:
            fit_arguments["preparation_notes"] = preparation_notes
        fit_result = context.call(
            stage=f"job_fit:{job_id}",
            tool="analyze_job_fit_report",
            arguments=fit_arguments,
            target=job_id,
        )
        cards.append(
            _job_card(
                job=job,
                fit_result=fit_result,
                salary_result=salary_result,
                target_role=display_target,
                selected_ncs_codes={
                    str(item["ncs_code"]) for item in resolutions if item.get("ncs_code")
                },
                career_level=career_level,
                known_skills=known_skills,
                regions=regions,
                as_of_date=as_of_date,
            )
        )

    cards.sort(
        key=lambda card: (
            -int(card["fit"]["priority_score"]),
            _deadline_sort_value(card["deadline"].get("date")),
            str(card.get("job_id") or ""),
        )
    )
    for rank, card in enumerate(cards, start=1):
        card["rank"] = rank

    dashboard = {
        "view": "job_discovery",
        "title": "공공기관 지원 공고 탐색 결과",
        "scope_interpretation": "조회일 현재 접수 중인 공고를 탐색했습니다.",
        "target": display_target,
        "career_level": career_level,
        "regions": regions,
        "target_resolutions": resolutions,
        "search_coverage": {
            "available_combinations": len(search_requests),
            "queried_combinations": min(len(search_requests), _MAX_SEARCH_CALLS),
            "complete": not search_scope_truncated,
        },
        "candidate_counts": {
            "searched": len(candidate_jobs),
            "detail_evaluated": len(detailed_candidates),
            "displayed": len(cards),
        },
        "job_rankings": cards,
        "today_actions": _overall_today_actions(cards),
        "diagnostics": [],
        "source_links": _collect_card_links(cards),
    }
    return dashboard, None


def _execute_application_package(
    *,
    arguments: Mapping[str, Any],
    as_of_date: date,
    context: _ExecutionContext,
) -> tuple[dict[str, Any], str | None]:
    job_id = _first_job_id(arguments)
    detail_result = context.call(
        stage=f"job_detail:{job_id}",
        tool="fetch_job_detail",
        arguments={"job_id": job_id},
        target=job_id,
    )
    if not isinstance(detail_result.get("job"), Mapping):
        return (
            {
                "view": "application_package",
                "title": "선택 공고 지원 준비 결과",
                "job": None,
                "star_frameworks": [],
                "today_actions": ["공고 ID와 Job-ALIO 원문 접근 상태를 확인하세요."],
                "source_links": [],
            },
            "failed",
        )

    job = dict(detail_result["job"])
    known_skills = _text_list(arguments.get("known_skills"))
    target_role = (
        _text(arguments.get("target_role"))
        or _first_ncs_name(job)
        or _text(job.get("title"))
        or "지원 직무"
    )
    if not _text(arguments.get("target_role")):
        context.mark_partial(
            f"목표 직무가 없어 공고의 NCS·제목을 바탕으로 '{target_role}' 관점을 사용했습니다."
        )
    detail_institution = _text(job.get("institution_name"))
    input_institution = _text(arguments.get("institution_name"))
    institution_name = detail_institution or input_institution
    if (
        detail_institution
        and input_institution
        and _normalized(detail_institution) != _normalized(input_institution)
    ):
        context.mark_partial(
            "입력 기관명과 공고 상세 기관명이 달라 공고 상세 기관명을 기준으로 "
            "평균보수와 STAR 자료를 연결했습니다."
        )
    salary_result = _salary_for_institution(
        institution_name=institution_name,
        year=_optional_int(arguments.get("year")),
        job_id=job_id,
        cache={},
        context=context,
    )
    fit_arguments: dict[str, Any] = {
        "job_id": job_id,
        "target_role": target_role,
        "known_skills": known_skills,
    }
    preparation_notes = _text(arguments.get("preparation_notes"))
    if preparation_notes:
        fit_arguments["preparation_notes"] = preparation_notes
    fit_result = context.call(
        stage=f"job_fit:{job_id}",
        tool="analyze_job_fit_report",
        arguments=fit_arguments,
        target=job_id,
    )
    card = _job_card(
        job=job,
        fit_result=fit_result,
        salary_result=salary_result,
        target_role=target_role,
        selected_ncs_codes=set(),
        career_level=_text(arguments.get("career_level")) or "any",
        known_skills=known_skills,
        regions=_text_list(arguments.get("regions")),
        as_of_date=as_of_date,
    )
    card["rank"] = 1

    star_frameworks = _run_star_frameworks(
        experiences=_text_list(arguments.get("user_experiences")),
        question=_text(arguments.get("question"))
        or "이 직무에 지원하기 위해 준비한 경험을 설명해 주세요.",
        target_role=target_role,
        institution_name=institution_name,
        ncs_competencies=_ncs_names(job),
        mode="both",
        stage_prefix="application_star",
        context=context,
    )
    dashboard = {
        "view": "application_package",
        "title": "선택 공고 지원 준비 결과",
        "job": card,
        "star_frameworks": star_frameworks,
        "today_actions": card["today_actions"],
        "source_links": _collect_card_links([card]),
    }
    return dashboard, None


def _execute_interview_package(
    *,
    arguments: Mapping[str, Any],
    as_of_date: date,
    context: _ExecutionContext,
) -> tuple[dict[str, Any], str | None]:
    institution_name = _text(arguments.get("institution_name")) or ""
    target_role = _text(arguments.get("target_role")) or ""
    job_id = _optional_job_id(arguments)
    job: dict[str, Any] | None = None
    if job_id:
        detail_result = context.call(
            stage=f"job_detail:{job_id}",
            tool="fetch_job_detail",
            arguments={"job_id": job_id},
            target=job_id,
        )
        if isinstance(detail_result.get("job"), Mapping):
            job = dict(detail_result["job"])
            detail_institution = _text(job.get("institution_name"))
            if detail_institution and _normalized(detail_institution) != _normalized(
                institution_name
            ):
                context.mark_partial(
                    "입력 기관명과 공고의 기관명이 달라 해당 공고 맥락은 제외하고 "
                    "입력 기관명을 기준으로 면접 자료를 만들었습니다."
                )
                job = None

    resolve_arguments: dict[str, Any] = {
        "target_role": target_role,
        "limit": 5,
    }
    known_skills = _text_list(arguments.get("known_skills"))
    if known_skills:
        resolve_arguments["known_skills"] = known_skills
    resolution = context.call(
        stage="ncs_resolution",
        tool="resolve_ncs_code",
        arguments=resolve_arguments,
        target=target_role,
    )
    ncs_code = _text(resolution.get("selected_ncs_code"))
    ncs_name = _text(resolution.get("selected_ncs_name"))

    institution_arguments: dict[str, Any] = {
        "institution_name": institution_name,
        "target_role": target_role,
        "job_family": ncs_name or target_role,
        "fetch_live_alio": _optional_bool(
            arguments.get("fetch_live_alio"),
            default=True,
        ),
    }
    if ncs_code:
        institution_arguments["ncs_code"] = ncs_code
    year = _optional_int(arguments.get("year"))
    if year is not None:
        institution_arguments["year"] = year

    strategy = context.call(
        stage="institution_strategy",
        tool="analyze_institution_strategy",
        arguments=institution_arguments,
        target=institution_name,
    )
    weakness_arguments = {
        key: value
        for key, value in institution_arguments.items()
        if key in {"institution_name", "year", "fetch_live_alio"}
    }
    weakness = context.call(
        stage="institution_weakness",
        tool="analyze_institution_weakness",
        arguments=weakness_arguments,
        target=institution_name,
    )

    interview_arguments = dict(institution_arguments)
    reusable_evidence = _collect_evidence(strategy, weakness)
    if reusable_evidence:
        interview_arguments["evidence"] = reusable_evidence
        interview_arguments["fetch_live_alio"] = False
    interview = context.call(
        stage="interview_cards",
        tool="prepare_institution_interview",
        arguments=interview_arguments,
        target=institution_name,
    )
    salary_result = _salary_for_institution(
        institution_name=institution_name,
        year=year,
        job_id=job_id or institution_name,
        cache={},
        context=context,
    )

    interview_cards = _mapping_list(interview.get("interview_cards"))
    questions = [
        _text(card.get("likely_question"))
        for card in interview_cards
        if _text(card.get("likely_question"))
    ]
    star_frameworks = _run_star_frameworks(
        experiences=_text_list(arguments.get("user_experiences")),
        question=_text(arguments.get("question")),
        target_role=target_role,
        institution_name=institution_name,
        ncs_competencies=[ncs_name] if ncs_name else [],
        mode="interview",
        stage_prefix="interview_star",
        context=context,
        fallback_questions=questions,
    )

    compact_strategy = [
        {
            "summary": _text(signal.get("summary")),
            "job_connection": _text(signal.get("job_connection")),
        }
        for signal in _mapping_list(strategy.get("strategy_signals"))[:3]
    ]
    compact_weakness = [
        {
            "summary": _text(signal.get("summary")),
            "careful_wording": _text(signal.get("careful_wording")),
            "applicant_connection": _text(signal.get("applicant_connection")),
        }
        for signal in _mapping_list(weakness.get("weakness_signals"))[:3]
    ]
    compact_interview = [
        {
            "question_type": _text(card.get("question_type")),
            "likely_question": _text(card.get("likely_question")),
            "answer_strategy": _text(card.get("answer_strategy")),
            "answer_points": _text_list(card.get("answer_points"))[:4],
            "caution": _text(card.get("caution")),
            "safe_framing": _text(card.get("safe_framing")),
        }
        for card in interview_cards[:5]
    ]
    if not compact_strategy:
        context.mark_partial("기관 전략 근거를 확인하지 못했습니다.")
    if not compact_weakness:
        context.mark_partial("기관 개선·보완 근거를 확인하지 못했습니다.")
    if not compact_interview:
        context.mark_partial("기관·직무 맞춤 면접 질문을 만들지 못했습니다.")
    today_actions = _interview_today_actions(compact_interview, interview)
    dashboard = {
        "view": "interview_package",
        "title": f"{institution_name} {target_role} 면접 준비 결과",
        "institution_name": institution_name,
        "target_role": target_role,
        "job": _compact_interview_job(job, as_of_date) if job else None,
        "average_compensation": _compact_salary(salary_result),
        "strategy_signals": compact_strategy,
        "improvement_signals": compact_weakness,
        "interview_questions": compact_interview,
        "star_frameworks": star_frameworks,
        "today_actions": today_actions,
        "source_links": _collect_urls(
            {
                "job": job,
                "salary": salary_result,
                "strategy": strategy,
                "weakness": weakness,
                "interview": interview,
            },
            limit=12,
        ),
    }
    if not compact_interview and not compact_strategy and not compact_weakness:
        terminal = "failed" if context.stage_failed("interview_cards") else None
        context.mark_partial("기관 면접 자료의 검증 가능한 근거가 충분하지 않습니다.")
        return dashboard, terminal
    return dashboard, None


def _salary_for_institution(
    *,
    institution_name: str | None,
    year: int | None,
    job_id: str,
    cache: dict[str, dict[str, Any]],
    context: _ExecutionContext,
) -> dict[str, Any]:
    if not institution_name:
        context.skipped(
            stage=f"average_compensation:{job_id}",
            tool="get_institution_average_salary",
            reason="기관명이 없어 조회하지 않았습니다.",
        )
        context.mark_partial(f"average_compensation:{job_id}: 기관명을 확인할 수 없습니다.")
        return {}
    cache_key = _normalized(institution_name)
    if cache_key in cache:
        context.cached(
            stage=f"average_compensation:{job_id}",
            tool="get_institution_average_salary",
            target=institution_name,
        )
        return cache[cache_key]
    salary_arguments: dict[str, Any] = {"institution_name": institution_name}
    if year is not None:
        salary_arguments["year"] = year
    result = context.call(
        stage=f"average_compensation:{job_id}",
        tool="get_institution_average_salary",
        arguments=salary_arguments,
        target=institution_name,
    )
    result.setdefault("requested_institution_name", institution_name)
    cache[cache_key] = result
    if not isinstance(result.get("average_salary"), Mapping):
        context.mark_partial(
            f"average_compensation:{job_id}: ALIO 평균보수 값을 확인하지 못했습니다."
        )
    return result


def _run_star_frameworks(
    *,
    experiences: list[str],
    question: str | None,
    target_role: str,
    institution_name: str | None,
    ncs_competencies: list[str],
    mode: str,
    stage_prefix: str,
    context: _ExecutionContext,
    fallback_questions: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not experiences:
        context.skipped(
            stage=stage_prefix,
            tool="generate_star_answer_framework",
            reason="사용자가 제공한 경험이 없어 STAR 생성을 생략했습니다.",
        )
        return []
    if len(experiences) > _MAX_STAR_EXPERIENCES:
        context.mark_partial("STAR 생성은 호출 폭주를 막기 위해 앞의 경험 3개만 사용했습니다.")
    questions = fallback_questions or []
    frameworks: list[dict[str, Any]] = []
    for index, experience in enumerate(experiences[:_MAX_STAR_EXPERIENCES], start=1):
        selected_question = (
            question
            or (questions[(index - 1) % len(questions)] if questions else None)
            or "지원 직무와 관련된 경험을 설명해 주세요."
        )
        star_arguments: dict[str, Any] = {
            "question": selected_question,
            "user_experience": experience,
            "target_job": target_role,
            "ncs_competencies": ncs_competencies,
            "mode": mode,
        }
        if institution_name:
            star_arguments["institution_name"] = institution_name
        result = context.call(
            stage=f"{stage_prefix}:{index}",
            tool="generate_star_answer_framework",
            arguments=star_arguments,
            target=f"experience-{index}",
        )
        if result:
            frameworks.append(_compact_star(result, index=index))
    return frameworks


def _job_card(
    *,
    job: Mapping[str, Any],
    fit_result: Mapping[str, Any],
    salary_result: Mapping[str, Any],
    target_role: str,
    selected_ncs_codes: set[str],
    career_level: str,
    known_skills: list[str],
    regions: list[str],
    as_of_date: date,
) -> dict[str, Any]:
    fit = _fit_assessment(
        job=job,
        fit_result=fit_result,
        target_role=target_role,
        selected_ncs_codes=selected_ncs_codes,
        career_level=career_level,
        known_skills=known_skills,
        regions=regions,
    )
    salary = _compact_salary(salary_result)
    links = {
        "application": _url(job.get("source_url")),
        "duty_description": _duty_description_url(job),
        "salary_disclosure": (salary.get("source_url") if isinstance(salary, Mapping) else None),
    }
    return {
        "rank": 0,
        "job_id": _job_id(job),
        "institution_name": _text(job.get("institution_name")),
        "title": _text(job.get("title")),
        "deadline": _deadline(job.get("end_date"), as_of_date),
        "recruitment_type": _text(job.get("recruitment_type")),
        "employment_types": _text_list(job.get("employment_types")),
        "work_regions": _text_list(job.get("work_regions")),
        "fit": fit,
        "average_compensation": salary,
        "today_actions": _today_actions(fit_result),
        "links": links,
    }


def _fit_assessment(
    *,
    job: Mapping[str, Any],
    fit_result: Mapping[str, Any],
    target_role: str,
    selected_ncs_codes: set[str],
    career_level: str,
    known_skills: list[str],
    regions: list[str],
) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    reasons: list[str] = []
    points = 0
    available = 0

    job_ncs = {
        code
        for mapping in _mapping_list(job.get("ncs_mappings"))
        if (code := _text(mapping.get("code")))
    }
    job_ncs_names = [
        name
        for mapping in _mapping_list(job.get("ncs_mappings"))
        if (name := _text(mapping.get("display_name")))
    ]
    role_text = " ".join(
        filter(
            None,
            [
                _text(job.get("title")),
                *job_ncs_names,
                _text(job.get("qualification")),
                _text(job.get("preferred_conditions")),
            ],
        )
    )
    available += 45
    ncs_match = bool(selected_ncs_codes and selected_ncs_codes & job_ncs)
    role_text_match = _contains_any(role_text, _role_terms(target_role))
    if ncs_match and role_text_match:
        role_points = 45
        role_evidence = "해석된 NCS 코드와 목표 직무 표현이 모두 공고 근거와 일치합니다."
    elif ncs_match:
        role_points = 30
        role_evidence = "해석된 NCS 코드는 일치하지만 세부 직무 표현은 추가 확인이 필요합니다."
    elif role_text_match:
        role_points = 30
        role_evidence = "목표 직무 표현이 공고 제목·NCS·자격 문구에서 확인됩니다."
    else:
        role_points = 0
        role_evidence = "목표 직무와의 직접 일치를 추가 확인해야 합니다."
    points += role_points
    components.append(
        {
            "criterion": "role_relevance",
            "points": role_points,
            "max_points": 45,
            "evidence": role_evidence,
        }
    )
    if role_points:
        reasons.append(role_evidence)

    available += 20
    career_text = " ".join(
        filter(None, [_text(job.get("title")), _text(job.get("recruitment_type"))])
    )
    career_points, career_evidence = _career_points(career_level, career_text)
    points += career_points
    components.append(
        {
            "criterion": "career_level",
            "points": career_points,
            "max_points": 20,
            "evidence": career_evidence,
        }
    )
    if career_points:
        reasons.append(career_evidence)

    matched_skills: list[str] = []
    if known_skills:
        available += 25
        evidence_text = " ".join(
            filter(
                None,
                [
                    _text(job.get("title")),
                    _text(job.get("qualification")),
                    _text(job.get("preferred_conditions")),
                    _text(job.get("preference")),
                    *job_ncs_names,
                ],
            )
        )
        matched_skills = [
            skill for skill in known_skills if _normalized(skill) in _normalized(evidence_text)
        ]
        skill_points = round(25 * len(matched_skills) / len(known_skills))
        points += skill_points
        skill_evidence = (
            f"공고 문구에서 보유 역량 {', '.join(matched_skills)}을 확인했습니다."
            if matched_skills
            else "보유 역량의 직접 일치를 공고 문구에서 확인하지 못했습니다."
        )
        components.append(
            {
                "criterion": "known_skills",
                "points": skill_points,
                "max_points": 25,
                "evidence": skill_evidence,
            }
        )
        if matched_skills:
            reasons.append(skill_evidence)

    if regions:
        available += 10
        work_regions = _text_list(job.get("work_regions"))
        region_match = any(
            _normalized(region) in _normalized(work_region)
            or _normalized(work_region) in _normalized(region)
            for region in regions
            for work_region in work_regions
        )
        region_points = 10 if region_match else 0
        points += region_points
        region_evidence = (
            "희망 지역과 공고 근무지역이 일치합니다."
            if region_match
            else "희망 지역과 공고 근무지역의 일치를 추가 확인해야 합니다."
        )
        components.append(
            {
                "criterion": "region",
                "points": region_points,
                "max_points": 10,
                "evidence": region_evidence,
            }
        )
        if region_match:
            reasons.append(region_evidence)

    priority_score = round(points * 100 / available) if available else 0
    level = "근거 있음" if priority_score >= 75 else "일부 일치"
    if priority_score < 50:
        level = "추가 확인"
    missing_competencies = _gap_titles(fit_result)
    return {
        "scope": "profile_fit" if known_skills else "role_relevance",
        "level": level,
        "priority_score": priority_score,
        "score_components": components,
        "score_caution": _PRIORITY_SCORE_CAUTION,
        "reasons": _deduplicate(reasons)[:4],
        "matched_skills": matched_skills,
        "missing_competencies": missing_competencies,
        "gap_caution": "확정된 결핍이 아니라 공고·NCS 근거에서 나온 보완·확인 후보입니다.",
        "eligibility_check_required": True,
    }


def _summary_sort_key(
    job: Mapping[str, Any],
    *,
    resolutions: list[dict[str, Any]],
    career_level: str,
    known_skills: list[str],
    regions: list[str],
    as_of_date: date,
) -> tuple[int, date, str]:
    selected_codes = {str(item["ncs_code"]) for item in resolutions if item.get("ncs_code")}
    assessment = _fit_assessment(
        job=job,
        fit_result={},
        target_role=" ".join(str(item["input"]) for item in resolutions),
        selected_ncs_codes=selected_codes,
        career_level=career_level,
        known_skills=known_skills,
        regions=regions,
    )
    deadline = _parse_date(job.get("end_date")) or date.max
    if deadline < as_of_date:
        deadline = date.max
    return (
        -int(assessment["priority_score"]),
        deadline,
        _job_id(job) or "",
    )


def _career_points(career_level: str, career_text: str) -> tuple[int, str]:
    normalized = _normalized(career_text)
    if career_level == "any":
        return 20, "경력 구분을 제한하지 않은 탐색입니다."
    entry_hints = ("신입", "인턴", "경력무관", "경력 무관", "무관")
    experienced_hints = ("경력직", "경력 채용", "경력사원")
    if career_level == "entry":
        if _contains_any(normalized, entry_hints):
            return 20, "공고의 신입·인턴·경력무관 표현이 사용자 단계와 일치합니다."
        if _contains_any(normalized, experienced_hints):
            return 0, "공고가 경력 채용으로 보여 지원자격 확인이 필요합니다."
        return 10, "공고의 신입·경력 구분이 명확하지 않아 원문 확인이 필요합니다."
    if _contains_any(normalized, experienced_hints):
        return 20, "공고의 경력 채용 표현이 사용자 단계와 일치합니다."
    if _contains_any(normalized, entry_hints):
        return 5, "신입·경력무관 공고이므로 요구 경력을 원문에서 확인해야 합니다."
    return 10, "공고의 신입·경력 구분이 명확하지 않아 원문 확인이 필요합니다."


def _compact_salary(result: Mapping[str, Any]) -> dict[str, Any] | None:
    salary = result.get("average_salary")
    if not isinstance(salary, Mapping):
        return None
    report = result.get("report")
    report_mapping = report if isinstance(report, Mapping) else {}
    institution = _mapping(result.get("institution"))
    query = _mapping(result.get("query"))
    return {
        "institution_name": (
            _text(institution.get("name"))
            or _text(query.get("institution_name"))
            or _text(result.get("requested_institution_name"))
        ),
        "amount_krw": salary.get("amount_krw"),
        "year": salary.get("year"),
        "basis": salary.get("basis"),
        "employment_group": salary.get("employment_group"),
        "source_url": _url(report_mapping.get("source_url")),
        "caution": _AVERAGE_COMPENSATION_CAUTION,
    }


def _compact_star(result: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    return {
        "experience_number": index,
        "question": _text(result.get("question"))
        or _text(_mapping(result.get("query")).get("question")),
        "interview_answer": result.get("interview_answer"),
        "cover_letter_draft": result.get("cover_letter_draft"),
        "follow_up_questions": _text_list(result.get("follow_up_questions"))[:3],
        "risk_flags": _mapping_list(result.get("risk_flags"))[:3],
        "verification_notes": _text_list(result.get("verification_notes"))[:3],
    }


def _compact_interview_job(job: Mapping[str, Any], as_of_date: date) -> dict[str, Any]:
    return {
        "job_id": _job_id(job),
        "title": _text(job.get("title")),
        "deadline": _deadline(job.get("end_date"), as_of_date),
        "application_url": _url(job.get("source_url")),
    }


def _deadline(value: Any, as_of_date: date) -> dict[str, Any]:
    deadline = _parse_date(value)
    if deadline is None:
        return {"date": _text(value), "days_remaining": None, "label": "마감일 확인 필요"}
    days_remaining = (deadline - as_of_date).days
    if days_remaining < 0:
        label = "마감"
    elif days_remaining == 0:
        label = "D-Day"
    else:
        label = f"D-{days_remaining}"
    return {
        "date": deadline.isoformat(),
        "days_remaining": days_remaining,
        "label": label,
    }


def _today_actions(fit_result: Mapping[str, Any]) -> list[str]:
    actions = ["지원자격과 정확한 마감시각을 공고 원문에서 확인하세요."]
    items = sorted(
        _mapping_list(fit_result.get("preparation_items")),
        key=lambda item: {"P0": 0, "P1": 1, "P2": 2}.get(
            _text(item.get("priority")) or "",
            3,
        ),
    )
    for item in items:
        recommended = _text_list(item.get("recommended_actions"))
        if recommended:
            actions.extend(recommended)
        elif title := _text(item.get("title")):
            actions.append(f"{title} 항목을 확인하세요.")
        if len(_deduplicate(actions)) >= 3:
            break
    if len(_deduplicate(actions)) < 3:
        actions.extend(
            [
                "직무기술서에서 필요지식·기술·태도를 표로 정리하세요.",
                "가장 강한 경험 하나를 STAR 근거로 정리하세요.",
            ]
        )
    return _deduplicate(actions)[:3]


def _overall_today_actions(cards: list[dict[str, Any]]) -> list[str]:
    if not cards:
        return []
    actions = list(cards[0].get("today_actions") or [])
    if len(cards) > 1:
        actions.append("상위 공고들의 지원자격과 마감시각을 비교해 오늘 지원 순서를 확정하세요.")
    return _deduplicate([str(action) for action in actions])[:3]


def _interview_today_actions(
    cards: list[dict[str, Any]],
    interview_result: Mapping[str, Any],
) -> list[str]:
    actions = [
        f"'{question}' 질문에 대한 1분 답변을 작성하세요."
        for card in cards[:2]
        if (question := _text(card.get("likely_question")))
    ]
    actions.extend(
        f"{material} 자료를 확인하세요."
        for material in _text_list(interview_result.get("materials_to_check"))
    )
    if len(actions) < 3:
        actions.append("사용자 경험 하나를 STAR의 상황·과제·행동·결과로 나누세요.")
    return _deduplicate(actions)[:3]


def _gap_titles(fit_result: Mapping[str, Any]) -> list[str]:
    gaps = [
        title
        for item in _mapping_list(fit_result.get("knowledge_gaps"))
        if (title := _text(item.get("title")))
    ]
    if not gaps:
        gaps = [
            title
            for item in _mapping_list(fit_result.get("preparation_items"))
            if _text(item.get("priority")) == "P0" and (title := _text(item.get("title")))
        ]
    return _deduplicate(gaps)[:4]


def _collect_card_links(cards: list[dict[str, Any]]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for card in cards:
        title = _text(card.get("title")) or "공고"
        for kind, url in _mapping(card.get("links")).items():
            if valid_url := _url(url):
                links.append(
                    {
                        "type": str(kind),
                        "title": title,
                        "url": valid_url,
                    }
                )
    return _deduplicate_mappings(links, key="url")


def _collect_evidence(*results: Mapping[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        for key in ("strategy_signals", "weakness_signals"):
            for signal in _mapping_list(result.get(key)):
                for item in _mapping_list(signal.get("evidence")):
                    fingerprint = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
                    if fingerprint not in seen:
                        seen.add(fingerprint)
                        evidence.append(dict(item))
    return evidence[:20]


def _collect_urls(value: Any, *, limit: int) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []

    def visit(item: Any) -> None:
        if len(links) >= limit:
            return
        if isinstance(item, Mapping):
            candidate = _url(item.get("url") or item.get("source_url"))
            if candidate:
                links.append(
                    {
                        "title": _text(item.get("title") or item.get("name")) or "근거 링크",
                        "url": candidate,
                    }
                )
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return _deduplicate_mappings(links, key="url")[:limit]


def _input_summary(arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Keep useful execution context without repeating free-form personal text."""

    summary = {
        field: arguments[field]
        for field in (
            "support_mode",
            "career_level",
            "target_role",
            "regions",
            "job_id",
            "source_job_id",
            "recruitment_notice_sn",
            "institution_name",
            "year",
            "max_results",
            "fetch_live_alio",
        )
        if field in arguments
    }
    for input_field, output_field in (
        ("interests", "interest_count"),
        ("known_skills", "known_skill_count"),
        ("user_experiences", "user_experience_count"),
    ):
        values = _text_list(arguments.get(input_field))
        if values:
            summary[output_field] = len(values)
    if _text(arguments.get("question")):
        summary["question_provided"] = True
    if _text(arguments.get("preparation_notes")):
        summary["preparation_notes_provided"] = True
    return summary


def _status_summary(
    status: str,
    support_mode: str,
    dashboard: Mapping[str, Any],
) -> str:
    if status == "failed":
        return "핵심 조회 단계가 실패해 자동 실행을 완료하지 못했습니다."
    if status == "no_results":
        return "현재 조건에 맞는 접수 중 공고를 찾지 못했습니다."
    suffix = (
        "일부 단계는 확인이 필요합니다."
        if status == "partial_success"
        else "모든 핵심 단계를 실행했습니다."
    )
    if support_mode in {"beginner", "job_search"}:
        count = len(_as_list(dashboard.get("job_rankings")))
        return f"지원 우선순위 공고 {count}개를 한 화면으로 정리했습니다. {suffix}"
    if support_mode == "application":
        return f"선택 공고의 지원 준비 패키지를 만들었습니다. {suffix}"
    return f"기관·직무 기반 면접 준비 패키지를 만들었습니다. {suffix}"


def _role_terms(target_role: str) -> list[str]:
    terms = [
        term for term in target_role.replace("/", " ").replace("·", " ").split() if len(term) >= 2
    ]
    return terms or [target_role]


def _contains_any(text: str, values: Sequence[str]) -> bool:
    normalized_text = _normalized(text)
    return any(_normalized(value) in normalized_text for value in values if value)


def _ncs_names(job: Mapping[str, Any]) -> list[str]:
    return _deduplicate(
        [
            name
            for mapping in _mapping_list(job.get("ncs_mappings"))
            if (name := _text(mapping.get("display_name")))
        ]
    )


def _first_ncs_name(job: Mapping[str, Any]) -> str | None:
    names = _ncs_names(job)
    return names[0] if names else None


def _duty_description_url(job: Mapping[str, Any]) -> str | None:
    attachments = _mapping_list(job.get("attachments"))
    preferred = [item for item in attachments if item.get("duty_description_candidate") is True]
    candidates = preferred or attachments
    for item in candidates:
        if url := _url(item.get("url")):
            return url
    return None


def _deadline_sort_value(value: Any) -> date:
    return _parse_date(value) or date.max


def _parse_date(value: Any) -> date | None:
    text = _text(value)
    if text is None:
        return None
    digits = "".join(character for character in text if character.isdigit())
    if len(digits) != 8:
        return None
    try:
        return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError:
        return None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _positive_int(value: Any, *, default: int) -> int:
    number = _optional_int(value)
    return number if number is not None and number > 0 else default


def _optional_bool(value: Any, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _first_job_id(arguments: Mapping[str, Any]) -> str:
    return _optional_job_id(arguments) or ""


def _optional_job_id(arguments: Mapping[str, Any]) -> str | None:
    for field_name in ("job_id", "source_job_id", "recruitment_notice_sn"):
        if value := _text(arguments.get(field_name)):
            return value
    return None


def _job_id(job: Mapping[str, Any]) -> str | None:
    return _text(job.get("id") or job.get("source_job_id"))


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    return [dict(item) for item in _as_list(value) if isinstance(item, Mapping)]


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _text_list(value: Any) -> list[str]:
    return _deduplicate([text for item in _as_list(value) if (text := _text(item))])


def _normalized(value: Any) -> str:
    return "".join(str(value or "").lower().split())


def _url(value: Any) -> str | None:
    text = _text(value)
    if text and text.lower().startswith(("http://", "https://")):
        return text
    return None


def _safe_error(exc: Exception) -> str:
    message = " ".join(str(exc).split())
    return (message or exc.__class__.__name__)[:240]


def _deduplicate(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _deduplicate_mappings(
    values: list[dict[str, str]],
    *,
    key: str,
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in values:
        fingerprint = value.get(key)
        if fingerprint and fingerprint not in seen:
            seen.add(fingerprint)
            result.append(value)
    return result
