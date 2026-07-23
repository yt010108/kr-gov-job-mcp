from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pytest

from kr_gov_job_mcp.tools.career_coach_execution import _ExecutionContext
from kr_gov_job_mcp.tools.public_job_career_coach import (
    create_public_job_career_coach_tool,
)


class FakeToolCaller:
    def __init__(
        self,
        *,
        salary_error: bool = False,
        salary_warning: bool = False,
        no_jobs: bool = False,
    ) -> None:
        self.salary_error = salary_error
        self.salary_warning = salary_warning
        self.no_jobs = no_jobs
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        payload = dict(arguments or {})
        self.calls.append((name, payload))
        if name == "resolve_ncs_code":
            return {
                "selected_ncs_code": "R600020",
                "selected_ncs_name": "정보통신",
                "confidence": "high",
                "warnings": [],
            }
        if name == "lookup_region_codes":
            return {
                "matches": [{"code": "R3010", "name": "서울"}],
                "warnings": [],
            }
        if name == "search_public_jobs":
            return {
                "jobs": [] if self.no_jobs else [_job_one(), _job_two()],
                "diagnostics": (
                    {"reason": "no_results", "recommended_next_calls": []} if self.no_jobs else None
                ),
                "warnings": [],
            }
        if name == "fetch_job_detail":
            job_id = str(payload["job_id"])
            job = _job_one() if job_id == "job-1" else _job_two()
            return {
                "job": {
                    **job,
                    "qualification": "정보보호 지식과 네트워크 이해",
                    "preferred_conditions": "정보보안기사 우대",
                    "preference": "관련 프로젝트 경험 우대",
                    "attachments": [
                        {
                            "name": "직무기술서.pdf",
                            "url": f"https://example.test/{job_id}/duty.pdf",
                            "duty_description_candidate": True,
                        }
                    ],
                },
                "warnings": [],
            }
        if name == "get_institution_average_salary":
            if self.salary_error:
                raise RuntimeError("ALIO timeout")
            return {
                "average_salary": {
                    "amount_krw": 74_146_000,
                    "year": 2025,
                    "basis": "결산",
                    "employment_group": "정규직",
                },
                "report": {
                    "source_url": "https://example.test/alio/salary",
                },
                "warnings": (
                    ["ALIO 최신 결산 공시를 확인해야 합니다."] if self.salary_warning else []
                ),
            }
        if name == "analyze_job_fit_report":
            return {
                "job_id": payload["job_id"],
                "preparation_items": [
                    {
                        "priority": "P0",
                        "title": "지원자격 확인",
                        "recommended_actions": ["직무기술서의 필요기술을 표로 정리하세요."],
                    }
                ],
                "knowledge_gaps": [
                    {
                        "title": "네트워크 보안 지식 확인",
                    }
                ],
                "warnings": [],
            }
        if name == "analyze_institution_strategy":
            return {
                "strategy_signals": [
                    {
                        "summary": "디지털 신뢰 기반 조성",
                        "job_connection": "정보보호 직무와 연결",
                        "evidence": [
                            {
                                "title": "ALIO 주요사업",
                                "source_type": "alio_disclosure",
                                "url": "https://example.test/alio/business",
                                "excerpt": "디지털 신뢰 기반 조성",
                            }
                        ],
                    }
                ],
                "warnings": [],
            }
        if name == "analyze_institution_weakness":
            return {
                "weakness_signals": [
                    {
                        "summary": "운영 체계 고도화 필요",
                        "careful_wording": "공시 근거에서 개선 필요성이 확인됩니다.",
                        "applicant_connection": "운영 자동화 경험과 연결합니다.",
                        "evidence": [
                            {
                                "title": "국회 지적사항",
                                "source_type": "alio_disclosure",
                                "url": "https://example.test/alio/audit",
                                "excerpt": "운영 체계 고도화 필요",
                            }
                        ],
                    }
                ],
                "warnings": [],
            }
        if name == "prepare_institution_interview":
            return {
                "interview_cards": [
                    {
                        "question_type": "지원동기",
                        "likely_question": "왜 이 기관의 정보보호 직무에 지원했나요?",
                        "answer_strategy": "기관 사업과 사용자 경험을 연결합니다.",
                        "answer_points": ["기관 사업", "직무 경험"],
                        "caution": "확인되지 않은 성과를 만들지 않습니다.",
                        "safe_framing": None,
                    }
                ],
                "materials_to_check": ["기관 주요사업 원문"],
                "warnings": [],
            }
        if name == "generate_star_answer_framework":
            return {
                "question": payload["question"],
                "interview_answer": {
                    "status": "ready",
                    "short_answer": "사용자 경험 기반 답변",
                },
                "cover_letter_draft": {
                    "status": "ready",
                    "sentence_draft": "사용자 경험 기반 문장",
                },
                "follow_up_questions": [],
                "risk_flags": [],
                "verification_notes": [],
            }
        raise AssertionError(f"unexpected tool call: {name}")


