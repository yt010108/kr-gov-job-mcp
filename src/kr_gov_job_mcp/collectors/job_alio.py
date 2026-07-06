"""Collector for Job-ALIO recruitment notices."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.clients.job_alio_web_client import JobAlioWebClient
from kr_gov_job_mcp.collectors.base import (
    CollectionResult,
    CollectorHttpPolicy,
    CollectorRequest,
    RawSample,
    RawSampleWriter,
    utc_now_text,
)


class JobAlioCollector:
    """Collect raw Job-ALIO list and detail payloads before field normalization."""

    name = "job_alio"
    _SEARCH_KEYS = {
        "keyword",
        "page",
        "limit",
        "ongoing_only",
        "institution_code",
        "ncs_code",
        "region_code",
        "academic_condition_code",
        "employment_type_code",
        "recruitment_type",
        "replacement_only",
        "announcement_start_date",
        "announcement_end_date",
        "institution_type",
        "institution_classification",
    }

    def __init__(
        self,
        client: JobAlioWebClient | None = None,
        http_policy: CollectorHttpPolicy | None = None,
        default_detail_limit: int = 5,
    ) -> None:
        self.http_policy = http_policy or CollectorHttpPolicy()
        self.default_detail_limit = default_detail_limit
        self._owns_client = client is None
        self._client = client or JobAlioWebClient(timeout=self.http_policy.timeout_seconds)

    async def __aenter__(self) -> JobAlioCollector:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def collect_raw(
        self,
        *,
        query: Mapping[str, Any],
        sample_store: RawSampleWriter,
    ) -> CollectionResult:
        collected_at = utc_now_text()
        search_kwargs = self._search_kwargs(query)
        detail_limit = self._to_int(query.get("detail_limit"), self.default_detail_limit)
        fetch_details = self._to_bool(query.get("fetch_details"), default=True)
        requested_detail_ids = self._detail_ids(query.get("detail_ids"))

        search_result = await self._client.search_jobs(**search_kwargs)
        list_rows = [job.raw for job in search_result.jobs]
        raw_sample_paths = [
            sample_store.write_sample(
                RawSample(
                    source=self.name,
                    raw_type="list",
                    sample_id=self._list_sample_id(search_kwargs),
                    payload={
                        "page": search_result.page,
                        "limit": search_result.limit,
                        "total_count": search_result.total_count,
                        "jobs": list_rows,
                    },
                    request=CollectorRequest(
                        method="POST",
                        url=JobAlioWebClient.LIST_URL,
                        endpoint="recrutInquiryAjaxList.do",
                        body=search_kwargs,
                    ),
                    collected_at=collected_at,
                    content_type="application/json",
                    metadata={
                        "result_count": len(search_result.jobs),
                        "field_names": self._field_names(list_rows),
                    },
                )
            )
        ]

        errors: list[str] = []
        detail_ids = requested_detail_ids or [
            job.id for job in search_result.jobs[:detail_limit] if job.id
        ]
        if fetch_details:
            for detail_id in detail_ids:
                try:
                    detail = await self._client.fetch_job_detail(detail_id)
                except Exception as exc:  # noqa: BLE001 - keep collecting the remaining details.
                    errors.append(f"detail {detail_id}: {exc}")
                    continue

                raw_sample_paths.append(
                    sample_store.write_sample(
                        RawSample(
                            source=self.name,
                            raw_type="detail",
                            sample_id=detail.id,
                            payload=detail.raw,
                            request=CollectorRequest(
                                method="POST",
                                url=JobAlioWebClient.DETAIL_URL,
                                endpoint="recrutInquiryAjaxDetail.do",
                                body={"sn": detail.id},
                            ),
                            collected_at=collected_at,
                            content_type="application/json",
                            metadata={
                                "attachment_count": len(detail.attachments),
                                "step_count": len(detail.steps),
                                "ncs_code_count": len(detail.ncs_codes),
                                "field_names": sorted(detail.raw.keys()),
                            },
                        )
                    )
                )

        return CollectionResult(
            source=self.name,
            run_id=f"{self.name}-{collected_at.replace(':', '').replace('-', '')}",
            collected_at=collected_at,
            raw_sample_paths=raw_sample_paths,
            normalized_count=len(search_result.jobs),
            notes=[
                f"list_rows={len(search_result.jobs)}",
                f"details_requested={len(detail_ids) if fetch_details else 0}",
                f"details_saved={len(raw_sample_paths) - 1}",
            ],
            errors=errors,
        )

    def _search_kwargs(self, query: Mapping[str, Any]) -> dict[str, Any]:
        kwargs = {key: query[key] for key in self._SEARCH_KEYS if key in query}
        kwargs["page"] = self._to_int(kwargs.get("page"), 1)
        kwargs["limit"] = self._to_int(kwargs.get("limit"), 20)
        if "ongoing_only" in kwargs:
            kwargs["ongoing_only"] = self._to_bool(kwargs["ongoing_only"], default=True)
        return kwargs

    @staticmethod
    def _field_names(rows: list[dict[str, Any]]) -> list[str]:
        return sorted({key for row in rows for key in row})

    @staticmethod
    def _detail_ids(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, list | tuple | set):
            return [str(part).strip() for part in value if str(part).strip()]
        return [str(value).strip()]

    @staticmethod
    def _list_sample_id(search_kwargs: Mapping[str, Any]) -> str:
        page = search_kwargs.get("page", 1)
        limit = search_kwargs.get("limit", 20)
        keyword = search_kwargs.get("keyword")
        if keyword:
            return f"list-page-{page}-limit-{limit}-{keyword}"
        return f"list-page-{page}-limit-{limit}"

    @staticmethod
    def _to_int(value: Any, default: int) -> int:
        if value is None or value == "":
            return default
        try:
            return int(str(value))
        except ValueError:
            return default

    @staticmethod
    def _to_bool(value: Any, *, default: bool) -> bool:
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {"0", "false", "n", "no"}
