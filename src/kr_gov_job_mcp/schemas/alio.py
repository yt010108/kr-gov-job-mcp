"""Schemas for ALIO management disclosure observations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AlioPointKind = Literal["national_assembly"]


class AlioInstitution(BaseModel):
    id: str
    name: str | None = None
    type_name: str | None = None
    ministry_name: str | None = None
    ceo: str | None = None
    established_date: str | None = None
    region: str | None = None
    address: str | None = None
    homepage_url: str | None = None
    main_business: str | None = None
    disclosure_start_date: str | None = None
    submission_no: str | None = None
    source_url: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class AlioInstitutionSearchResult(BaseModel):
    page: int
    total_count: int
    institutions: list[AlioInstitution] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class AlioPointAttachment(BaseModel):
    slot: str
    original_name: str | None = None
    save_name: str | None = None
    save_path: str | None = None
    submission_no: str | None = None
    download_url: str | None = None
    raw: str | None = None


class AlioPointItem(BaseModel):
    id: str
    kind: AlioPointKind
    report_form_no: str | None = None
    institution_id: str | None = None
    institution_name: str | None = None
    title: str | None = None
    registered_date: str | None = None
    action_plan_date: str | None = None
    action_result_date: str | None = None
    enforcement_start_date: str | None = None
    enforcement_end_date: str | None = None
    source_url: str | None = None
    attachments: list[AlioPointAttachment] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class AlioPointSearchResult(BaseModel):
    kind: AlioPointKind
    page: int
    limit: int
    total_count: int
    items: list[AlioPointItem] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class AlioReportFile(BaseModel):
    file_no: str
    disclosure_no: str | None = None
    report_form_no: str | None = None
    institution_id: str | None = None
    submission_no: str | None = None
    original_name: str | None = None
    save_name: str | None = None
    save_path: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    download_url: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class AlioReportDisclosure(BaseModel):
    disclosure_no: str
    report_form_no: str | None = None
    title: str | None = None
    report_kind: str | None = None
    disclosed_date: str | None = None
    institution_id: str | None = None
    institution_name: str | None = None
    submission_no: str | None = None
    source_url: str | None = None
    attachments: list[AlioReportFile] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class AlioReportSearchResult(BaseModel):
    report_form_root_no: str
    page: int | None = None
    total_count: int | None = None
    reports: list[AlioReportDisclosure] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
