"""Normalized job posting schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JobAlioAttachment(BaseModel):
    sort_no: int | None = None
    file_no: int | None = None
    name: str | None = None
    file_type: str | None = None
    url: str | None = None


class JobAlioStep(BaseModel):
    sort_no: int | None = None
    title: str | None = None
    step_sn: int | None = None
    min_step_sn: int | None = None
    max_step_sn: int | None = None
    headcount: int | None = None
    applicant_count: int | None = None
    competition_rate: float | None = None
    occurrence_date: str | None = None


class JobAlioSummary(BaseModel):
    id: str
    institution_name: str | None = None
    institution_code: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_ongoing: bool | None = None
    ncs_codes: list[str] = Field(default_factory=list)
    ncs_categories: list[str] = Field(default_factory=list)
    employment_types: list[str] = Field(default_factory=list)
    recruitment_type: str | None = None
    headcount: int | None = None
    work_regions: list[str] = Field(default_factory=list)
    source_url: str | None = None
    qualification: str | None = None
    preferred_conditions: str | None = None
    preference: str | None = None
    disqualification_reason: str | None = None
    screening_procedure: str | None = None
    replacement_recruitment: bool | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class JobAlioDetail(JobAlioSummary):
    attachments: list[JobAlioAttachment] = Field(default_factory=list)
    steps: list[JobAlioStep] = Field(default_factory=list)


class JobAlioSearchResult(BaseModel):
    page: int
    limit: int
    total_count: int
    jobs: list[JobAlioSummary] = Field(default_factory=list)
