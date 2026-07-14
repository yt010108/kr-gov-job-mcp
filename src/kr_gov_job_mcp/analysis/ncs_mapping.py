"""Prepare evidence-backed inputs for NCS/KSA mapping."""

from __future__ import annotations

import re

from kr_gov_job_mcp.schemas.job import JobAlioAttachment, JobAlioDetail
from kr_gov_job_mcp.schemas.ncs import (
    KsaCandidate,
    KsaCategory,
    NcsAttachmentCandidate,
    NcsCodeMapping,
    NcsEvidenceReference,
    NcsMappingInput,
    NcsVerificationNote,
)


class NcsMappingPreparer:
    """Convert collected job detail fields into NCS mapping input candidates."""

    DUTY_ATTACHMENT_HINTS = ("직무기술서", "ncs", "직무 설명", "직무설명")
    SOURCE_TEXT_FIELDS = {
        "qualification": "지원자격",
        "preferred_conditions": "우대조건",
        "preference": "가점/우대사항",
        "disqualification_reason": "결격사유",
        "screening_procedure": "전형절차",
    }
    KSA_LABELS: dict[KsaCategory, tuple[str, ...]] = {
        "knowledge": ("필요지식", "지식", "knowledge"),
        "skill": ("필요기술", "기술", "skill"),
        "attitude": ("직무수행태도", "태도", "attitude"),
        "basic_competency": ("직업기초능력", "기초능력", "basic competency"),
        "duty_competency": ("직무수행능력", "직무능력", "duty competency"),
    }

    @classmethod
    def prepare(
        cls,
        detail: JobAlioDetail,
        *,
        duty_description_text: str | None = None,
        duty_description_source: NcsEvidenceReference | None = None,
    ) -> NcsMappingInput:
        verification_notes: list[NcsVerificationNote] = []
        ncs_codes = cls._ncs_codes(detail, verification_notes)
        duty_attachments = cls._duty_description_attachments(detail.attachments)
        source_fields = cls._source_fields(detail)
        ksa_candidates = cls._ksa_candidates(
            duty_description_text,
            source=duty_description_source,
        )

        if not duty_attachments:
            verification_notes.append(
                NcsVerificationNote(
                    field="duty_description_attachments",
                    reason="잡알리오 상세 첨부에서 직무기술서 후보를 찾지 못했습니다.",
                    suggested_check="잡알리오 상세의 공고 첨부파일을 확인합니다.",
                )
            )
        if not duty_description_text:
            verification_notes.append(
                NcsVerificationNote(
                    field="ksa_candidates",
                    reason="직무기술서 원문 텍스트가 없어 K/S/A 후보를 추출하지 않았습니다.",
                    suggested_check="직무기술서 PDF/HWP/HWPX 텍스트 추출 후 다시 매핑합니다.",
                )
            )
        elif not ksa_candidates:
            verification_notes.append(
                NcsVerificationNote(
                    field="ksa_candidates",
                    reason="직무기술서 텍스트에서 명시적인 지식/기술/태도 라벨을 찾지 못했습니다.",
                    suggested_check="표 구조나 이미지 기반 문서인지 확인하고 수동 검토합니다.",
                )
            )

        return NcsMappingInput(
            job_id=detail.id,
            institution_name=detail.institution_name,
            title=detail.title,
            source_url=detail.source_url,
            ncs_codes=ncs_codes,
            duty_description_attachments=duty_attachments,
            source_fields=source_fields,
            ksa_candidates=ksa_candidates,
            verification_notes=verification_notes,
        )

    @classmethod
    def _ncs_codes(
        cls,
        detail: JobAlioDetail,
        verification_notes: list[NcsVerificationNote],
    ) -> list[NcsCodeMapping]:
        if len(detail.ncs_codes) != len(detail.ncs_categories):
            verification_notes.append(
                NcsVerificationNote(
                    field="ncs_codes",
                    reason="NCS 코드 수와 표시명 수가 달라 일부 표시명을 비워 둡니다.",
                    suggested_check="잡알리오 원문 필드 ncsCdLst/ncsCdNmLst를 확인합니다.",
                )
            )
        mappings: list[NcsCodeMapping] = []
        for index, code in enumerate(detail.ncs_codes):
            display_name = (
                detail.ncs_categories[index] if index < len(detail.ncs_categories) else None
            )
            mappings.append(
                NcsCodeMapping(
                    code=code,
                    display_name=display_name,
                    evidence=[
                        NcsEvidenceReference(
                            title="잡알리오 NCS 코드",
                            source_type="ncs_code",
                            field_name="ncsCdLst/ncsCdNmLst",
                            excerpt=f"{code} {display_name or ''}".strip(),
                        )
                    ],
                )
            )
        return mappings

    @classmethod
    def _duty_description_attachments(
        cls,
        attachments: list[JobAlioAttachment],
    ) -> list[NcsAttachmentCandidate]:
        candidates: list[NcsAttachmentCandidate] = []
        for attachment in attachments:
            name = attachment.name or ""
            lower_name = name.lower()
            is_candidate = attachment.file_type == "C" or any(
                hint in lower_name for hint in cls.DUTY_ATTACHMENT_HINTS
            )
            if not is_candidate:
                continue
            candidates.append(
                NcsAttachmentCandidate(
                    name=attachment.name,
                    file_type=attachment.file_type,
                    url=attachment.url,
                    evidence=[
                        NcsEvidenceReference(
                            title=attachment.name or "직무기술서 첨부 후보",
                            source_type="duty_description_attachment",
                            field_name="attachments",
                            url=attachment.url,
                            excerpt=f"file_type={attachment.file_type or 'unknown'}",
                        )
                    ],
                )
            )
        return candidates

    @classmethod
    def _source_fields(cls, detail: JobAlioDetail) -> list[NcsEvidenceReference]:
        references: list[NcsEvidenceReference] = []
        for field_name, title in cls.SOURCE_TEXT_FIELDS.items():
            value = getattr(detail, field_name)
            if not value:
                continue
            references.append(
                NcsEvidenceReference(
                    title=title,
                    source_type="job_alio_field",
                    field_name=field_name,
                    url=detail.source_url,
                    excerpt=str(value)[:500],
                )
            )
        return references

    @classmethod
    def _ksa_candidates(
        cls,
        duty_description_text: str | None,
        *,
        source: NcsEvidenceReference | None = None,
    ) -> list[KsaCandidate]:
        if not duty_description_text:
            return []
        candidates: list[KsaCandidate] = []
        for category, labels in cls.KSA_LABELS.items():
            for label in labels:
                candidates.extend(
                    cls._extract_labeled_items(
                        duty_description_text,
                        category,
                        label,
                        source=source,
                    )
                )
        return cls._dedupe_candidates(candidates)

    @classmethod
    def _extract_labeled_items(
        cls,
        text: str,
        category: KsaCategory,
        label: str,
        *,
        source: NcsEvidenceReference | None = None,
    ) -> list[KsaCandidate]:
        pattern = re.compile(rf"{re.escape(label)}\s*[:：]\s*(.+)", flags=re.IGNORECASE)
        candidates: list[KsaCandidate] = []
        for match in pattern.finditer(text):
            for item in cls._split_items(match.group(1)):
                candidates.append(
                    KsaCandidate(
                        category=category,
                        name=item,
                        evidence=[
                            NcsEvidenceReference(
                                title=source.title if source else f"직무기술서 {label}",
                                source_type="duty_description_text",
                                field_name=label,
                                url=source.url if source else None,
                                excerpt=match.group(0)[:500],
                            )
                        ],
                    )
                )
        return candidates

    @staticmethod
    def _split_items(value: str) -> list[str]:
        cleaned = re.sub(r"\s+", " ", value).strip(" -•·")
        if not cleaned:
            return []
        parts = re.split(r"[,;/·•]| {2,}", cleaned)
        return [part.strip(" -") for part in parts if part.strip(" -")]

    @staticmethod
    def _dedupe_candidates(candidates: list[KsaCandidate]) -> list[KsaCandidate]:
        deduped: dict[tuple[str, str], KsaCandidate] = {}
        for candidate in candidates:
            key = (candidate.category, candidate.name)
            if key not in deduped:
                deduped[key] = candidate
        return list(deduped.values())


def prepare_ncs_mapping_input(
    detail: JobAlioDetail,
    *,
    duty_description_text: str | None = None,
    duty_description_source: NcsEvidenceReference | None = None,
) -> NcsMappingInput:
    return NcsMappingPreparer.prepare(
        detail,
        duty_description_text=duty_description_text,
        duty_description_source=duty_description_source,
    )
