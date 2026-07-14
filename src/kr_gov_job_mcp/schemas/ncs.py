"""Schemas for preparing NCS/KSA mapping inputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


NcsEvidenceType = Literal[
    "job_alio_field",
    "duty_description_attachment",
    "duty_description_text",
    "ncs_code",
]
AttachmentExtractionStatus = Literal[
    "not_selected",
    "provided_text",
    "extracted",
    "unsupported_format",
    "ocr_required",
    "download_failed",
    "invalid_pdf",
]
KsaCategory = Literal[
    "basic_competency",
    "duty_competency",
    "knowledge",
    "skill",
    "attitude",
]


class NcsEvidenceReference(BaseModel):
    title: str
    source_type: NcsEvidenceType
    field_name: str | None = None
    url: str | None = None
    excerpt: str | None = None


class NcsVerificationNote(BaseModel):
    field: str
    reason: str
    suggested_check: str


class NcsCodeMapping(BaseModel):
    code: str
    display_name: str | None = None
    evidence: list[NcsEvidenceReference] = Field(default_factory=list)


class NcsAttachmentCandidate(BaseModel):
    name: str | None = None
    file_type: str | None = None
    url: str | None = None
    selected: bool = False
    selection_reason: str | None = None
    extraction_status: AttachmentExtractionStatus = "not_selected"
    evidence: list[NcsEvidenceReference] = Field(default_factory=list)


class KsaCandidate(BaseModel):
    category: KsaCategory
    name: str
    evidence: list[NcsEvidenceReference] = Field(default_factory=list)
    needs_verification: bool = False


class NcsMappingInput(BaseModel):
    job_id: str
    institution_name: str | None = None
    title: str | None = None
    source_url: str | None = None
    ncs_codes: list[NcsCodeMapping] = Field(default_factory=list)
    duty_description_attachments: list[NcsAttachmentCandidate] = Field(default_factory=list)
    source_fields: list[NcsEvidenceReference] = Field(default_factory=list)
    ksa_candidates: list[KsaCandidate] = Field(default_factory=list)
    verification_notes: list[NcsVerificationNote] = Field(default_factory=list)


class NcsMappingReport(BaseModel):
    job_id: str
    ncs_codes: list[NcsCodeMapping] = Field(default_factory=list)
    basic_competencies: list[KsaCandidate] = Field(default_factory=list)
    duty_competencies: list[KsaCandidate] = Field(default_factory=list)
    knowledge: list[KsaCandidate] = Field(default_factory=list)
    skills: list[KsaCandidate] = Field(default_factory=list)
    attitudes: list[KsaCandidate] = Field(default_factory=list)
    attachment_candidates: list[NcsAttachmentCandidate] = Field(default_factory=list)
    evidence: list[NcsEvidenceReference] = Field(default_factory=list)
    verification_notes: list[NcsVerificationNote] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
