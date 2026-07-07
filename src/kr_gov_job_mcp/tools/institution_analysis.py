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
from kr_gov_job_mcp.schemas.institution import (
    InstitutionAnalysisInput,
    InstitutionEvidence,
    InstitutionIdentityCandidate,
    InstitutionSignalCandidate,
    InstitutionVerificationNote,
)
from kr_gov_job_mcp.tools.registry import ToolDefinition


CollectInstitutionContextRunner = Callable[..., InstitutionAnalysisInput | Mapping[str, Any]]

COLLECT_INSTITUTION_CONTEXT_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "institution_name": {
            "type": "string",
            "description": "근거를 수집할 기관명입니다.",
        },
        "year": {
            "type": "integer",
            "description": "근거 선별 기준 연도입니다.",
        },
        "sources": {
            "type": "array",
            "items": {"type": "string", "enum": ["alio", "homepage", "cleaneye"]},
            "default": ["alio", "homepage"],
            "description": "수집할 공개 소스입니다. v1은 ALIO와 ALIO에서 확인한 홈페이지 URL을 지원합니다.",
        },
        "institution_code": {
            "type": "string",
            "description": "ALIO 기관 코드(apbaId)입니다. 기관명을 보완하는 선택 입력입니다.",
        },
        "alio_id": {
            "type": "string",
            "description": "institution_code와 같은 ALIO 기관 코드 별칭입니다.",
        },
    },
    "additionalProperties": False,
}

