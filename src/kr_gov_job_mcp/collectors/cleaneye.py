"""Raw collector for Cleaneye local public enterprise disclosures."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kr_gov_job_mcp.clients.cleaneye_client import CleaneyeClient, CleaneyeClientError
from kr_gov_job_mcp.collectors.base import (
    CollectionResult,
    CollectorHttpPolicy,
    CollectorRequest,
    RawSample,
    RawSampleWriter,
    utc_now_text,
)
from kr_gov_job_mcp.schemas.cleaneye import (
    CleaneyeDisclosureItem,
    CleaneyeInstitution,
    CleaneyeInstitutionKind,
    CleaneyeInstitutionSearchResult,
)


class CleaneyeCollector:
    """Collect raw Cleaneye search, item tree, metadata, and HTML samples."""

    name = "cleaneye"

    DEFAULT_PUBLIC_ITEMS = {
        "general_status": "1_1",
        "management_evaluation": "10_1",
        "debt_scale": "7_1",
        "business_report": "12_3",
        "new_investment": "6_19_4",
    }
    DEFAULT_INVESTED_ITEMS = {
        "general_status": "10",
        "management_result": "45",
        "finance": "50_30",
        "finance_debt_plan": "50_70",
        "external_audit": "60_20",
    }

    def __init__(
        self,
        client: CleaneyeClient | None = None,
        http_policy: CollectorHttpPolicy | None = None,
    ) -> None:
        self.client = client or CleaneyeClient()
        self.http_policy = http_policy or CollectorHttpPolicy()

    async def collect_raw(
        self,
        *,
        query: Mapping[str, Any],
        sample_store: RawSampleWriter,
    ) -> CollectionResult:
        collected_at = utc_now_text()
        result = CollectionResult(
            source=self.name,
            run_id=f"cleaneye-{collected_at}",
            collected_at=collected_at,
        )

        keyword = self._to_text(query.get("institution_name") or query.get("keyword"))
        institution_id = self._to_text(query.get("institution_id"))
        kind = self._to_kind(query.get("kind"))
        if not keyword and not institution_id:
            result.errors.append("institution_name or institution_id is required")
            return result

        search_result = await self._search(result, keyword, kind)
        selected = self._select_institution(search_result, keyword, institution_id)
        if institution_id and selected is None:
            selected = CleaneyeInstitution(
                id=institution_id,
                name=keyword,
                kind=kind,
                source_url=CleaneyeClient.home_url(kind),
            )
        if selected is None:
            result.errors.append("Cleaneye search returned no usable institution")
            return result

        if search_result is not None:
            self._write_sample(
                result,
                sample_store,
                RawSample(
                    source=self.name,
                    raw_type="list",
                    sample_id=self._sample_id(selected.id, "search"),
                    payload=search_result.raw,
                    request=self._search_request(keyword, kind),
                    collected_at=collected_at,
                    content_type="application/json",
                    metadata={
                        "kind": kind,
                        "normalized_count": len(search_result.institutions),
                        "selected_institution_id": selected.id,
                    },
                ),
            )

        item_tree = await self._try_step(
            result,
            "item tree",
            self.client.fetch_item_tree(institution_id=selected.id, kind=selected.kind),
        )
        if isinstance(item_tree, dict):
            self._write_sample(
                result,
                sample_store,
                RawSample(
                    source=self.name,
                    raw_type="list",
                    sample_id=self._sample_id(selected.id, "item-tree"),
                    payload=item_tree,
                    request=CollectorRequest(
                        method="POST",
                        url=CleaneyeClient._absolute_url(
                            CleaneyeClient.PUBLIC_ITEM_TREE_PATH
                            if selected.kind == "local_public_enterprise"
                            else CleaneyeClient.INVESTED_ITEM_TREE_PATH
                        ),
                        endpoint=(
                            CleaneyeClient.PUBLIC_ITEM_TREE_PATH
                            if selected.kind == "local_public_enterprise"
                            else CleaneyeClient.INVESTED_ITEM_TREE_PATH
                        ),
                        body={"entId": selected.id},
                    ),
                    collected_at=collected_at,
                    content_type="application/json",
                    metadata={"kind": selected.kind},
                ),
            )

        item_map = (
            self.DEFAULT_PUBLIC_ITEMS
            if selected.kind == "local_public_enterprise"
            else self.DEFAULT_INVESTED_ITEMS
        )
        for label, item_no in item_map.items():
            await self._collect_item(
                result,
                sample_store,
                institution=selected,
                label=label,
                item_no=item_no,
                collected_at=collected_at,
            )

        self._write_source_links(result, sample_store, selected, collected_at)
        result.notes.extend(
            [
                "Cleaneye public enterprises use entId; invested/contributed institutions use insttCode.",
                "Disclosure item bodies are HTML and need a table parser before field-level normalization.",
                "ALIO and Cleaneye should stay separate by source/kind before shared analysis schemas.",
            ]
        )
        return result

    async def _search(
        self,
        result: CollectionResult,
        keyword: str | None,
        kind: CleaneyeInstitutionKind,
    ) -> CleaneyeInstitutionSearchResult | None:
        if not keyword:
            return None
        if kind == "local_public_enterprise":
            return await self._try_step(
                result,
                "public enterprise search",
                self.client.search_public_enterprises(keyword=keyword),
            )
        return await self._try_step(
            result,
            "invested/contributed search",
            self.client.search_invested_or_contributed(keyword=keyword),
        )

    async def _collect_item(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        *,
        institution: CleaneyeInstitution,
        label: str,
        item_no: str,
        collected_at: str,
    ) -> None:
        item = await self._try_step(
            result,
            f"{label} metadata",
            self.client.fetch_item_metadata(item_no=item_no, kind=institution.kind),
        )
        if not isinstance(item, CleaneyeDisclosureItem):
            return

        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="metadata",
                sample_id=self._sample_id(institution.id, f"{label}-metadata"),
                payload=item.raw,
                request=CollectorRequest(
                    method="POST",
                    url=CleaneyeClient._absolute_url(
                        CleaneyeClient.PUBLIC_ITEM_META_PATH
                        if institution.kind == "local_public_enterprise"
                        else CleaneyeClient.INVESTED_ITEM_META_PATH
                    ),
                    endpoint=(
                        CleaneyeClient.PUBLIC_ITEM_META_PATH
                        if institution.kind == "local_public_enterprise"
                        else CleaneyeClient.INVESTED_ITEM_META_PATH
                    ),
                    body={"item": item_no},
                ),
                collected_at=collected_at,
                content_type="application/json",
                metadata={
                    "kind": institution.kind,
                    "institution_id": institution.id,
                    "label": label,
                },
            ),
        )
        result.normalized_count += 1

        html = await self._try_step(
            result,
            f"{label} html",
            self.client.fetch_disclosure_html(institution=institution, item=item),
        )
        if html is None:
            return
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="html",
                sample_id=self._sample_id(institution.id, f"{label}-html"),
                payload=html,
                request=CollectorRequest(
                    method="POST",
                    url=item.action_url,
                    endpoint=item.action_url,
                    body={
                        "entId": institution.id,
                        "entName": institution.name,
                        "entKind": institution.kind_code,
                        "itemId": item.item_id,
                    },
                ),
                collected_at=collected_at,
                content_type="text/html",
                metadata={
                    "kind": institution.kind,
                    "institution_id": institution.id,
                    "label": label,
                    "item": item.model_dump(exclude={"raw"}),
                },
            ),
        )

    def _write_source_links(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        institution: CleaneyeInstitution,
        collected_at: str,
    ) -> None:
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="metadata",
                sample_id=self._sample_id(institution.id, "source-links"),
                payload={
                    "home": CleaneyeClient.home_url(institution.kind),
                    "institution_id": institution.id,
                    "institution_name": institution.name,
                    "kind": institution.kind,
                },
                collected_at=collected_at,
                metadata={"institution_id": institution.id, "kind": institution.kind},
            ),
        )

    def _write_sample(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        sample: RawSample,
    ) -> Path:
        path = sample_store.write_sample(sample)
        result.raw_sample_paths.append(path)
        return path

    async def _try_step(self, result: CollectionResult, label: str, awaitable: Any) -> Any | None:
        try:
            return await awaitable
        except CleaneyeClientError as exc:
            result.errors.append(f"{label}: {exc}")
            return None

    @classmethod
    def _select_institution(
        cls,
        search_result: CleaneyeInstitutionSearchResult | None,
        keyword: str | None,
        institution_id: str | None,
    ) -> CleaneyeInstitution | None:
        if search_result is None or not search_result.institutions:
            return None
        if institution_id:
            for institution in search_result.institutions:
                if institution.id == institution_id:
                    return institution
        if keyword:
            for institution in search_result.institutions:
                if institution.name == keyword:
                    return institution
        return search_result.institutions[0]

    @staticmethod
    def _search_request(keyword: str | None, kind: CleaneyeInstitutionKind) -> CollectorRequest:
        if kind == "local_public_enterprise":
            return CollectorRequest(
                method="POST",
                url=CleaneyeClient._absolute_url(CleaneyeClient.PUBLIC_SEARCH_PATH),
                endpoint=CleaneyeClient.PUBLIC_SEARCH_PATH,
                body={"entName": keyword, "entKind": ""},
            )
        return CollectorRequest(
            method="POST",
            url=CleaneyeClient._absolute_url(CleaneyeClient.INVESTED_SEARCH_PATH),
            endpoint=CleaneyeClient.INVESTED_SEARCH_PATH,
            body={"insttNm": keyword, "iptEntKind": "", "entGubun": ""},
        )

    @staticmethod
    def _to_kind(value: Any) -> CleaneyeInstitutionKind:
        text = CleaneyeCollector._to_text(value)
        if text in {"local_invested_contributed", "invested", "contributed", "ipt"}:
            return "local_invested_contributed"
        return "local_public_enterprise"

    @staticmethod
    def _sample_id(value: str | None, suffix: str) -> str:
        return f"{value or 'unknown'}-{suffix}"

    @staticmethod
    def _to_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
