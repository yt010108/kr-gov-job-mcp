"""Evidence-backed NCS competency mapping tool."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from typing import Any

from kr_gov_job_mcp.analysis import prepare_ncs_mapping_input
from kr_gov_job_mcp.clients.attachment_text_client import (
    AttachmentTextClient,
    AttachmentTextResult,
)
from kr_gov_job_mcp.clients.job_alio_web_client import JobAlioWebClient
from kr_gov_job_mcp.schemas.job import JobAlioDetail
from kr_gov_job_mcp.schemas.ncs import (
    AttachmentExtractionStatus,
    KsaCandidate,
    NcsAttachmentCandidate,
    NcsEvidenceReference,
    NcsMappingReport,
    NcsMappingInput,
    NcsVerificationNote,
)
from kr_gov_job_mcp.tools.registry import (
    ToolDefinition,
    non_blank_string_schema,
    read_only_tool_annotations,
)


FetchJobDetailRunner = Callable[[str], JobAlioDetail]
ExtractAttachmentRunner = Callable[[str, str | None], AttachmentTextResult]

MAP_NCS_COMPETENCIES_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_id": non_blank_string_schema("잡알리오 채용공고 ID입니다."),
        "source_job_id": non_blank_string_schema("search_public_jobs의 source_job_id 별칭입니다."),
        "recruitment_notice_sn": non_blank_string_schema(
            "잡알리오 채용공고 일련번호(recrutPblntSn)입니다."
        ),
        "duty_description_text": {
            "type": "string",
            "description": "사용자가 이미 추출한 직무기술서 본문입니다. 첨부 다운로드보다 우선합니다.",
        },
        "attachment_url": {
            "type": "string",
            "format": "uri",
            "description": "여러 후보 중 사용자가 명시적으로 선택한 직무기술서 URL입니다.",
        },
        "include_attachment_text": {
            "type": "boolean",
            "default": True,
            "description": "본문이 없을 때 선택 가능한 PDF 첨부를 다운로드해 분석할지 여부입니다.",
        },
    },
    "anyOf": [
        {"required": ["job_id"]},
        {"required": ["source_job_id"]},
        {"required": ["recruitment_notice_sn"]},
    ],
    "additionalProperties": False,
}

_SUPPORTED_ARGUMENTS = set(MAP_NCS_COMPETENCIES_INPUT_SCHEMA["properties"])


def create_map_ncs_competencies_tool(
    fetch_job_detail: FetchJobDetailRunner | None = None,
    extract_attachment: ExtractAttachmentRunner | None = None,
) -> ToolDefinition:
    def handler(arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - _SUPPORTED_ARGUMENTS)
        if unknown:
            raise ValueError("unsupported map_ncs_competencies arguments: " + ", ".join(unknown))
        job_id = _normalize_job_id(arguments)
        supplied_text = _to_text(arguments.get("duty_description_text"))
        explicit_url = _to_text(arguments.get("attachment_url"))
        include_attachment_text = _to_bool(arguments.get("include_attachment_text"), default=True)

        detail = (
            fetch_job_detail(job_id)
            if fetch_job_detail is not None
            else _run_async(_fetch_job_detail(job_id))
        )
        initial = prepare_ncs_mapping_input(detail)
        candidates = initial.duty_description_attachments
        selected = _select_candidate(candidates, explicit_url=explicit_url)
        explicit_url_unmatched = explicit_url is not None and selected is None
        if supplied_text and explicit_url_unmatched:
            selected = NcsAttachmentCandidate(url=explicit_url)
            candidates.append(selected)
        warnings: list[str] = []
        extra_notes: list[NcsVerificationNote] = []
        source: NcsEvidenceReference | None = None
        text = supplied_text

        if supplied_text:
            source = NcsEvidenceReference(
                title=selected.name if selected and selected.name else "사용자 제공 직무기술서 본문",
                source_type="duty_description_text",
                url=explicit_url or (selected.url if selected else None),
            )
            if selected:
                _mark_selected(selected, "사용자가 제공한 본문의 출처 후보입니다.", "provided_text")
        elif explicit_url_unmatched:
            candidates.append(NcsAttachmentCandidate(url=explicit_url))
            extra_notes.append(
                NcsVerificationNote(
                    field="attachment_url",
                    reason="attachment_url이 Job-ALIO 직무기술서 후보와 일치하지 않습니다.",
                    suggested_check="attachment_candidates에서 반환된 URL 중 하나를 지정합니다.",
                )
            )
        elif not include_attachment_text:
            extra_notes.append(
                NcsVerificationNote(
                    field="attachment_candidates",
                    reason="include_attachment_text=false로 첨부 본문 추출을 건너뛰었습니다.",
                    suggested_check="후보를 확인하거나 직무기술서 본문을 직접 전달합니다.",
                )
            )
        elif selected and selected.url:
            reason = (
                "사용자가 attachment_url로 선택했습니다."
                if explicit_url
                else "직무기술서 후보가 하나여서 자동 선택했습니다."
            )
            result = (
                extract_attachment(selected.url, selected.name)
                if extract_attachment is not None
                else _run_async(_extract_attachment(selected.url, selected.name))
            )
            _mark_selected(selected, reason, result.status)
            text = result.text
            source = NcsEvidenceReference(
                title=selected.name or "직무기술서 첨부",
                source_type="duty_description_text",
                url=selected.url,
            )
            if result.reason:
                warnings.append(result.reason)
                extra_notes.append(
                    NcsVerificationNote(
                        field="attachment_text",
                        reason=result.reason,
                        suggested_check=_suggested_check(result.status),
                    )
                )
            elif result.status == "extracted":
                extra_notes.append(
                    NcsVerificationNote(
                        field="attachment_text",
                        reason="PDF 텍스트 추출은 표와 이미지의 시각적 구조를 완전히 보존하지 않을 수 있습니다.",
                        suggested_check="중요한 역량 항목은 원문 PDF 표와 함께 확인합니다.",
                    )
                )
        elif selected and not selected.url:
            _mark_selected(selected, "직무기술서 후보가 하나지만 다운로드 URL이 없습니다.")
            extra_notes.append(
                NcsVerificationNote(
                    field="attachment_url",
                    reason="선택한 직무기술서 후보에 다운로드 URL이 없습니다.",
                    suggested_check="잡알리오 원문 첨부 링크를 확인합니다.",
                )
            )
        elif len(candidates) > 1 and not explicit_url:
            extra_notes.append(
                NcsVerificationNote(
                    field="attachment_candidates",
                    reason="직무기술서 후보가 여러 개여서 임의로 선택하지 않았습니다.",
                    suggested_check="attachment_url로 분석할 후보를 지정합니다.",
                )
            )
        prepared = prepare_ncs_mapping_input(
            detail,
            duty_description_text=text,
            duty_description_source=source,
        )
        _copy_candidate_state(candidates, prepared.duty_description_attachments)
        known_urls = {item.url for item in prepared.duty_description_attachments}
        prepared.duty_description_attachments.extend(
            item for item in candidates if item.url not in known_urls
        )
        report = _build_report(prepared, warnings=warnings, extra_notes=extra_notes)
        return {"source": "job_alio", **report.model_dump(mode="json")}

    return ToolDefinition(
        name="map_ncs_competencies",
        description=(
            "kr-gov-job-mcp 서비스에서 잡알리오 상세 공고와 직무기술서 본문 또는 PDF 첨부의 "
            "명시된 NCS 코드, "
            "직업기초능력, 직무수행능력, 지식, 기술, 태도를 근거와 함께 정리합니다."
        ),
        input_schema=MAP_NCS_COMPETENCIES_INPUT_SCHEMA,
        annotations=read_only_tool_annotations("Map NCS Competencies", open_world=True),
        handler=handler,
    )


async def _fetch_job_detail(job_id: str) -> JobAlioDetail:
    async with JobAlioWebClient() as client:
        return await client.fetch_job_detail(job_id)


async def _extract_attachment(url: str, file_name: str | None) -> AttachmentTextResult:
    async with AttachmentTextClient() as client:
        return await client.extract(url, file_name=file_name)


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    if hasattr(coro, "close"):
        coro.close()
    raise ValueError("map_ncs_competencies cannot run inside an active event loop")


def _normalize_job_id(arguments: Mapping[str, Any]) -> str:
    values = {
        key: _to_text(arguments.get(key))
        for key in ("job_id", "source_job_id", "recruitment_notice_sn")
    }
    provided = {key: value for key, value in values.items() if value is not None}
    if not provided:
        raise ValueError("map_ncs_competencies requires job_id")
    if len(set(provided.values())) > 1:
        raise ValueError(
            "conflicting map_ncs_competencies ids: "
            + ", ".join(f"{key}={value}" for key, value in provided.items())
        )
    return next(iter(provided.values()))


def _select_candidate(
    candidates: list[NcsAttachmentCandidate],
    *,
    explicit_url: str | None,
) -> NcsAttachmentCandidate | None:
    if explicit_url:
        return next((item for item in candidates if item.url == explicit_url), None)
    return candidates[0] if len(candidates) == 1 else None


def _mark_selected(
    candidate: NcsAttachmentCandidate,
    reason: str,
    status: AttachmentExtractionStatus = "not_selected",
) -> None:
    candidate.selected = True
    candidate.selection_reason = reason
    candidate.extraction_status = status


def _copy_candidate_state(
    source: list[NcsAttachmentCandidate],
    target: list[NcsAttachmentCandidate],
) -> None:
    states = {_candidate_key(item): item for item in source}
    for item in target:
        state = states.get(_candidate_key(item))
        if state:
            item.selected = state.selected
            item.selection_reason = state.selection_reason
            item.extraction_status = state.extraction_status


def _candidate_key(candidate: NcsAttachmentCandidate) -> tuple[str | None, str | None, str | None]:
    return candidate.url, candidate.name, candidate.file_type


def _build_report(
    prepared: NcsMappingInput,
    *,
    warnings: list[str],
    extra_notes: list[NcsVerificationNote],
) -> NcsMappingReport:
    grouped: dict[str, list[KsaCandidate]] = {
        "basic_competency": [],
        "duty_competency": [],
        "knowledge": [],
        "skill": [],
        "attitude": [],
    }
    for candidate in prepared.ksa_candidates:
        grouped[candidate.category].append(candidate)
    return NcsMappingReport(
        job_id=prepared.job_id,
        ncs_codes=prepared.ncs_codes,
        basic_competencies=grouped["basic_competency"],
        duty_competencies=grouped["duty_competency"],
        knowledge=grouped["knowledge"],
        skills=grouped["skill"],
        attitudes=grouped["attitude"],
        attachment_candidates=prepared.duty_description_attachments,
        evidence=_collect_evidence(prepared),
        verification_notes=[*prepared.verification_notes, *extra_notes],
        warnings=warnings,
    )


def _collect_evidence(prepared: NcsMappingInput) -> list[NcsEvidenceReference]:
    references = [*prepared.source_fields]
    references.extend(
        evidence for mapping in prepared.ncs_codes for evidence in mapping.evidence
    )
    references.extend(
        evidence
        for attachment in prepared.duty_description_attachments
        for evidence in attachment.evidence
    )
    references.extend(
        evidence for candidate in prepared.ksa_candidates for evidence in candidate.evidence
    )
    deduped: dict[tuple[str, str, str | None, str | None], NcsEvidenceReference] = {}
    for reference in references:
        key = (reference.title, reference.source_type, reference.url, reference.excerpt)
        deduped.setdefault(key, reference)
    return list(deduped.values())


def _suggested_check(status: AttachmentExtractionStatus) -> str:
    if status == "ocr_required":
        return "OCR을 수행하거나 원문 PDF를 직접 확인합니다."
    if status == "unsupported_format":
        return "HWP/HWPX 원문을 수동으로 확인하거나 텍스트를 직접 전달합니다."
    return "첨부 URL과 원본 파일 상태를 확인합니다."


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
