"""Raw collector for ALIO management disclosure data."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kr_gov_job_mcp.clients.alio_disclosure_client import (
    AlioDisclosureClient,
    AlioDisclosureClientError,
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
    AlioPointKind,
    AlioReportDisclosure,
)


class AlioDisclosureCollector:
    """Collect raw ALIO institution, point, and disclosure report samples."""

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

        point_limit = self._to_int(query.get("point_limit"), default=5)
        include_report_html = self._to_bool(query.get("include_report_html"), default=True)

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

        point_name = institution.name or institution_name
        if point_name:
            for kind in ("national_assembly", "audit"):
                await self._collect_points(
                    result,
                    sample_store,
                    kind=kind,
                    institution_id=institution.id,
                    institution_name=point_name,
                    limit=point_limit,
                    collected_at=collected_at,
                )

        await self._collect_general_status(
            result,
            sample_store,
            institution=institution,
            institution_type=institution_type,
            include_report_html=include_report_html,
            collected_at=collected_at,
        )
        await self._collect_main_business(
            result,
            sample_store,
            institution=institution,
            include_report_html=include_report_html,
            collected_at=collected_at,
        )
        self._write_source_links(result, sample_store, institution, collected_at)

        result.notes.extend(
            [
                "Institution detail exposes general fields and main_business from ALIO contents.",
                "General status uses reportFormRootNo=10105; main business uses reportFormRootNo=31501.",
                "National assembly and audit points are available through reportFormNo B1210/B1220.",
            ]
        )
        return result

    async def _collect_points(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        *,
        kind: AlioPointKind,
        institution_id: str,
        institution_name: str,
        limit: int,
        collected_at: str,
    ) -> None:
        points = await self._try_step(
            result,
            f"{kind} points",
            self.client.list_point_items(
                kind=kind,
                institution_name=institution_name,
                page=1,
                limit=limit,
            ),
        )
        if not points:
            return

        result.normalized_count += len(points.items)
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="list",
                sample_id=self._sample_id(institution_id, f"{kind}-points"),
                payload=points.raw,
                request=CollectorRequest(
                    method="GET",
                    url=AlioDisclosureClient._absolute_url(AlioDisclosureClient.POINT_LIST_PATH),
                    endpoint=AlioDisclosureClient.POINT_LIST_PATH,
                    params={
                        "reportFormNo": AlioDisclosureClient.POINT_REPORT_FORM_NO[kind],
                        "countPerPage": limit,
                        "pageNo": 1,
                        "type": "apbaNa",
                        "word": institution_name,
                    },
                ),
                collected_at=collected_at,
                content_type="application/json",
                metadata={
                    "kind": kind,
                    "normalized_count": len(points.items),
                    "total_count": points.total_count,
                },
            ),
        )

    async def _collect_general_status(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        *,
        institution: AlioInstitution,
        institution_type: str | None,
        include_report_html: bool,
        collected_at: str,
    ) -> None:
        reports = await self._try_step(
            result,
            "general status reports",
            self.client.list_general_status_reports(
                institution_code=institution.id,
                institution_type=institution_type,
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
                sample_id=self._sample_id(institution.id, "general-status-reports"),
                payload=reports.raw,
                request=CollectorRequest(
                    method="POST",
                    url=AlioDisclosureClient._absolute_url(
                        AlioDisclosureClient.GENERAL_REPORT_LIST_PATH
                    ),
                    endpoint=AlioDisclosureClient.GENERAL_REPORT_LIST_PATH,
                    body={
                        "pageNo": 1,
                        "apbaId": institution.id,
                        "apbaType": institution_type,
                        "reportFormRootNo": AlioDisclosureClient.GENERAL_STATUS_REPORT_FORM_ROOT_NO,
                    },
                ),
                collected_at=collected_at,
                content_type="application/json",
                metadata={"normalized_count": len(reports.reports)},
            ),
        )
        await self._collect_report_payloads(
            result,
            sample_store,
            report=self._first_report_with_disclosure(reports.reports),
            sample_prefix="general-status",
            include_report_html=include_report_html,
            collected_at=collected_at,
        )

    async def _collect_main_business(
        self,
        result: CollectionResult,
        sample_store: RawSampleWriter,
        *,
        institution: AlioInstitution,
        include_report_html: bool,
        collected_at: str,
    ) -> None:
        reports = await self._try_step(
            result,
            "quarterly reports",
            self.client.list_quarterly_report_disclosures(institution_code=institution.id),
        )
        if not reports:
            return

        main_business = [
            report
            for report in reports.reports
            if report.report_form_no == AlioDisclosureClient.MAIN_BUSINESS_REPORT_FORM_ROOT_NO
        ]
        result.normalized_count += len(main_business)
        self._write_sample(
            result,
            sample_store,
            RawSample(
                source=self.name,
                raw_type="list",
                sample_id=self._sample_id(institution.id, "quarterly-report-list"),
                payload=reports.raw,
                request=CollectorRequest(
                    method="GET",
                    url=AlioDisclosureClient._absolute_url(AlioDisclosureClient.QUARTERLY_REPORT_PATH),
                    endpoint=AlioDisclosureClient.QUARTERLY_REPORT_PATH,
                    params={"apbaId": institution.id, "nowQuarter": 0},
                ),
                collected_at=collected_at,
                content_type="text/html",
                metadata={
                    "normalized_count": len(reports.reports),
                    "main_business_count": len(main_business),
                },
            ),
        )
        await self._collect_report_payloads(
            result,
            sample_store,
            report=self._first_report_with_disclosure(main_business),
            sample_prefix="main-business",
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
                    "general_status": AlioDisclosureClient.item_organ_list_url(
                        institution.id,
                        AlioDisclosureClient.GENERAL_STATUS_REPORT_FORM_ROOT_NO,
                    ),
                    "main_business": AlioDisclosureClient.item_report_term_url(
                        institution_code=institution.id,
                        report_form_root_no=AlioDisclosureClient.MAIN_BUSINESS_REPORT_FORM_ROOT_NO,
                    ),
                    "national_assembly_points": AlioDisclosureClient._absolute_url(
                        "/occasional/nationalAssemblyList.do"
                    ),
                    "audit_points": AlioDisclosureClient._absolute_url(
                        "/occasional/auditPointList.do"
                    ),
                },
                collected_at=collected_at,
                metadata={"institution_id": institution.id, "institution_name": institution.name},
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
    def _first_report_with_disclosure(
        reports: list[AlioReportDisclosure],
    ) -> AlioReportDisclosure | None:
        for report in reports:
            if report.disclosure_no:
                return report
        return None

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
