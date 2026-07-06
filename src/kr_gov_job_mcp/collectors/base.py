"""Common collector contracts used before final analysis schemas are settled."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


RawSampleType = Literal[
    "list",
    "detail",
    "attachment",
    "html",
    "pdf_text",
    "api_response",
    "metadata",
    "other",
]
RawPayload = dict[str, Any] | list[Any] | str


def utc_now_text() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class CollectorHttpPolicy(BaseModel):
    """HTTP behavior shared by public data collectors."""

    timeout_seconds: float = Field(default=10.0, gt=0)
    retry_attempts: int = Field(default=2, ge=0)
    retry_backoff_seconds: float = Field(default=0.5, ge=0)
    rate_limit_per_second: float = Field(default=1.0, gt=0)
    user_agent: str = "kr-gov-job-mcp/0.1 (raw-data-observation)"


class CollectorRequest(BaseModel):
    """Sanitized request metadata saved with a raw sample."""

    method: str = "GET"
    url: str | None = None
    endpoint: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class RawSample(BaseModel):
    """Raw source payload plus enough context to compare source fields later."""

    source: str
    raw_type: RawSampleType
    sample_id: str
    payload: RawPayload
    request: CollectorRequest = Field(default_factory=CollectorRequest)
    collected_at: str = Field(default_factory=utc_now_text)
    content_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectionResult(BaseModel):
    """Summary returned by a collector run.

    Raw sample paths are relative to the repository root when possible.
    """

    source: str
    run_id: str
    collected_at: str = Field(default_factory=utc_now_text)
    raw_sample_paths: list[Path] = Field(default_factory=list)
    normalized_count: int = 0
    notes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


@runtime_checkable
class RawSampleWriter(Protocol):
    """Storage interface collectors need for saving raw samples."""

    def write_sample(self, sample: RawSample) -> Path:
        """Persist a raw sample and return its path."""
        ...


@runtime_checkable
class Collector(Protocol):
    """Minimum interface each source collector should expose."""

    name: str
    http_policy: CollectorHttpPolicy

    async def collect_raw(
        self,
        *,
        query: Mapping[str, Any],
        sample_store: RawSampleWriter,
    ) -> CollectionResult:
        """Collect source data and write raw samples before normalization."""
        ...
