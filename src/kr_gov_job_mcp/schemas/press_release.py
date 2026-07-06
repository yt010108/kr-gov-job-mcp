"""Schemas for institution press release observations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PressReleaseLink(BaseModel):
    url: str
    text: str | None = None
    kind: str = "other"


class PressReleaseListItem(BaseModel):
    title: str
    url: str
    published_date: str | None = None
    raw_text: str | None = None


class PressReleaseDetail(BaseModel):
    title: str
    url: str
    published_date: str | None = None
    body_text_preview: str | None = None
    links: list[PressReleaseLink] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)

    @property
    def attachment_candidates(self) -> list[PressReleaseLink]:
        return [link for link in self.links if link.kind == "attachment_candidate"]


class PressReleaseEvidenceSource(BaseModel):
    source_type: str = "press_release"
    institution_name: str | None = None
    title: str
    url: str
    published_date: str | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    excerpt: str | None = None
