"""Guided entry-point tool for public-sector job preparation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.tools.registry import (
    ToolDefinition,
    non_blank_string_schema,
    read_only_tool_annotations,
)


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
            "items": non_blank_string_schema("관심 업무, 분야 또는 경험입니다."),
            "uniqueItems": True,
            "description": "처음 준비하는 사용자의 관심 업무, 분야 또는 경험입니다.",
        },
        "target_role": non_blank_string_schema("목표 직무 또는 준비하려는 직무입니다."),
        "known_skills": {
            "type": "array",
            "items": non_blank_string_schema("보유 기술, 자격증 또는 경험입니다."),
            "uniqueItems": True,
            "description": "사용자가 이미 보유한 기술, 자격증 또는 경험입니다.",
        },
        "regions": {
            "type": "array",
            "items": non_blank_string_schema("희망 근무지역입니다."),
            "uniqueItems": True,
            "description": "희망 근무지역 목록입니다.",
        },
        "job_id": non_blank_string_schema("Job-ALIO 채용공고 ID입니다."),
        "source_job_id": non_blank_string_schema(
            "search_public_jobs가 반환한 source_job_id입니다."
        ),
        "recruitment_notice_sn": non_blank_string_schema(
            "Job-ALIO 채용공고 일련번호(recrutPblntSn)입니다."
        ),
        "institution_name": non_blank_string_schema("지원하거나 면접을 준비할 기관명입니다."),
        "user_experiences": {
            "type": "array",
            "items": non_blank_string_schema("자기소개서나 면접 답변에 사용할 실제 경험입니다."),
            "uniqueItems": True,
            "description": "STAR 구성에 사용할 사용자의 실제 경험 목록입니다.",
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
)

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


def create_public_job_career_coach_tool() -> ToolDefinition:
    """Create the stateless guided workflow router."""

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

        return {
            "status": "workflow_ready",
            "support_mode": support_mode,
            "preserved_arguments": normalized,
            "workflow_steps": _workflow_steps(support_mode, normalized),
            "next_call": None,
        }

    return ToolDefinition(
        name="public_job_career_coach",
        description=(
            "kr-gov-job-mcp의 대표 진입 도구입니다. 공공기관 취업을 포괄적으로 도와달라는 "
            "요청에서 사용자 유형을 먼저 선택하게 하고, 필요한 정보가 모이면 기존 MCP 도구를 "
            "안전한 순서로 사용할 계획을 반환합니다. 이 v1 도구는 계획만 반환하며 다른 도구를 "
            "직접 호출하지 않습니다."
        ),
        input_schema=PUBLIC_JOB_CAREER_COACH_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Public Job Career Coach", open_world=False),
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
            normalized[field] = text

    for field in _LIST_FIELDS:
        if field not in arguments or arguments[field] is None:
            continue
        values = _text_list(arguments.get(field), field)
        normalized[field] = values

    _validate_job_id_aliases(normalized)
    return normalized


def _missing_fields(support_mode: str, arguments: Mapping[str, Any]) -> list[str]:
    if support_mode == "beginner":
        return [
            field
            for field in ("career_level", "interests")
            if not arguments.get(field)
        ]
    if support_mode == "job_search":
        return [
            field
            for field in ("target_role", "career_level")
            if not arguments.get(field)
        ]
    if support_mode == "application":
        return [] if any(arguments.get(field) for field in _JOB_ID_FIELDS) else ["job_id"]
    return [
        field
        for field in ("institution_name", "target_role")
        if not arguments.get(field)
    ]


def _workflow_steps(support_mode: str, arguments: Mapping[str, Any]) -> list[dict[str, Any]]:
    if support_mode == "beginner":
        steps = [
            (
                "lookup_job_alio_codes",
                "관심 분야를 Job-ALIO NCS·기관 코드 후보로 해석합니다.",
            ),
            (
                "search_public_jobs",
                "해석한 직무 후보로 현재 공공기관 채용공고를 탐색합니다.",
            ),
            (
                "fetch_job_detail",
                "검색 결과의 후보 공고를 상세 조회해 자격과 직무 정보를 확인합니다.",
            ),
        ]
    elif support_mode == "job_search":
        steps = [
            (
                "lookup_job_alio_codes",
                "목표 직무를 Job-ALIO 검색 코드 후보로 해석합니다.",
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


def _text_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    values: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            raise ValueError(f"{field} items must be non-blank")
        if text not in values:
            values.append(text)
    return values


def _validate_job_id_aliases(arguments: Mapping[str, Any]) -> None:
    provided = {
        field: arguments[field]
        for field in _JOB_ID_FIELDS
        if arguments.get(field) is not None
    }
    if len(set(provided.values())) <= 1:
        return
    detail = ", ".join(f"{field}={value}" for field, value in provided.items())
    raise ValueError("conflicting public_job_career_coach job ids: " + detail)