def _job_one() -> dict[str, Any]:
    return {
        "id": "job-1",
        "source_job_id": "job-1",
        "institution_name": "한국인터넷진흥원",
        "title": "정보보호 신입 채용",
        "start_date": "2026-07-01",
        "end_date": "2026-07-29",
        "recruitment_type": "신입",
        "employment_types": ["정규직"],
        "work_regions": ["서울"],
        "source_url": "https://example.test/job-1",
        "ncs_mappings": [{"code": "R600020", "display_name": "정보통신"}],
    }


def _job_two() -> dict[str, Any]:
    return {
        "id": "job-2",
        "source_job_id": "job-2",
        "institution_name": "한국인터넷진흥원",
        "title": "정보통신 경력 채용",
        "start_date": "2026-07-02",
        "end_date": "2026-07-31",
        "recruitment_type": "경력직",
        "employment_types": ["정규직"],
        "work_regions": ["서울"],
        "source_url": "https://example.test/job-2",
        "ncs_mappings": [{"code": "R600020", "display_name": "정보통신"}],
    }


def _ranking_job(number: int) -> dict[str, Any]:
    return {
        "id": f"rank-job-{number}",
        "source_job_id": f"rank-job-{number}",
        "institution_name": "한국인터넷진흥원",
        "title": f"정보보호 신입 채용 {number}",
        "start_date": "2026-07-01",
        "end_date": f"2026-07-{23 + number:02d}",
        "recruitment_type": "신입",
        "employment_types": ["정규직"],
        "work_regions": ["서울"],
        "source_url": f"https://example.test/rank-job-{number}",
        "ncs_mappings": [{"code": "R600020", "display_name": "정보통신"}],
    }


