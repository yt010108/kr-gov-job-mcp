"""Raw collector for institution press release pages."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kr_gov_job_mcp.clients.press_release_client import (
    PressReleaseClient,
    PressReleaseClientError,
)
from kr_gov_job_mcp.collectors.base import (
    CollectionResult,
    CollectorHttpPolicy,
    CollectorRequest,
    RawSample,
    RawSampleWriter,
    utc_now_text,
)


class PressReleaseCollector:
    """Collect recent press release list/detail samples from a public institution site."""

    name = "press_release"

    def __init__(
        self,
        client: PressReleaseClient | None = None,
        http_policy: CollectorHttpPolicy | None = None,
    ) -> None:
        self.http_policy = http_policy or CollectorHttpPolicy()
        self.client = client or PressReleaseClient(
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
            run_id=f"press-release-{collected_at}",
            collected_at=collected_at,
        )

        list_url = self._to_text(query.get("list_url") or query.get("url"))
        if not list_url:
            result.errors.append("list_url or url is required")
            return result

        limit = self._to_int(query.get("limit")) or 3
        institution_name = self._to_text(query.get("institution_name"))
        keywords = self._keywords(query.get("keywords"))

        try:
            list_items, list_html = await self.client.fetch_list(list_url, limit=limit)
        except PressReleaseClientError as exc:
            result.errors.append(str(exc))
            return result

        list_request = CollectorRequest(method="GET", url=list_url)
        sample_prefix = self._sample_id(institution_name or list_url)
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="html",
                sample_id=f"{sample_prefix}-list-html",
                payload=list_html,
                request=list_request,
                collected_at=collected_at,
                content_type="text/html",
                metadata={"institution_name": institution_name, "list_url": list_url},
            ),
        )
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="metadata",
                sample_id=f"{sample_prefix}-list-metadata",
                payload={"items": [item.model_dump() for item in list_items]},
                request=list_request,
                collected_at=collected_at,
                content_type="application/json",
                metadata={
                    "institution_name": institution_name,
                    "list_url": list_url,
                    "item_count": len(list_items),
                },
            ),
        )

        for item in list_items[:limit]:
            await self._collect_detail(
                result,
                sample_store,
                item=item,
                institution_name=institution_name,
                keywords=keywords,
                collected_at=collected_at,
            )

        result.notes.extend(
            [
                "Press releases are collected as evidence candidates, not final institution analysis.",
                "Keyword matches are recall-oriented and should be reviewed before report generation.",
            ]
        )
        return result

    async def _collect_detail(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        *,
        item: Any,
        institution_name: str | None,
        keywords: tuple[str, ...],
        collected_at: str,
    ) -> None:
        try:
            detail, detail_html = await self.client.fetch_detail(item, keywords=keywords)
        except PressReleaseClientError as exc:
            result.errors.append(f"{item.url}: {exc}")
            return

        request = CollectorRequest(method="GET", url=item.url)
        sample_prefix = self._sample_id(item.url)
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="html",
                sample_id=f"{sample_prefix}-detail-html",
                payload=detail_html,
                request=request,
                collected_at=collected_at,
                content_type="text/html",
                metadata={"institution_name": institution_name, "title": item.title},
            ),
        )
        evidence = self.client.to_evidence_source(detail, institution_name=institution_name)
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="metadata",
                sample_id=f"{sample_prefix}-detail-metadata",
                payload={
                    "detail": detail.model_dump(),
                    "evidence_source": evidence.model_dump(),
                },
                request=request,
                collected_at=collected_at,
                content_type="application/json",
                metadata={
                    "institution_name": institution_name,
                    "title": detail.title,
                    "published_date": detail.published_date,
                    "matched_keywords": detail.matched_keywords,
                    "attachment_candidate_count": len(detail.attachment_candidates),
                },
            ),
        )
        result.normalized_count += 1

    def _write_sample(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        sample: RawSample,
    ) -> Path:
        path = sample_store.write_sample(sample)
        result.raw_sample_paths.append(path)
        return path

    @staticmethod
    def _keywords(value: Any) -> tuple[str, ...]:
        if value is None:
            return PressReleaseClient.DEFAULT_STRATEGY_KEYWORDS
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        if isinstance(value, list):
            return tuple(str(part).strip() for part in value if str(part).strip())
        return PressReleaseClient.DEFAULT_STRATEGY_KEYWORDS

    @staticmethod
    def _sample_id(value: str) -> str:
        return value

    @staticmethod
    def _to_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(str(value).strip())
        except ValueError:
            return None
