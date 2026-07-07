"""Raw collector for ALIO management disclosure data."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kr_gov_job_mcp.clients.alio_disclosure_client import (
    AlioDisclosureClient,
    AlioDisclosureClientError,
    AlioDisclosureItemConfig,
)
from kr_gov_job_mcp.collectors.base import (
    CollectionResult,
    CollectorHttpPolicy,
    CollectorRequest,
    RawSample,
    RawSampleWriter,
    utc_now_text,
)
from kr_gov_job_mcp.schemas.alio import (
    AlioInstitution,
    AlioInstitutionSearchResult,
    AlioReportDisclosure,
)


class AlioDisclosureCollector:
    """Collect raw ALIO institution and item report samples."""

    name = "alio_disclosure"

    def __init__(
        self,
        client: AlioDisclosureClient | None = None,
        http_policy: CollectorHttpPolicy | None = None,
    ) -> None:
        self.client = client or AlioDisclosureClient()
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
            run_id=f"alio-disclosure-{collected_at}",
            collected_at=collected_at,
        )

        institution_name = self._to_text(
            query.get("institution_name") or query.get("name") or query.get("keyword")
        )
        institution_code = self._to_text(
            query.get("institution_code") or query.get("apbaId") or query.get("apba_id")
        )
        if not institution_name and not institution_code:
            result.errors.append("institution_name or institution_code is required")
            return result

        include_report_html = self._to_bool(query.get("include_report_html"), default=True)
        target_item_numbers, invalid_item_numbers = self._target_item_numbers(
            query.get("item_numbers")
        )
        if invalid_item_numbers:
            result.errors.append(
                "unknown ALIO item_numbers: " + ", ".join(invalid_item_numbers)
            )
            return result

        search_result: AlioInstitutionSearchResult | None = None
        selected: AlioInstitution | None = None
        institution_type: str | None = None

        if institution_name or institution_code:
            search_result = await self._try_step(
                result,
                "institution search",
                self.client.search_institutions(
                    keyword=institution_name,
                    institution_code=institution_code,
                    page=1,
                ),
            )
            if search_result:
                selected = self._select_institution(search_result, institution_name, institution_code)
                institution_type = self._to_text(selected.raw.get("apbaType")) if selected else None
                self._write_sample(
                    result,
                    sample_store,
                    RawSample(
                        source=self.name,
                        raw_type="list",
                        sample_id=self._sample_id(
                            selected.id if selected else institution_code or institution_name,
                            "search",
                        ),
                        payload=search_result.raw,
                        request=CollectorRequest(
                            method="POST",
                            url=AlioDisclosureClient._absolute_url(
                                AlioDisclosureClient.INSTITUTION_LIST_PATH
                            ),
                            endpoint=AlioDisclosureClient.INSTITUTION_LIST_PATH,
                            body={
                                "apbaNa": institution_name,
                                "apba_id": institution_code,
                                "pageNo": 1,
                            },
                        ),
                        collected_at=collected_at,
                        content_type="application/json",
                        metadata={
                            "normalized_count": len(search_result.institutions),
                            "selected_institution_id": selected.id if selected else None,
                        },
                    ),
                )

        detail: AlioInstitution | None = None
        target_code = institution_code or (selected.id if selected else None)
        if target_code:
            detail = await self._try_step(
                result,
                "institution detail",
                self.client.fetch_institution_detail(target_code),
            )
            if detail:
                self._write_sample(
                    result,
                    sample_store,
                    RawSample(
                        source=self.name,
                        raw_type="detail",
                        sample_id=self._sample_id(detail.id, "institution-detail"),
                        payload=detail.raw,
                        request=CollectorRequest(
                            method="GET",
                            url=AlioDisclosureClient._absolute_url(
                                AlioDisclosureClient.INSTITUTION_DETAIL_PATH
                            ),
                            endpoint=AlioDisclosureClient.INSTITUTION_DETAIL_PATH,
                            params={"apbaId": detail.id},
                        ),
                        collected_at=collected_at,
                        content_type="application/json",
                        metadata=detail.model_dump(exclude={"raw"}),
                    ),
                )
                result.normalized_count += 1
        else:
            result.errors.append("ALIO institution search returned no usable institution id")
            return result

        institution = detail or selected
        if not institution:
            result.errors.append("ALIO institution detail could not be resolved")
            return result

        for item_number in target_item_numbers:
            item = AlioDisclosureClient.TARGET_ITEM_REPORTS[item_number]
            await self._collect_item_report(
                result,
                sample_store,
                institution=institution,
                institution_type=institution_type,
                item=item,
                include_report_html=include_report_html,
                collected_at=collected_at,
            )

        self._write_source_links(result, sample_store, institution, collected_at)

        result.notes.extend(
            [
                "Institution detail exposes general fields and main_business from ALIO contents.",
                "ALIO target item reports are collected from itemOrganList.do verified on the institution page.",
                "47-2 audit and 47-3 ministry point items are intentionally excluded.",
            ]
        )
        return result

    async def _collect_item_report(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        *,
        institution: AlioInstitution,
        institution_type: str | None,
        item: AlioDisclosureItemConfig,
        include_report_html: bool,
        collected_at: str,
    ) -> None:
        reports = await self._try_step(
            result,
            f"ALIO item {item.item_no} {item.name}",
            self.client.list_item_reports(
                institution_code=institution.id,
                institution_type=institution_type,
                item=item,
            ),
        )
        if not reports:
            return

        result.normalized_count += len(reports.reports)
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="list",
                sample_id=self._sample_id(
                    institution.id,
                    f"item-{item.item_no}-{item.report_form_root_no}-reports",
                ),
                payload=reports.raw,
                request=CollectorRequest(
                    method="POST",
                    url=AlioDisclosureClient._absolute_url(
                        AlioDisclosureClient.REGULAR_REPORT_LIST_PATH
                        if item.kind == "regular"
                        else AlioDisclosureClient.OCCASIONAL_REPORT_LIST_PATH
                    ),
                    endpoint=(
                        AlioDisclosureClient.REGULAR_REPORT_LIST_PATH
                        if item.kind == "regular"
                        else AlioDisclosureClient.OCCASIONAL_REPORT_LIST_PATH
                    ),
                    body=self._item_report_request_body(
                        institution=institution,
                        institution_type=institution_type,
                        item=item,
                    ),
                ),
                collected_at=collected_at,
                content_type="application/json",
                metadata={
                    "item_no": item.item_no,
                    "item_name": item.name,
                    "report_form_root_no": item.report_form_root_no,
                    "kind": item.kind,
                    "normalized_count": len(reports.reports),
                    "total_count": reports.total_count,
                    "note": item.note,
                },
            ),
        )
        first_report = self._first_report_for_payload(reports.reports)
        sample_prefix = f"item-{item.item_no}-{item.report_form_root_no}"
        if item.kind == "regular":
            await self._collect_report_payloads(
                result,
                sample_store,
                report=first_report,
                sample_prefix=sample_prefix,
                include_report_html=include_report_html,
                collected_at=collected_at,
            )
        else:
            await self._collect_board_payload(
                result,
                sample_store,
                report=first_report,
                sample_prefix=sample_prefix,
                include_report_html=include_report_html,
                collected_at=collected_at,
            )

    async def _collect_report_payloads(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        *,
        report: AlioReportDisclosure | None,
        sample_prefix: str,
        include_report_html: bool,
        collected_at: str,
    ) -> None:
        if not report or not report.disclosure_no:
            result.notes.append(f"{sample_prefix} report had no disclosureNo")
            return

        files = await self._try_step(
            result,
            f"{sample_prefix} files",
            self.client.fetch_report_files(report.disclosure_no),
        )
        if files is not None:
            self._write_sample(
                result,
                sample_store,
                RawSample(
                    source=self.name,
                    raw_type="attachment",
                    sample_id=self._sample_id(report.disclosure_no, f"{sample_prefix}-files"),
                    payload=[file.raw for file in files],
                    request=CollectorRequest(
                        method="GET",
                        url=AlioDisclosureClient._absolute_url(
                            AlioDisclosureClient.REPORT_FILES_PATH
                        ),
                        endpoint=AlioDisclosureClient.REPORT_FILES_PATH,
                        params={"disclosureNo": report.disclosure_no},
                    ),
                    collected_at=collected_at,
                    content_type="application/json",
                    metadata={
                        "report": report.model_dump(exclude={"raw"}),
                        "normalized_count": len(files),
                    },
                ),
            )

        if not include_report_html:
            return
        html = await self._try_step(
            result,
            f"{sample_prefix} html",
            self.client.fetch_report_html(report.disclosure_no),
        )
        if html is not None:
            self._write_sample(
                result,
                sample_store,
                RawSample(
                    source=self.name,
                    raw_type="html",
                    sample_id=self._sample_id(report.disclosure_no, f"{sample_prefix}-html"),
                    payload=html,
                    request=CollectorRequest(
                        method="GET",
                        url=AlioDisclosureClient._absolute_url(AlioDisclosureClient.REPORT_RIGHT_PATH),
                        endpoint=AlioDisclosureClient.REPORT_RIGHT_PATH,
                        params={"disclosureNo": report.disclosure_no},
                    ),
                    collected_at=collected_at,
                    content_type="text/html",
                    metadata={"report": report.model_dump(exclude={"raw"})},
                ),
            )

    async def _collect_board_payload(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        *,
        report: AlioReportDisclosure | None,
        sample_prefix: str,
        include_report_html: bool,
        collected_at: str,
    ) -> None:
        if not report:
            result.notes.append(f"{sample_prefix} report list had no rows")
            return
        if not include_report_html:
            return

        html = await self._try_step(
            result,
            f"{sample_prefix} board html",
            self.client.fetch_board_report_html(report),
        )
        if html is None:
            return

        report_form_no = self._to_text(report.raw.get("reportFormNo") or report.report_form_no)
        board_path = f"/item/itemBoard{report_form_no}.do" if report_form_no else "/item/itemBoard.do"
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="html",
                sample_id=self._sample_id(
                    self._report_sample_key(report),
                    f"{sample_prefix}-board-html",
                ),
                payload=html,
                request=CollectorRequest(
                    method="GET",
                    url=AlioDisclosureClient._absolute_url(board_path),
                    endpoint=board_path,
                    params=AlioDisclosureClient.item_board_params(report.raw),
                ),
                collected_at=collected_at,
                content_type="text/html",
                metadata={"report": report.model_dump(exclude={"raw"})},
            ),
        )

    def _write_source_links(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        institution: AlioInstitution,
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
                    "institution_detail": AlioDisclosureClient.institution_detail_url(institution.id),
                    "item_reports": {
                        item_no: {
                            "item_name": item.name,
                            "report_form_root_no": item.report_form_root_no,
                            "kind": item.kind,
                            "url": AlioDisclosureClient.item_organ_list_url(
                                institution.id,
                                item.report_form_root_no,
                            ),
                        }
                        for item_no, item in AlioDisclosureClient.TARGET_ITEM_REPORTS.items()
                    },
                    "excluded_item_reports": {
                        "47-2": "감사원 지적사항",
                        "47-3": "주무부처 지적사항",
                    },
                },
                collected_at=collected_at,
                metadata={"institution_id": institution.id, "institution_name": institution.name},
            ),
        )

    @staticmethod
    def _item_report_request_body(
        *,
        institution: AlioInstitution,
        institution_type: str | None,
        item: AlioDisclosureItemConfig,
    ) -> dict[str, Any]:
        if item.kind == "regular":
            return {
                "apbaType": [],
                "jidtDptm": [],
                "area": [],
                "apbaId": institution.id,
                "reportFormRootNo": item.report_form_root_no,
                "quart": "",
            }
        return {
            "pageNo": 1,
            "apbaId": institution.id,
            "apbaType": institution_type,
            "reportFormRootNo": item.report_form_root_no,
            "search_word": "",
            "search_flag": "title",
            "bid_type": "",
            "enfc_istt": "",
        }

    def _write_sample(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        sample: RawSample,
    ) -> Path:
        path = sample_store.write_sample(sample)
        result.raw_sample_paths.append(path)
        return path

    async def _try_step(
        self,
        result: CollectionResult,
        label: str,
        awaitable: Any,
    ) -> Any | None:
        try:
            return await awaitable
        except AlioDisclosureClientError as exc:
            result.errors.append(f"{label}: {exc}")
            return None

    @staticmethod
    def _select_institution(
        search_result: AlioInstitutionSearchResult,
        institution_name: str | None,
        institution_code: str | None,
    ) -> AlioInstitution | None:
        if not search_result.institutions:
            return None
        if institution_code:
            for institution in search_result.institutions:
                if institution.id == institution_code:
                    return institution
        if institution_name:
            for institution in search_result.institutions:
                if institution.name == institution_name:
                    return institution
        return search_result.institutions[0]

    @staticmethod
    def _first_report_for_payload(
        reports: list[AlioReportDisclosure],
    ) -> AlioReportDisclosure | None:
        for report in reports:
            if report.disclosure_no or report.source_url:
                return report
        return None

    @classmethod
    def _report_sample_key(cls, report: AlioReportDisclosure) -> str | None:
        if report.disclosure_no and set(report.disclosure_no) != {"0"}:
            return report.disclosure_no
        return cls._to_text(
            report.raw.get("idx") or report.raw.get("submissionNo") or report.disclosure_no
        )

    @classmethod
    def _target_item_numbers(cls, value: Any) -> tuple[list[str], list[str]]:
        if value is None:
            return list(AlioDisclosureClient.DEFAULT_TARGET_ITEM_NOS), []
        if isinstance(value, str):
            raw_values = [part.strip() for part in value.split(",")]
        else:
            try:
                raw_values = [str(part).strip() for part in value]
            except TypeError:
                raw_values = [str(value).strip()]

        item_numbers: list[str] = []
        invalid: list[str] = []
        for raw in raw_values:
            if not raw:
                continue
            expanded = AlioDisclosureClient.TARGET_ITEM_GROUPS.get(raw, (raw,))
            for item_number in expanded:
                if item_number not in AlioDisclosureClient.TARGET_ITEM_REPORTS:
                    invalid.append(item_number)
                    continue
                if item_number not in item_numbers:
                    item_numbers.append(item_number)
        return item_numbers, invalid

    @staticmethod
    def _sample_id(value: str | None, suffix: str) -> str:
        return f"{value or 'unknown'}-{suffix}"

    @staticmethod
    def _to_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _to_int(value: Any, *, default: int) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_bool(value: Any, *, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "y", "yes"}
