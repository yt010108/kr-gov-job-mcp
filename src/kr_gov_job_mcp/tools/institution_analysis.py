"""MCP-style tools for institution analysis reports."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.analysis import (
    generate_institution_interview_report,
    generate_institution_strategy_report,
    generate_institution_weakness_report,
    prepare_institution_analysis_input,
)
from kr_gov_job_mcp.analysis.alio_institution_context import (
    AlioInstitutionContext,
    fetch_alio_institution_context_sync,
)
from kr_gov_job_mcp.schemas.institution import (
    InstitutionEvidence,
    InstitutionSignalCandidate,
)
from kr_gov_job_mcp.tools.registry import (
    ToolDefinition,
    non_blank_string_schema,
    read_only_tool_annotations,
)


ANALYZE_INSTITUTION_STRATEGY_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": non_blank_string_schema("분석할 기관명입니다."),
        "year": {
            "type": "integer",
            "description": "분석 기준 연도입니다.",
        },
        "job_family": {
            "type": "string",
            "description": "기관 분석에서 사용할 직무 관점입니다. Job-ALIO 채용 검색 필터가 아니며, resolver가 선택한 NCS명은 이 필드에 함께 보존할 수 있습니다.",
        },
        "original_job_family": {
            "type": "string",
            "description": "resolver 호출 전 사용자가 입력한 원문 직무군입니다. resolver가 선택한 NCS명과 다를 때 보존합니다.",
        },
        "target_role": {
            "type": "string",
            "description": "resolver가 보존한 원문 목표 직무명입니다. 기관 전략의 직무 연결 축은 job_family를 사용합니다.",
        },
        "original_target_role": {
            "type": "string",
            "description": "사용자가 처음 표현한 원문 목표 직무명입니다. NCS명과 다를 때 원문 관점을 보존합니다.",
        },
        "ncs_code": {
            "type": "string",
            "description": "resolve_ncs_code가 선택한 Job-ALIO NCS 코드입니다. 기관 분석의 검색 필터로 사용하지 않고 호출 맥락에만 보존합니다.",
        },
        "alio_id": {
            "type": "string",
            "description": "ALIO 기관 코드(apbaId)입니다. 예: C1304",
        },
        "apba_id": {
            "type": "string",
            "description": "ALIO 기관 코드(apbaId)의 별칭입니다.",
        },
        "fetch_live_alio": {
            "type": "boolean",
            "default": True,
            "description": "evidence/signals가 없을 때 ALIO 공시를 실시간 조회할지 여부입니다.",
        },
        "evidence": {
            "type": "array",
            "items": {"type": "object"},
            "default": [],
            "description": "ALIO, 클린아이, 기관 홈페이지, 수동 입력에서 가져온 기관 근거 후보입니다.",
        },
        "signals": {
            "type": "array",
            "items": {"type": "object"},
            "default": [],
            "description": "근거가 연결된 사전 추출 기관 signal 후보입니다.",
        },
    },
    "required": ["institution_name"],
    "additionalProperties": False,
}


_STRATEGY_ARGUMENTS = set(ANALYZE_INSTITUTION_STRATEGY_INPUT_SCHEMA["properties"])

ANALYZE_INSTITUTION_WEAKNESS_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": non_blank_string_schema("분석할 기관명입니다."),
        "year": {
            "type": "integer",
            "description": "분석 기준 연도입니다.",
        },
        "alio_id": {
            "type": "string",
            "description": "ALIO 기관 코드(apbaId)입니다. 예: C1304",
        },
        "apba_id": {
            "type": "string",
            "description": "ALIO 기관 코드(apbaId)의 별칭입니다.",
        },
        "fetch_live_alio": {
            "type": "boolean",
            "default": True,
            "description": "evidence/signals가 없을 때 ALIO 공시를 실시간 조회할지 여부입니다.",
        },
        "evidence": {
            "type": "array",
            "items": {"type": "object"},
            "default": [],
            "description": "ALIO, 클린아이, 수동 입력에서 가져온 개선 과제 근거 후보입니다.",
        },
        "signals": {
            "type": "array",
            "items": {"type": "object"},
            "default": [],
            "description": "근거가 연결된 사전 추출 개선 과제 signal 후보입니다.",
        },
    },
    "required": ["institution_name"],
    "additionalProperties": False,
}

_WEAKNESS_ARGUMENTS = set(ANALYZE_INSTITUTION_WEAKNESS_INPUT_SCHEMA["properties"])


PREPARE_INSTITUTION_INTERVIEW_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": non_blank_string_schema("면접 준비 대상 기관명입니다."),
        "target_role": non_blank_string_schema(
            "지원자가 목표로 하는 원문 직무 또는 직무군입니다. Job-ALIO 검색용 NCS 코드와 구분합니다."
        ),
        "job_family": non_blank_string_schema(
            "target_role의 호환 별칭 또는 resolver가 선택한 NCS명입니다."
        ),
        "original_job_family": non_blank_string_schema(
            "resolver 호출 전 사용자가 입력한 원문 직무군입니다."
        ),
        "original_target_role": non_blank_string_schema(
            "resolver 호출 전 사용자가 입력한 원문 목표 직무명입니다."
        ),
        "ncs_code": non_blank_string_schema(
            "resolve_ncs_code가 선택한 Job-ALIO NCS 코드입니다. 면접 카드의 검색 필터로 사용하지 않고 호출 맥락에 보존합니다."
        ),
        "year": {
            "type": "integer",
            "description": "분석 기준 연도입니다.",
        },
        "focus_areas": {
            "type": "array",
            "items": {"type": "string"},
            "default": ["지원동기", "기관이해", "개선과제", "입사후포부"],
            "description": "생성할 면접 카드 유형입니다.",
        },
        "alio_id": {
            "type": "string",
            "description": "ALIO 기관 코드(apbaId)입니다. 예: C1304",
        },
        "apba_id": {
            "type": "string",
            "description": "ALIO 기관 코드(apbaId)의 별칭입니다.",
        },
        "fetch_live_alio": {
            "type": "boolean",
            "default": True,
            "description": "evidence/signals가 없을 때 ALIO 공시를 실시간 조회할지 여부입니다.",
        },
        "evidence": {
            "type": "array",
            "items": {"type": "object"},
            "default": [],
            "description": "주요사업, 연구/정책 자료, 국회 지적사항 등 기관 분석 근거 후보입니다.",
        },
        "signals": {
            "type": "array",
            "items": {"type": "object"},
            "default": [],
            "description": "근거가 연결된 사전 추출 기관 signal 후보입니다.",
        },
    },
    "required": ["institution_name"],
    "anyOf": [
        {"required": ["target_role"]},
        {"required": ["job_family"]},
    ],
    "additionalProperties": False,
}

_INTERVIEW_ARGUMENTS = set(PREPARE_INSTITUTION_INTERVIEW_INPUT_SCHEMA["properties"])

def create_analyze_institution_strategy_tool() -> ToolDefinition:
    """Create the institution business-direction analysis tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _STRATEGY_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported analyze_institution_strategy arguments: " + ", ".join(unknown))

        institution_name = _required_text(arguments.get("institution_name"), "institution_name")
        year = _to_int(arguments.get("year"), field="year")
        job_family = _to_text(arguments.get("job_family"))
        original_job_family = _to_text(arguments.get("original_job_family")) or job_family
        target_role = _to_text(arguments.get("target_role"))
        original_target_role = _to_text(arguments.get("original_target_role")) or target_role
        ncs_code = _to_text(arguments.get("ncs_code"))
        alio_id = _to_text(arguments.get("alio_id") or arguments.get("apba_id"))
        evidence = _model_list(arguments.get("evidence"), InstitutionEvidence, field="evidence")
        signals = _model_list(arguments.get("signals"), InstitutionSignalCandidate, field="signals")
        alio_context = _live_alio_context(
            institution_name=institution_name,
            alio_id=alio_id,
            evidence=evidence,
            signals=signals,
            fetch_live=_to_bool(arguments.get("fetch_live_alio"), default=True),
            year=year,
        )
        evidence = [*evidence, *alio_context.evidence]
        signals = [*signals, *alio_context.signals]
        resolved_alio_id = alio_id or alio_context.institution_id
        analysis_input = prepare_institution_analysis_input(
            institution_name=institution_name,
            alio_id=resolved_alio_id,
            identity_candidates=alio_context.identity_candidates,
            evidence=evidence,
            signals=signals,
        )
        report = generate_institution_strategy_report(
            analysis_input,
            year=year,
            job_family=job_family,
        )
        return {
            "source": "institution_analysis",
            "query": {
                "institution_name": institution_name,
                "year": year,
                "job_family": job_family,
                "original_job_family": original_job_family,
                "target_role": target_role,
                "original_target_role": original_target_role,
                "ncs_code": ncs_code,
                "alio_id": resolved_alio_id,
            },
            **report.model_dump(mode="json"),
            "warnings": alio_context.warnings,
        }

    return ToolDefinition(
        name="analyze_institution_strategy",
        description=(
            "kr-gov-job-mcp 서비스에서 명시적인 근거를 바탕으로 기관의 사업 방향 signal과 "
            "직무 연결 포인트를 요약하고, 근거가 부족한 내용은 검증 필요 사항으로 남깁니다. Job-ALIO 공고 "
            "검색용 NCS 코드는 resolve_ncs_code 결과를 search_public_jobs.ncs_code로 전달합니다."
        ),
        input_schema=ANALYZE_INSTITUTION_STRATEGY_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Analyze Institution Strategy", open_world=True),
        handler=handler,
    )


