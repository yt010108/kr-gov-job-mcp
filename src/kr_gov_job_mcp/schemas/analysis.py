"""Shared data schemas for public-sector job analysis tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Confidence = Literal["low", "medium", "high"]
EvidenceType = Literal[
    "job_posting",
    "duty_description",
    "ncs",
    "alio",
    "cleaneye",
    "institution_homepage",
    "press_release",
    "other",
]


class EvidenceSource(BaseModel):
    """A source snippet or link used to justify a structured output."""

    title: str
    source_type: EvidenceType
    url: str | None = None
    excerpt: str | None = None
    retrieved_at: str | None = Field(default=None, description="ISO 8601 date or datetime.")


class VerificationNote(BaseModel):
    field: str
    reason: str
    suggested_check: str


class ApplicantProfile(BaseModel):
    target_role: str
    known_skills: list[str] = Field(default_factory=list)
    preparation_status: str | None = None


class JobRequirement(BaseModel):
    category: Literal["eligibility", "required", "preferred", "other"]
    description: str
    evidence: list[EvidenceSource] = Field(default_factory=list)
    needs_verification: bool = False


class SelectionStep(BaseModel):
    name: str
    description: str | None = None
    order: int | None = None


class JobDuty(BaseModel):
    description: str
    evidence: list[EvidenceSource] = Field(default_factory=list)


class JobDetail(BaseModel):
    institution_name: str
    job_title: str | None = None
    job_family: str
    employment_type: str | None = None
    location: str | None = None
    deadline: str | None = Field(default=None, description="ISO 8601 date or original deadline text.")
    source_url: str | None = None
    qualifications: list[JobRequirement] = Field(default_factory=list)
    duties: list[JobDuty] = Field(default_factory=list)
    selection_steps: list[SelectionStep] = Field(default_factory=list)
    ncs_keywords: list[str] = Field(default_factory=list)
    verification_notes: list[VerificationNote] = Field(default_factory=list)


class CompetencyItem(BaseModel):
    name: str
    description: str | None = None
    evidence: list[EvidenceSource] = Field(default_factory=list)
    confidence: Confidence = "medium"


class NcsKsaMapping(BaseModel):
    job_family: str
    basic_competencies: list[CompetencyItem] = Field(default_factory=list)
    duty_competencies: list[CompetencyItem] = Field(default_factory=list)
    knowledge: list[CompetencyItem] = Field(default_factory=list)
    skills: list[CompetencyItem] = Field(default_factory=list)
    attitudes: list[CompetencyItem] = Field(default_factory=list)
    validation_points: list[VerificationNote] = Field(default_factory=list)


class BusinessItem(BaseModel):
    title: str
    summary: str
    evidence: list[EvidenceSource] = Field(default_factory=list)


class InstitutionStrategy(BaseModel):
    institution_name: str
    year: int | None = None
    main_businesses: list[BusinessItem] = Field(default_factory=list)
    growth_initiatives: list[BusinessItem] = Field(default_factory=list)
    job_connection_points: list[str] = Field(default_factory=list)
    verification_notes: list[VerificationNote] = Field(default_factory=list)


class WeaknessItem(BaseModel):
    title: str
    summary: str
    careful_expression: str | None = None
    contribution_idea: str | None = None
    evidence: list[EvidenceSource] = Field(default_factory=list)


class InstitutionWeakness(BaseModel):
    institution_name: str
    year: int | None = None
    improvement_tasks: list[WeaknessItem] = Field(default_factory=list)
    operational_risks: list[WeaknessItem] = Field(default_factory=list)
    verification_notes: list[VerificationNote] = Field(default_factory=list)


class PreparationItem(BaseModel):
    priority: Literal["P0", "P1", "P2"]
    title: str
    rationale: str
    recommended_actions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSource] = Field(default_factory=list)


class InstitutionMaterial(BaseModel):
    title: str
    reason: str
    source_hint: str


class JobFitReport(BaseModel):
    institution_name: str
    job_family: str
    applicant_profile: ApplicantProfile | None = None
    job_detail: JobDetail
    ncs_profile: NcsKsaMapping
    institution_strategy: InstitutionStrategy
    institution_weakness: InstitutionWeakness
    preparation_priorities: list[PreparationItem] = Field(default_factory=list)
    knowledge_gaps: list[PreparationItem] = Field(default_factory=list)
    institution_materials_to_check: list[InstitutionMaterial] = Field(default_factory=list)
    evidence_links: list[EvidenceSource] = Field(default_factory=list)
    verification_notes: list[VerificationNote] = Field(default_factory=list)
