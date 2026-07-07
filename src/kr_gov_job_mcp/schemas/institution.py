"""Schemas for preparing institution analysis inputs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from kr_gov_job_mcp.schemas.cleaneye import CleaneyeInstitutionKind


InstitutionSourceType = Literal[
    "alio_disclosure",
    "cleaneye",
    "institution_homepage",
    "job_alio",
    "manual",
]
InstitutionSignalCategory = Literal[
    "business_direction",
    "improvement_task",
    "job_connection",
    "financial_or_operational",
    "management_evaluation",
]


class InstitutionVerificationNote(BaseModel):
    field: str
    reason: str
    suggested_check: str


class InstitutionIdentityCandidate(BaseModel):
    name: str
    source_type: InstitutionSourceType
    source_id: str | None = None
    code_type: str | None = None
    source_url: str | None = None
    confidence: Literal["low", "medium", "high"] = "medium"


class InstitutionEvidence(BaseModel):
    title: str
    source_type: InstitutionSourceType
    url: str | None = None
    source_id: str | None = None
    collected_at: str | None = None
    excerpt: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)


class InstitutionSignalCandidate(BaseModel):
    category: InstitutionSignalCategory
    title: str
    summary: str | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    evidence: list[InstitutionEvidence] = Field(default_factory=list)
    needs_verification: bool = False


class InstitutionAnalysisInput(BaseModel):
    institution_name: str
    normalized_name: str
    aliases: list[str] = Field(default_factory=list)
    alio_id: str | None = None
    cleaneye_id: str | None = None
    cleaneye_kind: CleaneyeInstitutionKind | None = None
    identity_candidates: list[InstitutionIdentityCandidate] = Field(default_factory=list)
    evidence: list[InstitutionEvidence] = Field(default_factory=list)
    signals: list[InstitutionSignalCandidate] = Field(default_factory=list)
    verification_notes: list[InstitutionVerificationNote] = Field(default_factory=list)
