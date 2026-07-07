"""Schemas for evidence-backed job fit preparation reports."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from kr_gov_job_mcp.schemas.ncs import NcsMappingInput


JobFitEvidenceType = Literal[
    "job_posting",
    "job_alio_field",
    "duty_description",
    "duty_description_text",
    "ncs",
    "institution_signal",
    "manual",
]
PreparationPriority = Literal["P0", "P1", "P2"]


class JobFitEvidenceSource(BaseModel):
    title: str
    source_type: JobFitEvidenceType
    url: str | None = None
    excerpt: str | None = None


class JobFitVerificationNote(BaseModel):
    field: str
    reason: str
    suggested_check: str


class ApplicantReadinessInput(BaseModel):
    target_role: str | None = None
    known_skills: list[str] = Field(default_factory=list)
    preparation_notes: str | None = None


class JobFitInstitutionSignal(BaseModel):
    title: str
    summary: str | None = None
    evidence: list[JobFitEvidenceSource] = Field(default_factory=list)


class JobFitPreparationItem(BaseModel):
    priority: PreparationPriority
    title: str
    rationale: str
    recommended_actions: list[str] = Field(default_factory=list)
    evidence: list[JobFitEvidenceSource] = Field(default_factory=list)
    verification_notes: list[JobFitVerificationNote] = Field(default_factory=list)


class InstitutionMaterialCheck(BaseModel):
    title: str
    reason: str
    source_hint: str


class JobFitPreparationReport(BaseModel):
    job_id: str
    institution_name: str | None = None
    job_title: str | None = None
    applicant_target_role: str | None = None
    preparation_items: list[JobFitPreparationItem] = Field(default_factory=list)
    knowledge_gaps: list[JobFitPreparationItem] = Field(default_factory=list)
    ncs_mapping: NcsMappingInput | None = None
    institution_materials_to_check: list[InstitutionMaterialCheck] = Field(default_factory=list)
    evidence_links: list[JobFitEvidenceSource] = Field(default_factory=list)
    verification_notes: list[JobFitVerificationNote] = Field(default_factory=list)