class RankingToolCaller(FakeToolCaller):
    def __call__(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        payload = dict(arguments or {})
        if name == "search_public_jobs":
            self.calls.append((name, payload))
            return {
                "jobs": [_ranking_job(number) for number in range(1, 5)],
                "warnings": [],
            }
        if name == "fetch_job_detail":
            self.calls.append((name, payload))
            number = int(str(payload["job_id"]).rsplit("-", 1)[1])
            return {
                "job": {
                    **_ranking_job(number),
                    "qualification": "정보보호 지식",
                    "preferred_conditions": (
                        "클라우드보안 역량 우대" if number == 4 else "관련 경험 우대"
                    ),
                },
                "warnings": [],
            }
        return super().__call__(name, arguments)


class DistinctNoJobsCaller(FakeToolCaller):
    def __call__(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        payload = dict(arguments or {})
        if name == "resolve_ncs_code":
            self.calls.append((name, payload))
            target = str(payload["target_role"])
            number = {"보안": 1, "전산": 2, "데이터": 3}[target]
            return {
                "selected_ncs_code": f"NCS-{number}",
                "selected_ncs_name": target,
                "confidence": "high",
                "warnings": [],
            }
        if name == "lookup_region_codes":
            self.calls.append((name, payload))
            region = str(payload["query"])
            number = {"서울": 1, "대전": 2, "부산": 3}[region]
            return {
                "matches": [{"code": f"REGION-{number}", "name": region}],
                "warnings": [],
            }
        if name == "search_public_jobs":
            self.calls.append((name, payload))
            return {
                "jobs": [],
                "diagnostics": {"reason": "no_results"},
                "warnings": [],
            }
        return super().__call__(name, arguments)


def _tool(caller: FakeToolCaller):
    return create_public_job_career_coach_tool(
        call_tool=caller,
        today_provider=lambda: date(2026, 7, 23),
    )


def test_execution_context_stops_starting_calls_after_elapsed_budget() -> None:
    calls: list[str] = []
    context = _ExecutionContext(
        call_tool=lambda name, _arguments: calls.append(name) or {},
    )
    context.started_at -= 60

    result = context.call(
        stage="late_stage",
        tool="search_public_jobs",
        arguments={},
    )

    assert result == {}
    assert calls == []
    assert context.degraded is True
    assert context.trace[0]["status"] == "skipped"
    assert "경과 시간" in context.trace[0]["reason"]


def test_job_search_auto_executes_and_returns_ranked_one_screen_result() -> None:
    caller = FakeToolCaller()

    result = _tool(caller).handler(
        {
            "support_mode": "job_search",
            "target_role": "정보보호",
            "career_level": "entry",
            "known_skills": ["정보보안기사"],
            "regions": ["서울"],
        }
    )

    assert result["status"] == "completed"
    assert result["dashboard"]["view"] == "job_discovery"
    rankings = result["dashboard"]["job_rankings"]
    assert [card["rank"] for card in rankings] == [1, 2]
    assert rankings[0]["job_id"] == "job-1"
    assert rankings[0]["deadline"] == {
        "date": "2026-07-29",
        "days_remaining": 6,
        "label": "D-6",
    }
    assert rankings[0]["average_compensation"]["amount_krw"] == 74_146_000
    assert "신입 초봉" in rankings[0]["average_compensation"]["caution"]
    assert rankings[0]["fit"]["scope"] == "profile_fit"
    assert rankings[0]["fit"]["level"] == "근거 있음"
    assert rankings[0]["fit"]["missing_competencies"] == ["네트워크 보안 지식 확인"]
    assert rankings[0]["links"]["application"] == "https://example.test/job-1"
    assert result["dashboard"]["today_actions"]

    call_names = [name for name, _arguments in caller.calls]
    assert call_names == [
        "resolve_ncs_code",
        "lookup_region_codes",
        "search_public_jobs",
        "fetch_job_detail",
        "fetch_job_detail",
        "get_institution_average_salary",
        "analyze_job_fit_report",
        "analyze_job_fit_report",
    ]
    assert sum(name == "get_institution_average_salary" for name in call_names) == 1
    assert any(
        entry["status"] == "cached" and entry["tool"] == "get_institution_average_salary"
        for entry in result["execution_trace"]
    )


def test_job_search_no_results_stops_before_detail_calls() -> None:
    caller = FakeToolCaller(no_jobs=True)

    result = _tool(caller).handler(
        {
            "support_mode": "job_search",
            "target_role": "정보보호",
            "career_level": "entry",
        }
    )

    assert result["status"] == "no_results"
    assert result["dashboard"]["job_rankings"] == []
    assert [name for name, _arguments in caller.calls] == [
        "resolve_ncs_code",
        "search_public_jobs",
    ]
    resolve_arguments = caller.calls[0][1]
    assert "known_skills" not in resolve_arguments


def test_job_search_ranks_after_detail_skill_evaluation() -> None:
    caller = RankingToolCaller()

    result = _tool(caller).handler(
        {
            "support_mode": "job_search",
            "target_role": "정보보호",
            "career_level": "entry",
            "known_skills": ["클라우드보안"],
        }
    )

    rankings = result["dashboard"]["job_rankings"]
    assert rankings[0]["job_id"] == "rank-job-4"
    assert result["dashboard"]["candidate_counts"] == {
        "searched": 4,
        "detail_evaluated": 4,
        "displayed": 3,
    }
    assert sum(name == "fetch_job_detail" for name, _arguments in caller.calls) == 4
    assert sum(name == "analyze_job_fit_report" for name, _arguments in caller.calls) == 3


def test_job_search_deduplicates_equivalent_search_scopes() -> None:
    caller = FakeToolCaller()

    result = _tool(caller).handler(
        {
            "support_mode": "beginner",
            "career_level": "entry",
            "interests": ["정보보호", "보안", "정보통신"],
            "regions": ["서울", "서울특별시", "서울시"],
        }
    )

    assert result["status"] == "completed"
    assert sum(name == "search_public_jobs" for name, _arguments in caller.calls) == 1
    assert (
        sum(entry["status"] in {"success", "failed"} for entry in result["execution_trace"]) <= 12
    )


def test_beginner_search_budget_balances_targets_and_regions() -> None:
    caller = DistinctNoJobsCaller()

    result = _tool(caller).handler(
        {
            "support_mode": "beginner",
            "career_level": "entry",
            "interests": ["보안", "전산", "데이터"],
            "regions": ["서울", "대전", "부산"],
        }
    )

    search_arguments = [
        arguments for name, arguments in caller.calls if name == "search_public_jobs"
    ]
    assert [
        (arguments["ncs_code"], arguments["region_code"]) for arguments in search_arguments
    ] == [
        ("NCS-1", "REGION-1"),
        ("NCS-2", "REGION-2"),
        ("NCS-3", "REGION-3"),
    ]
    assert result["status"] == "no_results"
    assert result["dashboard"]["search_coverage"] == {
        "available_combinations": 9,
        "queried_combinations": 3,
        "complete": False,
    }
    assert (
        "전체 입력 조합의 무결과를 뜻하지 않습니다" in result["dashboard"]["scope_interpretation"]
    )
    assert any("분산한 3개만" in warning for warning in result["warnings"])


def test_job_search_marks_region_truncation_as_partial() -> None:
    caller = FakeToolCaller()

    result = _tool(caller).handler(
        {
            "support_mode": "job_search",
            "target_role": "정보보호",
            "career_level": "entry",
            "regions": ["서울", "경기", "대전", "부산"],
        }
    )

    assert result["status"] == "partial_success"
    assert any("앞의 3개" in warning for warning in result["warnings"])


def test_job_search_keeps_job_when_salary_lookup_fails() -> None:
    caller = FakeToolCaller(salary_error=True)

    result = _tool(caller).handler(
        {
            "support_mode": "job_search",
            "target_role": "정보보호",
            "career_level": "entry",
            "max_results": 1,
        }
    )

    assert result["status"] == "partial_success"
    assert result["dashboard"]["job_rankings"][0]["job_id"] == "job-1"
    assert result["dashboard"]["job_rankings"][0]["average_compensation"] is None
    assert any("ALIO timeout" in warning for warning in result["warnings"])


def test_downstream_warning_marks_result_as_partial() -> None:
    caller = FakeToolCaller(salary_warning=True)

    result = _tool(caller).handler(
        {
            "support_mode": "job_search",
            "target_role": "정보보호",
            "career_level": "entry",
            "max_results": 1,
        }
    )

    assert result["status"] == "partial_success"
    assert any("최신 결산 공시" in warning for warning in result["warnings"])


def test_application_auto_executes_detail_salary_fit_and_star() -> None:
    caller = FakeToolCaller()

    result = _tool(caller).handler(
        {
            "support_mode": "application",
            "job_id": "job-1",
            "target_role": "정보보호",
            "career_level": "entry",
            "known_skills": ["정보보안기사"],
            "user_experiences": ["로그 분석으로 반복 오류를 줄인 경험"],
        }
    )

    assert result["status"] == "completed"
    assert result["dashboard"]["view"] == "application_package"
    assert result["dashboard"]["job"]["job_id"] == "job-1"
    assert len(result["dashboard"]["star_frameworks"]) == 1
    assert [name for name, _arguments in caller.calls] == [
        "fetch_job_detail",
        "get_institution_average_salary",
        "analyze_job_fit_report",
        "generate_star_answer_framework",
    ]
    assert "preserved_arguments" not in result
    assert result["input_summary"]["user_experience_count"] == 1
    assert "user_experiences" not in result["input_summary"]


def test_application_uses_detail_institution_for_salary_when_input_differs() -> None:
    caller = FakeToolCaller()

    result = _tool(caller).handler(
        {
            "support_mode": "application",
            "job_id": "job-1",
            "institution_name": "한국전력공사",
            "target_role": "정보보호",
        }
    )

    salary_arguments = next(
        arguments for name, arguments in caller.calls if name == "get_institution_average_salary"
    )
    assert salary_arguments["institution_name"] == "한국인터넷진흥원"
    assert (
        result["dashboard"]["job"]["average_compensation"]["institution_name"] == "한국인터넷진흥원"
    )
    assert result["status"] == "partial_success"
    assert any("공고 상세 기관명" in warning for warning in result["warnings"])


def test_interview_auto_executes_institution_analysis_and_star() -> None:
    caller = FakeToolCaller()

    result = _tool(caller).handler(
        {
            "support_mode": "interview",
            "institution_name": "한국인터넷진흥원",
            "target_role": "정보보호",
            "user_experiences": ["보안 점검 절차를 개선한 경험"],
        }
    )

    assert result["status"] == "completed"
    assert result["dashboard"]["view"] == "interview_package"
    assert result["dashboard"]["strategy_signals"][0]["summary"] == "디지털 신뢰 기반 조성"
    assert result["dashboard"]["improvement_signals"][0]["summary"] == "운영 체계 고도화 필요"
    assert result["dashboard"]["interview_questions"][0]["question_type"] == "지원동기"
    assert len(result["dashboard"]["star_frameworks"]) == 1
    assert [name for name, _arguments in caller.calls] == [
        "resolve_ncs_code",
        "analyze_institution_strategy",
        "analyze_institution_weakness",
        "prepare_institution_interview",
        "get_institution_average_salary",
        "generate_star_answer_framework",
    ]
    interview_arguments = next(
        arguments for name, arguments in caller.calls if name == "prepare_institution_interview"
    )
    assert interview_arguments["fetch_live_alio"] is False
    assert interview_arguments["evidence"]
    resolve_arguments = next(
        arguments for name, arguments in caller.calls if name == "resolve_ncs_code"
    )
    assert "known_skills" not in resolve_arguments


def test_interview_excludes_mismatched_optional_job_context() -> None:
    caller = FakeToolCaller()

    result = _tool(caller).handler(
        {
            "support_mode": "interview",
            "institution_name": "한국전력공사",
            "target_role": "정보보호",
            "job_id": "job-1",
        }
    )

    assert result["status"] == "partial_success"
    assert result["dashboard"]["job"] is None
    assert any("공고 맥락은 제외" in warning for warning in result["warnings"])
    salary_arguments = next(
        arguments for name, arguments in caller.calls if name == "get_institution_average_salary"
    )
    assert salary_arguments["institution_name"] == "한국전력공사"
    assert [step["tool"] for step in result["workflow_steps"]] == [
        entry["tool"] for entry in result["execution_trace"] if entry["status"] != "skipped"
    ]


def test_auto_execution_limits_star_experiences_to_three() -> None:
    caller = FakeToolCaller()

    result = _tool(caller).handler(
        {
            "support_mode": "application",
            "job_id": "job-1",
            "target_role": "정보보호",
            "user_experiences": ["경험 1", "경험 2", "경험 3", "경험 4"],
        }
    )

    assert result["status"] == "partial_success"
    assert len(result["dashboard"]["star_frameworks"]) == 3
    assert sum(name == "generate_star_answer_framework" for name, _arguments in caller.calls) == 3


def test_standalone_factory_defaults_to_plan_and_rejects_explicit_auto_execution() -> None:
    tool = create_public_job_career_coach_tool()
    arguments = {
        "support_mode": "job_search",
        "target_role": "정보보호",
        "career_level": "entry",
    }

    assert tool.input_schema["properties"]["auto_execute"]["default"] is False
    assert tool.handler(arguments)["status"] == "workflow_ready"

    with pytest.raises(ValueError, match="requires an injected tool caller"):
        tool.handler({**arguments, "auto_execute": True})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("max_results", 4, "max_results must be between 1 and 3"),
        ("year", 1999, "year must be between 2000 and 2100"),
        ("as_of_date", "2026-02-30", "as_of_date must be a valid"),
        ("auto_execute", "sometimes", "auto_execute must be a boolean"),
    ],
)
def test_execution_options_are_strictly_validated(
    field: str,
    value: object,
    message: str,
) -> None:
    tool = create_public_job_career_coach_tool()

    with pytest.raises(ValueError, match=message):
        tool.handler(
            {
                "support_mode": "job_search",
                "target_role": "정보보호",
                "career_level": "entry",
                field: value,
            }
        )