def create_analyze_institution_weakness_tool() -> ToolDefinition:
    """Create the institution improvement analysis tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _WEAKNESS_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported analyze_institution_weakness arguments: " + ", ".join(unknown))

        institution_name = _required_text(arguments.get("institution_name"), "institution_name")
        year = _to_int(arguments.get("year"), field="year")
        alio_id = _to_text(arguments.get("alio_id") or arguments.get("apba_id"))
        evidence = _model_list(arguments.get("evidence"), InstitutionEvidence, field="evidence")
        signals = _model_list(arguments.get("signals"), InstitutionSignalCandidate, field="signals")
        alio_context = _live_alio_context(
            institution_name=institution_name,
            alio_id=alio_id,
            evidence=evidence,
            signals=signals,
            fetch_live=_to_bool(arguments.get("fetch_live_alio"), default=True),
            year=year,
        )
        evidence = [*evidence, *alio_context.evidence]
        signals = [*signals, *alio_context.signals]
        resolved_alio_id = alio_id or alio_context.institution_id
        analysis_input = prepare_institution_analysis_input(
            institution_name=institution_name,
            alio_id=resolved_alio_id,
            identity_candidates=alio_context.identity_candidates,
            evidence=evidence,
            signals=signals,
        )
        report = generate_institution_weakness_report(analysis_input, year=year)
        return {
            "source": "institution_analysis",
            "query": {
                "institution_name": institution_name,
                "year": year,
                "alio_id": resolved_alio_id,
            },
            **report.model_dump(mode="json"),
            "warnings": alio_context.warnings,
        }

    return ToolDefinition(
        name="analyze_institution_weakness",
        description=(
            "kr-gov-job-mcp 서비스에서 명시적인 근거를 바탕으로 기관의 개선 과제 signal을 요약하고, "
            "단정적 표현을 피하면서 근거가 부족한 내용은 검증 필요 사항으로 남깁니다."
        ),
        input_schema=ANALYZE_INSTITUTION_WEAKNESS_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Analyze Institution Weakness", open_world=True),
        handler=handler,
    )


def create_prepare_institution_interview_tool() -> ToolDefinition:
    """Create the integrated institution interview preparation tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _INTERVIEW_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported prepare_institution_interview arguments: " + ", ".join(unknown))

        institution_name = _required_text(arguments.get("institution_name"), "institution_name")
        target_role = _required_text(
            arguments.get("target_role") or arguments.get("job_family"),
            "target_role",
        )
        original_target_role = _to_text(arguments.get("original_target_role")) or target_role
        job_family = _to_text(arguments.get("job_family"))
        original_job_family = _to_text(arguments.get("original_job_family")) or job_family
        ncs_code = _to_text(arguments.get("ncs_code"))
        year = _to_int(arguments.get("year"), field="year")
        focus_areas = _text_list(arguments.get("focus_areas"), field="focus_areas")
        alio_id = _to_text(arguments.get("alio_id") or arguments.get("apba_id"))
        evidence = _model_list(arguments.get("evidence"), InstitutionEvidence, field="evidence")
        signals = _model_list(arguments.get("signals"), InstitutionSignalCandidate, field="signals")
        alio_context = _live_alio_context(
            institution_name=institution_name,
            alio_id=alio_id,
            evidence=evidence,
            signals=signals,
            fetch_live=_to_bool(arguments.get("fetch_live_alio"), default=True),
            year=year,
        )
        evidence = [*evidence, *alio_context.evidence]
        signals = [*signals, *alio_context.signals]
        resolved_alio_id = alio_id or alio_context.institution_id
        analysis_input = prepare_institution_analysis_input(
            institution_name=institution_name,
            alio_id=resolved_alio_id,
            identity_candidates=alio_context.identity_candidates,
            evidence=evidence,
            signals=signals,
        )
        report = generate_institution_interview_report(
            analysis_input,
            year=year,
            target_role=original_target_role,
            focus_areas=focus_areas or None,
        )
        return {
            "source": "institution_interview",
            "query": {
                "institution_name": institution_name,
                "year": year,
                "target_role": target_role,
                "job_family": job_family,
                "original_job_family": original_job_family,
                "original_target_role": original_target_role,
                "ncs_code": ncs_code,
                "focus_areas": focus_areas or None,
                "alio_id": resolved_alio_id,
            },
            **report.model_dump(mode="json"),
            "warnings": alio_context.warnings,
        }

    return ToolDefinition(
        name="prepare_institution_interview",
        description=(
            "kr-gov-job-mcp 서비스에서 기관명과 목표 직무를 받아 주요사업, 연구/정책 자료, "
            "국회 지적사항 근거를 면접 질문 카드로 변환합니다. 원문 직무명은 유지하며, 공고 검색이 필요하면 "
            "resolve_ncs_code 결과의 ncs_code를 search_public_jobs에 사용합니다."
        ),
        input_schema=PREPARE_INSTITUTION_INTERVIEW_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Prepare Institution Interview", open_world=True),
        handler=handler,
    )


def _model_list(value: Any, model_type: type, *, field: str) -> list[Any]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    return [model_type.model_validate(item) for item in value]


def _text_list(value: Any, *, field: str) -> list[str]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    values: list[str] = []
    for item in value:
        text = _to_text(item)
        if text:
            values.append(text)
    return values


def _live_alio_context(
    *,
    institution_name: str,
    alio_id: str | None,
    evidence: list[InstitutionEvidence],
    signals: list[InstitutionSignalCandidate],
    fetch_live: bool,
    year: int | None,
) -> AlioInstitutionContext:
    if not fetch_live or evidence or signals:
        return AlioInstitutionContext()
    return fetch_alio_institution_context_sync(
        institution_name=institution_name,
        alio_id=alio_id,
        year=year,
    )


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


def _to_int(value: Any, *, field: str) -> int | None:
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
    if text in {"1", "true", "t", "yes", "y"}:
        return True
    if text in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"expected boolean value: {value}")
