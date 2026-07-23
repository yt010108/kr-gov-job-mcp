"""Schemas for evidence-grounded STAR answer frameworks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


StarAnswerMode = Literal["cover_letter", "interview", "both"]
StarSectionStatus = Literal["supported", "missing"]
StarDraftStatus = Literal["ready", "needs_evidence", "not_requested"]


class StarSection(BaseModel):
    """One STAR section with only excerpts supplied by the user."""

    status: StarSectionStatus
    source_excerpts: list[str] = Field(default_factory=list)
    guidance: str


class StarMissingEvidence(BaseModel):
    field: str
    reason: str
    follow_up_question: str


class StarRiskFlag(BaseModel):
    category: Literal[
        "absolute_claim",
        "exclusive_claim",
        "scope_claim",
        "unverified_metric",
    ]
    expression: str
    reason: str
    safer_framing: str


class StarJobConnection(BaseModel):
    competency: str | None = None
    connection_sentence: str
    source_excerpts: list[str] = Field(default_factory=list)
    needs_verification: bool = True


class StarInstitutionConnection(BaseModel):
    institution_name: str
    connection_sentence: str
    needs_verification: bool = True


class StarInterviewAnswer(BaseModel):
    status: StarDraftStatus
    short_answer: str | None = None
    supporting_excerpts: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class StarCoverLetterDraft(BaseModel):
    status: StarDraftStatus
    sentence_draft: str | None = None
    supporting_excerpts: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class StarAnswerFramework(BaseModel):
    question: str
    target_job: str
    institution_name: str | None = None
    ncs_competencies: list[str] = Field(default_factory=list)
    mode: StarAnswerMode
    star: dict[str, StarSection]
    unclassified_excerpts: list[str] = Field(default_factory=list)
    job_connections: list[StarJobConnection] = Field(default_factory=list)
    institution_connection: StarInstitutionConnection | None = None
    missing_evidence: list[StarMissingEvidence] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    risk_flags: list[StarRiskFlag] = Field(default_factory=list)
    interview_answer: StarInterviewAnswer
    cover_letter_draft: StarCoverLetterDraft
    verification_notes: list[str] = Field(default_factory=list)
