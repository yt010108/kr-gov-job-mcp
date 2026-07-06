"""Schemas for Cleaneye local public enterprise observations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


CleaneyeInstitutionKind = Literal["local_public_enterprise", "local_invested_contributed"]


class CleaneyeInstitution(BaseModel):
    id: str
    name: str | None = None
    kind: CleaneyeInstitutionKind
    kind_code: str | None = None
    source_url: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class CleaneyeInstitutionSearchResult(BaseModel):
    kind: CleaneyeInstitutionKind
    total_count: int
    institutions: list[CleaneyeInstitution] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class CleaneyeDisclosureItem(BaseModel):
    item_no: str
    item_id: str | None = None
    name: str | None = None
    action_url: str | None = None
    use_yn: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