_CONTEXT_ARGUMENTS = set(COLLECT_INSTITUTION_CONTEXT_INPUT_SCHEMA["properties"])
_CONTEXT_SOURCES = {"alio", "homepage", "cleaneye"}
_ALIO_CONTEXT_ITEM_NOS = ("40", "47-1")

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
    """Create the institution evidence collection tool."""

    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _CONTEXT_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported collect_institution_context arguments: " + ", ".join(unknown))

        institution_name = _required_text(arguments.get("institution_name"), "institution_name")
        year = _to_int(arguments.get("year"), field="year")
        sources = _source_list(arguments.get("sources"))
        institution_code = _context_institution_code(arguments)

        analysis_input = (
            collect_context(
                institution_name=institution_name,
                year=year,
                sources=sources,
                institution_code=institution_code,
            )
            if collect_context is not None
            else _run_async(
                "collect_institution_context",
                lambda: _collect_institution_context_from_public_sources(
                    institution_name=institution_name,
                    year=year,
                    sources=sources,
                    institution_code=institution_code,
                ),
            )
        )

        if isinstance(analysis_input, Mapping):
            return dict(analysis_input)

        return _serialize_context_result(
            analysis_input,
            query={
                "institution_name": institution_name,
                "year": year,
                "sources": sources,
                "institution_code": institution_code,
            },
        )

    return ToolDefinition(
        name="collect_institution_context",
        description=(
            "기관명으로 ALIO 기관 식별자와 기관 분석용 근거 후보를 수집하고, "
            "분석 도구에 바로 넘길 수 있는 evidence와 signal 후보를 반환합니다."
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


async def _collect_institution_context_from_public_sources(
    *,
    institution_name: str,
    year: int | None,
    sources: list[str],
    institution_code: str | None,
) -> InstitutionAnalysisInput:
    verification_notes: list[InstitutionVerificationNote] = []
    if "cleaneye" in sources:
        verification_notes.append(
            InstitutionVerificationNote(
                field="sources.cleaneye",
                reason="v1 collect_institution_context는 Cleaneye 자동 수집을 아직 지원하지 않습니다.",
                suggested_check="지방공기업/출자출연기관이면 Cleaneye entId 또는 insttCode를 별도 확인합니다.",
            )
        )

    needs_alio = bool({"alio", "homepage"} & set(sources))
    if not needs_alio:
        analysis_input = prepare_institution_analysis_input(institution_name=institution_name)
        analysis_input.verification_notes.extend(verification_notes)
        return analysis_input

    async with AlioDisclosureClient() as client:
        analysis_input = await _collect_alio_institution_context(
            client=client,
            institution_name=institution_name,
            year=year,
            sources=sources,
            institution_code=institution_code,
        )
    analysis_input.verification_notes.extend(verification_notes)
    return analysis_input


async def _collect_alio_institution_context(
    *,
    client: AlioDisclosureClient,
    institution_name: str,
    year: int | None,
    sources: list[str],
    institution_code: str | None,
) -> InstitutionAnalysisInput:
    identity_candidates: list[InstitutionIdentityCandidate] = []
    evidence: list[InstitutionEvidence] = []
    signals: list[InstitutionSignalCandidate] = []
    verification_notes: list[InstitutionVerificationNote] = []

    try:
        search_result = await client.search_institutions(
            keyword=institution_name,
            institution_code=institution_code,
            page=1,
        )
    except AlioDisclosureClientError as exc:
        analysis_input = prepare_institution_analysis_input(institution_name=institution_name)
        analysis_input.verification_notes.append(
            InstitutionVerificationNote(
                field="sources.alio",
                reason=f"ALIO 기관 검색에 실패했습니다: {exc}",
                suggested_check="기관명, ALIO apbaId, 네트워크 연결 상태를 확인합니다.",
            )
        )
        return analysis_input

    selected = _select_alio_institution(
        search_result.institutions,
        institution_name=institution_name,
        institution_code=institution_code,
    )
    for candidate in search_result.institutions[:5]:
        identity_candidates.append(
            InstitutionIdentityCandidate(
                name=candidate.name or institution_name,
                source_type="alio_disclosure",
                source_id=candidate.id or None,
                code_type="apbaId",
                source_url=candidate.source_url
                or (AlioDisclosureClient.institution_detail_url(candidate.id) if candidate.id else None),
                confidence="high" if selected and candidate.id == selected.id else "medium",
            )
        )

    if selected is None:
        analysis_input = prepare_institution_analysis_input(
            institution_name=institution_name,
            identity_candidates=identity_candidates,
        )
        analysis_input.verification_notes.append(
            InstitutionVerificationNote(
                field="identity_candidates",
                reason="ALIO 기관 검색 결과에서 사용할 수 있는 기관 후보를 찾지 못했습니다.",
                suggested_check="기관 공식명 또는 ALIO apbaId로 다시 조회합니다.",
            )
        )
        return analysis_input

    institution = selected
    try:
        institution = await client.fetch_institution_detail(selected.id)
    except AlioDisclosureClientError as exc:
        verification_notes.append(
            InstitutionVerificationNote(
                field="sources.alio.detail",
                reason=f"ALIO 기관 상세 조회에 실패해 검색 결과 후보만 사용했습니다: {exc}",
                suggested_check="ALIO 기관 상세 페이지에서 apbaId가 유효한지 확인합니다.",
            )
        )

    if "alio" in sources:
        main_evidence = _alio_institution_detail_evidence(institution)
        if main_evidence is not None:
            evidence.append(main_evidence)
            if main_evidence.excerpt:
                signals.append(
                    InstitutionSignalCandidate(
                        category="business_direction",
                        title="ALIO 기관 주요사업",
                        summary=main_evidence.excerpt,
                        evidence=[main_evidence],
                    )
                )

        institution_type = _to_text(
            institution.raw.get("apbaType") or selected.raw.get("apbaType")
        )
        item_evidence, item_signals, item_notes = await _collect_alio_item_context(
            client=client,
            institution_id=institution.id,
            institution_type=institution_type,
            year=year,
        )
        evidence.extend(item_evidence)
        signals.extend(item_signals)
        verification_notes.extend(item_notes)

    if "homepage" in sources:
        homepage_evidence = _homepage_evidence_from_alio(institution)
        if homepage_evidence is not None:
            evidence.append(homepage_evidence)
        else:
            verification_notes.append(
                InstitutionVerificationNote(
                    field="sources.homepage",
                    reason="ALIO 기관 상세에서 홈페이지 URL을 확인하지 못했습니다.",
                    suggested_check="기관 공식 홈페이지 URL을 수동으로 확인해 evidence에 연결합니다.",
                )
            )

    analysis_input = prepare_institution_analysis_input(
        institution_name=institution.name or institution_name,
        aliases=[institution_name],
        alio_id=institution.id,
        identity_candidates=identity_candidates,
        evidence=evidence,
        signals=signals,
    )
    analysis_input.verification_notes.extend(verification_notes)
    return analysis_input


async def _collect_alio_item_context(
    *,
    client: AlioDisclosureClient,
    institution_id: str,
    institution_type: str | None,
    year: int | None,
) -> tuple[
    list[InstitutionEvidence],
    list[InstitutionSignalCandidate],
    list[InstitutionVerificationNote],
]:
    evidence: list[InstitutionEvidence] = []
    signals: list[InstitutionSignalCandidate] = []
    verification_notes: list[InstitutionVerificationNote] = []

    for item_no in _ALIO_CONTEXT_ITEM_NOS:
        item = AlioDisclosureClient.TARGET_ITEM_REPORTS[item_no]
        try:
            reports = await client.list_item_reports(
                institution_code=institution_id,
                institution_type=institution_type,
                item=item,
            )
        except AlioDisclosureClientError as exc:
            verification_notes.append(
                InstitutionVerificationNote(
                    field=f"sources.alio.item.{item_no}",
                    reason=f"ALIO {item.name} 목록 조회에 실패했습니다: {exc}",
                    suggested_check="ALIO 공시 항목 페이지에서 해당 항목의 공개 여부를 확인합니다.",
                )
            )
            continue

        selected_reports = _select_reports_for_context(reports.reports, year=year)
        if not selected_reports:
            verification_notes.append(
                InstitutionVerificationNote(
                    field=f"sources.alio.item.{item_no}",
                    reason=f"ALIO {item.name} 목록에서 분석에 사용할 공시 행을 찾지 못했습니다.",
                    suggested_check="다른 기준 연도 또는 ALIO 원문 항목 페이지를 확인합니다.",
                )
            )
            continue
        if year is not None and not _has_report_for_year(reports.reports, year):
            verification_notes.append(
                InstitutionVerificationNote(
                    field=f"sources.alio.item.{item_no}.year",
                    reason=f"ALIO {item.name} 목록에서 {year}년 공시 행을 찾지 못해 조회된 최신 후보를 사용했습니다.",
                    suggested_check="기준 연도 공시가 필요한 경우 ALIO 원문 항목 페이지에서 연도별 공시 여부를 확인합니다.",
                )
            )

        for report in selected_reports:
            report_evidence = InstitutionEvidence(
                title=f"ALIO {item.name}",
                source_type="alio_disclosure",
                url=report.source_url
                or AlioDisclosureClient.item_organ_list_url(institution_id, item.report_form_root_no),
                source_id=_report_source_id(report),
                excerpt=report.title or item.name,
                fields={
                    "item_no": item.item_no,
                    "item_name": item.name,
                    "report_form_root_no": item.report_form_root_no,
                    "report_form_no": report.report_form_no,
                    "disclosed_date": report.disclosed_date,
                },
            )
            evidence.append(report_evidence)
            signals.append(_signal_from_alio_item(item_no, report_evidence))

    return evidence, signals, verification_notes


def _alio_institution_detail_evidence(
    institution: Any,
) -> InstitutionEvidence | None:
    fields = {
        key: value
        for key, value in {
            "institution_id": institution.id,
            "type_name": institution.type_name,
            "ministry_name": institution.ministry_name,
            "region": institution.region,
            "address": institution.address,
            "homepage_url": institution.homepage_url,
            "disclosure_start_date": institution.disclosure_start_date,
        }.items()
        if value is not None
    }
    if not fields and not institution.main_business:
        return None
    return InstitutionEvidence(
        title="ALIO 기관 일반현황",
        source_type="alio_disclosure",
        url=institution.source_url
        or (AlioDisclosureClient.institution_detail_url(institution.id) if institution.id else None),
        source_id=institution.id or None,
        excerpt=institution.main_business,
        fields=fields,
    )


def _homepage_evidence_from_alio(institution: Any) -> InstitutionEvidence | None:
    if not institution.homepage_url:
        return None
    return InstitutionEvidence(
        title="기관 홈페이지",
        source_type="institution_homepage",
        url=institution.homepage_url,
        source_id=institution.id or None,
        fields={
            "resolved_from": "ALIO 기관 상세",
            "institution_id": institution.id,
        },
    )


def _signal_from_alio_item(
    item_no: str,
    evidence: InstitutionEvidence,
) -> InstitutionSignalCandidate:
    if item_no == "47-1":
        return InstitutionSignalCandidate(
            category="improvement_task",
            title="ALIO 국회 지적사항",
            summary=evidence.excerpt,
            evidence=[evidence],
        )
    return InstitutionSignalCandidate(
        category="business_direction",
        title="ALIO 주요사업",
        summary=evidence.excerpt,
        evidence=[evidence],
    )


def _select_reports_for_context(
    reports: list[Any],
    *,
    year: int | None,
    limit: int = 2,
) -> list[Any]:
    if year is not None:
        matching = [
            report
            for report in reports
            if report.disclosed_date and report.disclosed_date.startswith(str(year))
        ]
        if matching:
            return matching[:limit]
    return reports[:limit]


def _has_report_for_year(reports: list[Any], year: int) -> bool:
    return any(
        report.disclosed_date and report.disclosed_date.startswith(str(year))
        for report in reports
    )


def _report_source_id(report: Any) -> str | None:
    disclosure_no = _to_text(report.disclosure_no)
    if disclosure_no and set(disclosure_no) != {"0"}:
        return disclosure_no
    return _to_text(report.submission_no) or disclosure_no


def _select_alio_institution(
    institutions: list[Any],
    *,
    institution_name: str,
    institution_code: str | None,
) -> Any | None:
    if not institutions:
        return None
    if institution_code:
        for institution in institutions:
            if institution.id == institution_code:
                return institution
    for institution in institutions:
        if institution.name == institution_name:
            return institution
    return institutions[0]


def _model_list(value: Any, model_type: type, *, field: str) -> list[Any]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected list value for {field}: {value}")
    return [model_type.model_validate(item) for item in value]


def _serialize_context_result(
    analysis_input: InstitutionAnalysisInput,
    *,
    query: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "source": "institution_context",
        "query": dict(query),
        **analysis_input.model_dump(mode="json"),
        "warnings": [],
    }


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
        return ["alio", "homepage"]
    if not isinstance(value, list):
        raise ValueError(f"expected list value for sources: {value}")
    sources: list[str] = []
    for item in value:
        source = _required_text(item, "sources")
        if source not in _CONTEXT_SOURCES:
            raise ValueError(f"unsupported institution context source: {source}")
        if source not in sources:
            sources.append(source)
    return sources or ["alio", "homepage"]


def _context_institution_code(arguments: Mapping[str, Any]) -> str | None:
    institution_code = _to_text(arguments.get("institution_code"))
    alio_id = _to_text(arguments.get("alio_id"))
    if institution_code and alio_id and institution_code != alio_id:
        raise ValueError(
            "institution_code and alio_id conflict: "
            f"institution_code={institution_code}, alio_id={alio_id}"
        )
    return institution_code or alio_id


def _run_async(tool_name: str, coro_factory: Callable[[], Any]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())
    raise ValueError(f"{tool_name} cannot run inside an active event loop")
