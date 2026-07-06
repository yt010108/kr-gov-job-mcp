"""Schemas for institution career page observations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CareerPageLinkKind = Literal["attachment_candidate", "apply_candidate", "other"]


class CareerPageLink(BaseModel):
    url: str
    text: str | None = None
    kind: CareerPageLinkKind = "other"


class CareerPageSnapshot(BaseModel):
    source_url: str
    final_url: str
    status_code: int
    content_type: str | None = None
    title: str | None = None
    page_type: str = "unknown"
    body_text_preview: str | None = None
    links: list[CareerPageLink] = Field(default_factory=list)

    @property
    def attachment_candidates(self) -> list[CareerPageLink]:
        return [link for link in self.links if link.kind == "attachment_candidate"]

    @property
    def apply_candidates(self) -> list[CareerPageLink]:
        return [link for link in self.links if link.kind == "apply_candidate"]
