"""MCP-style tools for institution analysis reports."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.analysis import (
    generate_institution_strategy_report,
    generate_institution_weakness_report,
    prepare_institution_analysis_input,
)
from kr_gov_job_mcp.clients.alio_disclosure_client import (
    AlioDisclosureClient,
    AlioDisclosureClientError,
)
from kr_gov_job_mcp.schemas.alio import AlioInstitution
from kr_gov_job_mcp.schemas.institution import (
    InstitutionEvidence,
    InstitutionIdentityCandidate,
    InstitutionSignalCandidate,
)
from kr_gov_job_mcp.tools.registry import ToolDefinition


CollectInstitutionContextRunner = Callable[..., dict[str, Any]]

COLLECT_INSTITUTION_CONTEXT_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": {
            "type": "string",
            "description": "근거를 수집할 기관명입니다.",
        },
        "sources": {
            "type": "array",
            "items": {"type": "string", "enum": ["alio", "homepage"]},
            "default": ["alio"],
            "description": "수집할 공개 출처입니다. 현재는 ALIO 기관 정보와 홈페이지 URL 근거를 지원합니다.",
        },
    },
    "additionalProperties": False,
}

_CONTEXT_ARGUMENTS = set(COLLECT_INSTITUTION_CONTEXT_INPUT_SCHEMA["properties"])
_SUPPORTED_CONTEXT_SOURCES = {"alio", "homepage"}

ANALYZE_INSTITUTION_STRATEGY_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": {
            "type": "string",
            "description": "분석할 기관명입니다.",
        },
        "year": {
            "type": "integer",
            "description": "분석 기준 연도입니다.",
        },
        "job_family": {
            "type": "string",
            "description": "목표 직무군입니다. 예: 정보보호, 전산",
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
    "additionalProperties": False,
}


_STRATEGY_ARGUMENTS = set(ANALYZE_INSTITUTION_STRATEGY_INPUT_SCHEMA["properties"])

ANALYZE_INSTITUTION_WEAKNESS_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": {
            "type": "string",
            "description": "분석할 기관명입니다.",
        },
        "year": {
            "type": "integer",
            "description": "분석 기준 연도입니다.",
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
    "additionalProperties": False,
}

_WEAKNESS_ARGUMENTS = set(ANALYZE_INSTITUTION_WEAKNESS_INPUT_SCHEMA["properties"])


def create_collect_institution_context_tool(
    collect_context: CollectInstitutionContextRunner | None = None,
) -> ToolDefinition:
    """Create a lightweight institution evidence collection tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _CONTEXT_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported collect_institution_context arguments: " + ", ".join(unknown))

        institution_name = _required_text(arguments.get("institution_name"), "institution_name")
        sources = _source_list(arguments.get("sources"))
        if collect_context is not None:
            return collect_context(institution_name=institution_name, sources=sources)
        return _run_async(
            "collect_institution_context",
            lambda: _collect_institution_context_from_alio(
                institution_name=institution_name,
                sources=sources,
            ),
        )

    return ToolDefinition(
        name="collect_institution_context",
        description=(
            "기관명으로 ALIO 기관 정보와 홈페이지 URL 근거를 수집해 기관 분석 입력으로 사용할 "
            "identity, evidence, signal 후보를 반환합니다."
        ),
        input_schema=COLLECT_INSTITUTION_CONTEXT_INPUT_SCHEMA,
        handler=handler,
    )


