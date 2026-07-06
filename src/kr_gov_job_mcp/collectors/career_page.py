"""Raw collector for institution career pages linked from Job-ALIO."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kr_gov_job_mcp.clients.career_page_client import CareerPageClient, CareerPageClientError
from kr_gov_job_mcp.collectors.base import (
    CollectionResult,
    CollectorHttpPolicy,
    CollectorRequest,
    RawSample,
    RawSampleWriter,
    utc_now_text,
)


class CareerPageCollector:
    """Collect a raw HTML snapshot and lightweight metadata from an institution URL."""

    name = "career_page"

    def __init__(
        self,
        client: CareerPageClient | None = None,
        http_policy: CollectorHttpPolicy | None = None,
    ) -> None:
        self.http_policy = http_policy or CollectorHttpPolicy()
        self.client = client or CareerPageClient(
            timeout=self.http_policy.timeout_seconds,
            user_agent=self.http_policy.user_agent,
        )

    async def collect_raw(
        self,
        *,
        query: Mapping[str, Any],
        sample_store: RawSampleWriter,
    ) -> CollectionResult:
        collected_at = utc_now_text()
        result = CollectionResult(
            source=self.name,
            run_id=f"career-page-{collected_at}",
            collected_at=collected_at,
        )

        url = self._to_text(query.get("source_url") or query.get("url"))
        if not url:
            result.errors.append("source_url or url is required")
            return result

        try:
            snapshot, html = await self.client.fetch_snapshot(url)
        except CareerPageClientError as exc:
            result.errors.append(str(exc))
            return result

        sample_id = self._sample_id(query, snapshot.final_url)
        request = CollectorRequest(method="GET", url=url)
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="html",
                sample_id=f"{sample_id}-html",
                payload=html,
                request=request,
                collected_at=collected_at,
                content_type=snapshot.content_type,
                metadata={
                    "final_url": snapshot.final_url,
                    "status_code": snapshot.status_code,
                    "page_type": snapshot.page_type,
                },
            ),
        )
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="metadata",
                sample_id=f"{sample_id}-metadata",
                payload=snapshot.model_dump(),
                request=request,
                collected_at=collected_at,
                content_type="application/json",
                metadata={
                    "job_id": self._to_text(query.get("job_id")),
                    "institution_name": self._to_text(query.get("institution_name")),
                    "attachment_candidate_count": len(snapshot.attachment_candidates),
                    "apply_candidate_count": len(snapshot.apply_candidates),
                    "page_type": snapshot.page_type,
                },
            ),
        )
        result.normalized_count = 1
        result.notes.extend(
            [
                "This collector preserves source HTML and candidate links only.",
                "Attachments and application links require site-specific validation before download or submission.",
            ]
        )
        return result

    def _write_sample(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        sample: RawSample,
    ) -> Path:
        path = sample_store.write_sample(sample)
        result.raw_sample_paths.append(path)
        return path

    @classmethod
    def _sample_id(cls, query: Mapping[str, Any], final_url: str) -> str:
        return (
            cls._to_text(query.get("job_id"))
            or cls._to_text(query.get("institution_name"))
            or final_url
        )

    @staticmethod
    def _to_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
