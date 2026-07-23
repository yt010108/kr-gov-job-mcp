"""Guided entry-point tool for public-sector job preparation."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Any

from kr_gov_job_mcp.tools.career_coach_execution import (
    TodayProvider,
    ToolCaller,
    execute_public_job_career_workflow,
)
from kr_gov_job_mcp.tools.registry import (
    ToolDefinition,
    non_blank_string_schema,
    read_only_tool_annotations,
)


def _bounded_text_schema(description: str, *, max_length: int) -> dict[str, Any]:
    return {
        **non_blank_string_schema(description),
        "maxLength": max_length,
    }


PUBLIC_JOB_CAREER_COACH_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "support_mode": {
            "type": "string",
            "enum": ["beginner", "job_search", "application", "interview"],
            "description": "사용자가 선택한 공공기관 취업 지원 유형입니다.",
        },
        "career_level": {
            "type": "string",
            "enum": ["entry", "experienced", "any"],
            "description": "신입(entry), 경력(experienced), 무관(any) 중 하나입니다.",
        },
        "interests": {
            "type": "array",
            "items": _bounded_text_schema(
                "관심 업무, 분야 또는 경험입니다.",
                max_length=300,
            ),
            "maxItems": 10,
            "uniqueItems": True,
            "description": "처음 준비하는 사용자의 관심 업무, 분야 또는 경험입니다.",
        },
        "target_role": _bounded_text_schema(
            "목표 직무 또는 준비하려는 직무입니다.",
            max_length=300,
        ),
        "known_skills": {
            "type": "array",
            "items": _bounded_text_schema(
                "보유 기술, 자격증 또는 경험입니다.",
                max_length=300,
            ),
            "maxItems": 20,
            "uniqueItems": True,
            "description": "사용자가 이미 보유한 기술, 자격증 또는 경험입니다.",
        },
        "regions": {
            "type": "array",
            "items": _bounded_text_schema("희망 근무지역입니다.", max_length=100),
            "maxItems": 10,
            "uniqueItems": True,
            "description": "희망 근무지역 목록입니다.",
        },
        "job_id": _bounded_text_schema("Job-ALIO 채용공고 ID입니다.", max_length=200),
        "source_job_id": _bounded_text_schema(
            "search_public_jobs가 반환한 source_job_id입니다.",
            max_length=200,
        ),
        "recruitment_notice_sn": _bounded_text_schema(
            "Job-ALIO 채용공고 일련번호(recrutPblntSn)입니다.",
            max_length=200,
        ),
        "institution_name": _bounded_text_schema(
            "지원하거나 면접을 준비할 기관명입니다.",
            max_length=300,
        ),
        "user_experiences": {
            "type": "array",
            "items": _bounded_text_schema(
                "자기소개서나 면접 답변에 사용할 실제 경험입니다.",
                max_length=2_000,
            ),
            "maxItems": 10,
            "uniqueItems": True,
            "description": "STAR 구성에 사용할 사용자의 실제 경험 목록입니다.",
        },
        "question": _bounded_text_schema(
            "STAR 답변을 준비할 자기소개서 문항 또는 면접 질문입니다.",
            max_length=2_000,
        ),
        "preparation_notes": _bounded_text_schema(
            "지원 준비 상태나 경험에 대한 추가 메모입니다.",
            max_length=4_000,
        ),
        "year": {
            "type": "integer",
            "minimum": 2000,
            "maximum": 2100,
            "description": "기관 분석과 평균보수 조회에 사용할 기준 연도입니다.",
        },
        "as_of_date": {
            "type": "string",
            "format": "date",
            "maxLength": 10,
            "description": "D-day 계산 기준일입니다. 생략하면 호출일을 사용합니다.",
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 3,
            "default": 3,
            "description": "자동 실행 후 한 화면에 표시할 최대 공고 수입니다.",
        },
        "fetch_live_alio": {
            "type": "boolean",
            "default": True,
            "description": "기관 분석 단계에서 ALIO 실시간 조회를 허용할지 여부입니다.",
        },
        "auto_execute": {
            "type": "boolean",
            "default": True,
            "description": "필수 정보가 모이면 후속 도구를 자동 실행할지 여부입니다.",
        },
    },
    "additionalProperties": False,
}

_SUPPORTED_ARGUMENTS = set(PUBLIC_JOB_CAREER_COACH_INPUT_SCHEMA["properties"])
_SUPPORT_MODES = {"beginner", "job_search", "application", "interview"}
_CAREER_LEVELS = {"entry", "experienced", "any"}
_JOB_ID_FIELDS = ("job_id", "source_job_id", "recruitment_notice_sn")
_LIST_FIELDS = ("interests", "known_skills", "regions", "user_experiences")
_TEXT_FIELDS = (
    "target_role",
    "job_id",
    "source_job_id",
    "recruitment_notice_sn",
    "institution_name",
    "question",
    "preparation_notes",
    "as_of_date",
)
_TEXT_MAX_LENGTHS = {
    "target_role": 300,
    "job_id": 200,
    "source_job_id": 200,
    "recruitment_notice_sn": 200,
    "institution_name": 300,
    "question": 2_000,
    "preparation_notes": 4_000,
    "as_of_date": 10,
}
_LIST_LIMITS = {
    "interests": (10, 300),
    "known_skills": (20, 300),
    "regions": (10, 100),
    "user_experiences": (10, 2_000),
}
_KOREA_STANDARD_TIME = timezone(timedelta(hours=9))

_CHOICES = [
    {
        "id": "beginner",
        "number": 1,
        "label": "처음 준비하고 있어요",
        "description": "관심 분야를 바탕으로 직무와 공고 탐색 순서를 안내합니다.",
    },
    {
        "id": "job_search",
        "number": 2,
        "label": "지원할 공고를 찾고 있어요",
        "description": "목표 직무와 조건에 맞는 공고 탐색 순서를 안내합니다.",
    },
    {
        "id": "application",
        "number": 3,
        "label": "지원할 공고가 정해졌어요",
        "description": "공고 상세, 적합도와 지원 준비 순서를 안내합니다.",
    },
    {
        "id": "interview",
        "number": 4,
        "label": "면접을 준비하고 있어요",
        "description": "기관 분석, 예상 질문과 STAR 준비 순서를 안내합니다.",
    },
]

_MENU = "\n".join(
    [
        "공공기관 취업 준비 상태를 선택해 주세요.",
        "1. 처음 준비하고 있어요",
        "2. 지원할 공고를 찾고 있어요",
        "3. 지원할 공고가 정해졌어요",
        "4. 면접을 준비하고 있어요",
        "번호나 현재 상황을 말씀해 주세요.",
    ]
)

_QUESTIONS: dict[str, dict[str, Any]] = {
    "career_level": {
        "field": "career_level",
        "prompt": "신입, 경력, 무관 중 어디에 해당하나요?",
        "choices": [
            {"id": "entry", "label": "신입"},
            {"id": "experienced", "label": "경력"},
            {"id": "any", "label": "무관"},
        ],
    },
    "interests": {
        "field": "interests",
        "prompt": "관심 있는 업무·분야나 해 본 경험을 하나 이상 알려주세요.",
    },
    "target_role": {
        "field": "target_role",
        "prompt": "어떤 직무의 공고를 찾거나 준비하고 있나요?",
    },
    "job_id": {
        "field": "job_id",
        "prompt": (
            "지원할 Job-ALIO 공고 ID를 알려주세요. job_id, source_job_id, "
            "recruitment_notice_sn 중 하나를 사용할 수 있습니다."
        ),
        "accepted_aliases": list(_JOB_ID_FIELDS),
    },
    "institution_name": {
        "field": "institution_name",
        "prompt": "면접을 준비할 공공기관 이름을 알려주세요.",
    },
}


def create_public_job_career_coach_tool(
    *,
    call_tool: ToolCaller | None = None,
    today_provider: TodayProvider | None = None,
) -> ToolDefinition:
    """Create the guided router and optional in-process workflow orchestrator.

    Registry deployments inject ``call_tool`` and default to automatic execution.
    A standalone definition without a caller defaults to plan-only mode; explicitly
    requesting automatic execution still raises a configuration error.
    """

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        normalized = _normalize_arguments(arguments)
        support_mode = normalized.get("support_mode")
        if support_mode is None:
            return {
                "status": "needs_user_selection",
                "menu": _MENU,
                "choices": [dict(choice) for choice in _CHOICES],
                "next_call": {
                    "tool": "public_job_career_coach",
                    "required_field": "support_mode",
                },
            }

        missing_fields = _missing_fields(support_mode, normalized)
        if missing_fields:
            return {
                "status": "needs_more_information",
                "support_mode": support_mode,
                "questions": [dict(_QUESTIONS[field]) for field in missing_fields],
                "missing_fields": missing_fields,
                "preserved_arguments": normalized,
                "next_call": {
                    "tool": "public_job_career_coach",
                    "arguments": normalized,
                    "fields_to_add": missing_fields,
                },
            }

        workflow_steps = _workflow_steps(support_mode, normalized)
        auto_execute = normalized.get("auto_execute", call_tool is not None)
        if auto_execute is False:
            return {
                "status": "workflow_ready",
                "support_mode": support_mode,
                "preserved_arguments": normalized,
                "workflow_steps": workflow_steps,
                "next_call": None,
            }
        if call_tool is None:
            raise ValueError(
                "public_job_career_coach auto execution requires an injected tool caller"
            )
        return execute_public_job_career_workflow(
            support_mode=support_mode,
            arguments=normalized,
            workflow_steps=workflow_steps,
            call_tool=call_tool,
            today_provider=today_provider or _seoul_today,
        )

    input_schema = PUBLIC_JOB_CAREER_COACH_INPUT_SCHEMA
    if call_tool is None:
        input_schema = deepcopy(PUBLIC_JOB_CAREER_COACH_INPUT_SCHEMA)
        input_schema["properties"]["auto_execute"]["default"] = False

    return ToolDefinition(
        name="public_job_career_coach",
        description=(
            "kr-gov-job-mcp의 대표 진입 도구입니다. 공공기관 취업을 포괄적으로 도와달라는 "
            "요청에서 사용자 유형을 먼저 선택하게 하고, 필요한 정보가 모이면 기존 MCP 도구를 "
            "안전한 순서로 자동 호출합니다. 공고·D-day·평균보수·적합 근거·보완 역량·오늘 할 일·"
            "지원 링크 또는 기관 면접 준비 결과를 한 화면용 응답으로 통합합니다."
        ),
        input_schema=input_schema,
        annotations=read_only_tool_annotations("Public Job Career Coach", open_world=True),
        handler=handler,
    )


def _normalize_arguments(arguments: Mapping[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(arguments) - _SUPPORTED_ARGUMENTS)
    if unknown:
        raise ValueError("unsupported public_job_career_coach arguments: " + ", ".join(unknown))

    normalized: dict[str, Any] = {}
    support_mode = _optional_text(arguments.get("support_mode"), "support_mode")
    if support_mode is not None:
        if support_mode not in _SUPPORT_MODES:
            raise ValueError(
                "support_mode must be one of: beginner, job_search, application, interview"
            )
        normalized["support_mode"] = support_mode

    career_level = _optional_text(arguments.get("career_level"), "career_level")
    if career_level is not None:
        if career_level not in _CAREER_LEVELS:
            raise ValueError("career_level must be one of: entry, experienced, any")
        normalized["career_level"] = career_level

    for field in _TEXT_FIELDS:
        text = _optional_text(arguments.get(field), field)
        if text is not None:
            max_length = _TEXT_MAX_LENGTHS[field]
            if len(text) > max_length:
                raise ValueError(f"{field} must be at most {max_length} characters")
            normalized[field] = text

    for field in _LIST_FIELDS:
        if field not in arguments or arguments[field] is None:
            continue
        max_items, max_item_length = _LIST_LIMITS[field]
        values = _text_list(
            arguments.get(field),
            field,
            max_items=max_items,
            max_item_length=max_item_length,
        )
        normalized[field] = values

    if "max_results" in arguments and arguments["max_results"] is not None:
        normalized["max_results"] = _integer(
            arguments["max_results"],
            field="max_results",
            default=None,
            minimum=1,
            maximum=3,
        )
    if "auto_execute" in arguments and arguments["auto_execute"] is not None:
        normalized["auto_execute"] = _boolean(
            arguments["auto_execute"],
            field="auto_execute",
            default=True,
        )
    if "fetch_live_alio" in arguments and arguments["fetch_live_alio"] is not None:
        normalized["fetch_live_alio"] = _boolean(
            arguments["fetch_live_alio"],
            field="fetch_live_alio",
            default=True,
        )
    if "year" in arguments and arguments["year"] is not None:
        normalized["year"] = _integer(
            arguments["year"],
            field="year",
            default=None,
            minimum=2000,
            maximum=2100,
        )
    if as_of_date := normalized.get("as_of_date"):
        try:
            date.fromisoformat(as_of_date)
        except ValueError as exc:
            raise ValueError("as_of_date must be a valid YYYY-MM-DD date") from exc

    _validate_job_id_aliases(normalized)
    return normalized


def _missing_fields(support_mode: str, arguments: Mapping[str, Any]) -> list[str]:
    if support_mode == "beginner":
        return [field for field in ("career_level", "interests") if not arguments.get(field)]
    if support_mode == "job_search":
        return [field for field in ("target_role", "career_level") if not arguments.get(field)]
    if support_mode == "application":
        return [] if any(arguments.get(field) for field in _JOB_ID_FIELDS) else ["job_id"]
    return [field for field in ("institution_name", "target_role") if not arguments.get(field)]


def _workflow_steps(support_mode: str, arguments: Mapping[str, Any]) -> list[dict[str, Any]]:
    if support_mode == "beginner":
        steps = [
            (
                "resolve_ncs_code",
                "관심 분야를 Job-ALIO NCS 코드 후보로 해석합니다.",
            ),
        ]
        if arguments.get("regions"):
            steps.append(
                (
                    "lookup_region_codes",
                    "희망 근무지역을 Job-ALIO 지역 코드로 확인합니다.",
                )
            )
        steps.extend(
            [
                (
                    "search_public_jobs",
                    "해석한 직무 후보로 현재 공공기관 채용공고를 탐색합니다.",
                ),
                (
                    "fetch_job_detail",
                    "검색 결과의 후보 공고를 상세 조회해 자격과 직무 정보를 확인합니다.",
                ),
                (
                    "get_institution_average_salary",
                    "후보 기관의 평균보수를 공시 근거와 함께 확인합니다.",
                ),
                (
                    "analyze_job_fit_report",
                    "공고 요구사항과 현재 준비 상태를 비교해 준비 항목을 정리합니다.",
                ),
            ]
        )
    elif support_mode == "job_search":
        steps = [
            (
                "resolve_ncs_code",
                "목표 직무를 Job-ALIO NCS 코드 후보로 해석합니다.",
            ),
        ]
        if arguments.get("regions"):
            steps.append(
                (
                    "lookup_region_codes",
                    "희망 근무지역을 Job-ALIO 지역 코드로 확인합니다.",
                )
            )
        steps.extend(
            [
                (
                    "search_public_jobs",
                    "직무, 경력 수준과 희망 지역 조건으로 공고를 검색합니다.",
                ),
                (
                    "fetch_job_detail",
                    "후보 공고별 지원자격과 직무 상세를 확인합니다.",
                ),
                (
                    "get_institution_average_salary",
                    "후보 기관의 평균보수를 공시 근거와 함께 확인합니다.",
                ),
                (
                    "analyze_job_fit_report",
                    "보유 역량을 공고 요구사항과 비교해 준비 항목을 정리합니다.",
                ),
            ]
        )
    elif support_mode == "application":
        steps = [
            (
                "fetch_job_detail",
                "선택한 공고의 지원자격, 전형과 직무기술 정보를 확인합니다.",
            ),
            (
                "get_institution_average_salary",
                "지원 기관의 평균보수를 공시 근거와 함께 확인합니다.",
            ),
            (
                "analyze_job_fit_report",
                "공고 요구사항과 보유 역량을 비교해 지원 준비 항목을 정리합니다.",
            ),
        ]
        if arguments.get("user_experiences"):
            steps.append(
                (
                    "generate_star_answer_framework",
                    "사용자가 제공한 실제 경험으로 자기소개서·면접용 STAR 틀을 만듭니다.",
                )
            )
    else:
        steps = []
        if any(arguments.get(field) for field in _JOB_ID_FIELDS):
            steps.append(
                (
                    "fetch_job_detail",
                    "선택한 공고의 직무와 전형 정보를 면접 준비 근거로 확인합니다.",
                )
            )
        steps.append(
            (
                "resolve_ncs_code",
                "목표 직무를 기관 분석과 면접 준비에 사용할 NCS 맥락으로 해석합니다.",
            )
        )
        steps.extend(
            [
                (
                    "analyze_institution_strategy",
                    "기관의 주요 사업과 전략 근거를 정리합니다.",
                ),
                (
                    "analyze_institution_weakness",
                    "기관의 개선과제를 검증 가능한 근거와 함께 정리합니다.",
                ),
                (
                    "prepare_institution_interview",
                    "기관과 목표 직무에 맞는 면접 질문 카드를 준비합니다.",
                ),
                (
                    "get_institution_average_salary",
                    "지원 기관의 평균보수를 공시 근거와 함께 확인합니다.",
                ),
            ]
        )
        if arguments.get("user_experiences"):
            steps.append(
                (
                    "generate_star_answer_framework",
                    "사용자가 제공한 실제 경험으로 면접용 STAR 답변 틀을 만듭니다.",
                )
            )

    return [
        {"order": index, "tool": tool, "purpose": purpose}
        for index, (tool, purpose) in enumerate(steps, start=1)
    ]


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} must be non-blank when provided")
    return text


def _text_list(
    value: Any,
    field: str,
    *,
    max_items: int,
    max_item_length: int,
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    if len(value) > max_items:
        raise ValueError(f"{field} must contain at most {max_items} items")
    values: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            raise ValueError(f"{field} items must be non-blank")
        if len(text) > max_item_length:
            raise ValueError(f"{field} items must be at most {max_item_length} characters")
        if text not in values:
            values.append(text)
    return values


def _seoul_today() -> date:
    """Return the calendar date used by Korean public recruitment notices."""

    return datetime.now(_KOREA_STANDARD_TIME).date()


def _integer(
    value: Any,
    *,
    field: str,
    default: int | None,
    minimum: int,
    maximum: int,
) -> int:
    if value is None or value == "":
        if default is None:
            raise ValueError(f"{field} is required")
        return default
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    try:
        number = int(str(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return number


def _boolean(value: Any, *, field: str, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"{field} must be a boolean")


def _validate_job_id_aliases(arguments: Mapping[str, Any]) -> None:
    provided = {
        field: arguments[field] for field in _JOB_ID_FIELDS if arguments.get(field) is not None
    }
    if len(set(provided.values())) <= 1:
        return
    detail = ", ".join(f"{field}={value}" for field, value in provided.items())
    raise ValueError("conflicting public_job_career_coach job ids: " + detail)