def create_analyze_institution_strategy_tool() -> ToolDefinition:
    """Create the institution business-direction analysis tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _STRATEGY_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported analyze_institution_strategy arguments: " + ", ".join(unknown))

        institution_name = _required_text(arguments.get("institution_name"), "institution_name")
        year = _to_int(arguments.get("year"), field="year")
        job_family = _to_text(arguments.get("job_family"))
        evidence = _model_list(arguments.get("evidence"), InstitutionEvidence, field="evidence")
        signals = _model_list(arguments.get("signals"), InstitutionSignalCandidate, field="signals")
        analysis_input = prepare_institution_analysis_input(
            institution_name=institution_name,
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
            },
            **report.model_dump(mode="json"),
            "warnings": [],
        }

    return ToolDefinition(
        name="analyze_institution_strategy",
        description=(
            "명시적인 근거를 바탕으로 기관의 사업 방향 signal과 직무 연결 포인트를 요약하고, "
            "근거가 부족한 내용은 검증 필요 사항으로 남깁니다."
        ),
        input_schema=ANALYZE_INSTITUTION_STRATEGY_INPUT_SCHEMA,
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
        evidence = _model_list(arguments.get("evidence"), InstitutionEvidence, field="evidence")
        signals = _model_list(arguments.get("signals"), InstitutionSignalCandidate, field="signals")
        analysis_input = prepare_institution_analysis_input(
            institution_name=institution_name,
            evidence=evidence,
            signals=signals,
        )
        report = generate_institution_weakness_report(analysis_input, year=year)
        return {
            "source": "institution_analysis",
            "query": {
                "institution_name": institution_name,
                "year": year,
            },
            **report.model_dump(mode="json"),
            "warnings": [],
        }

    return ToolDefinition(
        name="analyze_institution_weakness",
        description=(
            "명시적인 근거를 바탕으로 기관의 개선 과제 signal을 요약하고, 단정적 표현을 피하면서 "
            "근거가 부족한 내용은 검증 필요 사항으로 남깁니다."
        ),
        input_schema=ANALYZE_INSTITUTION_WEAKNESS_INPUT_SCHEMA,
        handler=handler,
    )


async def _collect_institution_context_from_alio(
    *,
    institution_name: str,
    sources: list[str],
) -> dict[str, Any]:
    warnings: list[str] = []
    try:
        async with AlioDisclosureClient() as client:
            search_result = await client.search_institutions(keyword=institution_name)
            selected = search_result.institutions[0] if search_result.institutions else None
            detail = (
                await client.fetch_institution_detail(selected.id)
                if selected is not None and selected.id
                else None
            )
    except AlioDisclosureClientError as exc:
        warnings.append(f"ALIO institution lookup failed: {exc}")
        selected = None
        detail = None

    institution = detail or selected
    identity_candidates = _identity_candidates(institution)
    evidence = _context_evidence(institution, sources)
    signals = _context_signals(evidence)
    analysis_input = prepare_institution_analysis_input(
        institution_name=institution.name if institution and institution.name else institution_name,
        alio_id=institution.id if institution and institution.id else None,
        identity_candidates=identity_candidates,
        evidence=evidence,
        signals=signals,
    )
    return {
        "source": "institution_context",
        "query": {
            "institution_name": institution_name,
            "sources": sources,
        },
        **analysis_input.model_dump(mode="json"),
        "warnings": warnings,
    }


def _identity_candidates(institution: AlioInstitution | None) -> list[InstitutionIdentityCandidate]:
    if institution is None:
        return []
    return [
        InstitutionIdentityCandidate(
            name=institution.name or institution.id,
            source_type="alio_disclosure",
            source_id=institution.id or None,
            code_type="apbaId",
            source_url=institution.source_url,
            confidence="high",
        )
    ]


def _context_evidence(
    institution: AlioInstitution | None,
    sources: list[str],
) -> list[InstitutionEvidence]:
    if institution is None:
        return []

    evidence: list[InstitutionEvidence] = []
    if "alio" in sources and institution.main_business:
        evidence.append(
            InstitutionEvidence(
                title="ALIO 기관 주요사업",
                source_type="alio_disclosure",
                url=institution.source_url,
                source_id=institution.id or None,
                excerpt=institution.main_business[:1000],
                fields={
                    "institution_type": institution.type_name,
                    "ministry_name": institution.ministry_name,
                    "homepage_url": institution.homepage_url,
                },
            )
        )
    if "homepage" in sources and institution.homepage_url:
        evidence.append(
            InstitutionEvidence(
                title="ALIO 기관정보 홈페이지 URL",
                source_type="institution_homepage",
                url=institution.homepage_url,
                source_id=institution.id or None,
                excerpt="ALIO 기관정보에 등록된 기관 홈페이지 URL입니다.",
            )
        )
    return evidence


def _context_signals(evidence: list[InstitutionEvidence]) -> list[InstitutionSignalCandidate]:
    return [
        InstitutionSignalCandidate(
            category="business_direction",
            title=evidence_item.title,
            summary=evidence_item.excerpt,
            evidence=[evidence_item],
            needs_verification=False,
        )
        for evidence_item in evidence
        if evidence_item.source_type == "alio_disclosure" and evidence_item.excerpt
    ]


def _model_list(value: Any, model_type: type, *, field: str) -> list[Any]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    return [model_type.model_validate(item) for item in value]


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


def _source_list(value: Any) -> list[str]:
    if value is None or value == "":
        return ["alio"]
    if not isinstance(value, list):
        raise ValueError(f"expected list value for sources: {value}")
    sources = [_required_text(item, "sources[]") for item in value]
    unsupported = sorted(set(sources) - _SUPPORTED_CONTEXT_SOURCES)
    if unsupported:
        raise ValueError("unsupported context sources: " + ", ".join(unsupported))
    return sources or ["alio"]


def _run_async(tool_name: str, coro_factory: Callable[[], Any]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())
    raise ValueError(f"{tool_name} cannot run inside an active event loop")
