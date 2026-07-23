"""ALIO management disclosure web client."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlencode

import httpx

from kr_gov_job_mcp.schemas.alio import (
    AlioInstitution,
    AlioInstitutionSearchResult,
    AlioPointAttachment,
    AlioPointItem,
    AlioPointKind,
    AlioPointSearchResult,
    AlioReportDisclosure,
    AlioReportFile,
    AlioReportSearchResult,
)


class AlioDisclosureClientError(RuntimeError):
    """Raised when ALIO returns an unusable disclosure response."""


AlioDisclosureItemKind = Literal["regular", "occasional"]


@dataclass(frozen=True)
class AlioDisclosureItemConfig:
    """ALIO item report target verified from the institution disclosure page."""

    item_no: str
    name: str
    report_form_root_no: str
    kind: AlioDisclosureItemKind
    note: str | None = None


class AlioDisclosureClient:
    """Client for public ALIO management disclosure endpoints."""

    BASE_URL = "https://www.alio.go.kr"
    INSTITUTION_LIST_PATH = "/organ/findOrganApbaList.json"
    INSTITUTION_DETAIL_PATH = "/organ/findOrganApbaDtl.json"
    POINT_LIST_PATH = "/occasional/findPointList.json"
    OCCASIONAL_REPORT_LIST_PATH = "/item/itemReportListSusi.json"
    GENERAL_REPORT_LIST_PATH = OCCASIONAL_REPORT_LIST_PATH
    REGULAR_REPORT_LIST_PATH = "/item/itemOrganListJung.json"
    QUARTERLY_REPORT_PATH = "/organ/quarterlyReport.do"
    REPORT_FILES_PATH = "/item/itemReportFiles.json"
    REPORT_RIGHT_PATH = "/item/itemReportRight.do"

    GENERAL_STATUS_REPORT_FORM_ROOT_NO = "10105"
    MAIN_BUSINESS_REPORT_FORM_ROOT_NO = "31501"
    AVERAGE_SALARY_REPORT_FORM_ROOT_NO = "2060"
    POINT_REPORT_FORM_NO: dict[AlioPointKind, str] = {
        "national_assembly": "B1210",
    }
    POINT_DETAIL_PATH: dict[AlioPointKind, str] = {
        "national_assembly": "/occasional/nationalAssemblyDtl.do",
    }
    TARGET_ITEM_REPORTS: dict[str, AlioDisclosureItemConfig] = {
        "6-2": AlioDisclosureItemConfig(
            item_no="6-2",
            name="직원 채용정보",
            report_form_root_no="B1020",
            kind="occasional",
        ),
        "40": AlioDisclosureItemConfig(
            item_no="40",
            name="주요사업",
            report_form_root_no="31501",
            kind="regular",
        ),
        "47-1": AlioDisclosureItemConfig(
            item_no="47-1",
            name="국회지적사항",
            report_form_root_no="B1210",
            kind="occasional",
            note="47-2 감사원 지적사항과 47-3 주무부처 지적사항은 수집 범위에서 제외한다.",
        ),
        "49-1": AlioDisclosureItemConfig(
            item_no="49-1",
            name="입찰공고",
            report_form_root_no="B1030",
            kind="occasional",
        ),
        "49-2": AlioDisclosureItemConfig(
            item_no="49-2",
            name="수의계약",
            report_form_root_no="7030",
            kind="regular",
        ),
        "50-1": AlioDisclosureItemConfig(
            item_no="50-1",
            name="자체 연구 보고서",
            report_form_root_no="B1040",
            kind="occasional",
        ),
        "50-2": AlioDisclosureItemConfig(
            item_no="50-2",
            name="외부용역 연구 보고서",
            report_form_root_no="B1260",
            kind="occasional",
        ),
    }
    DEFAULT_TARGET_ITEM_NOS = ("6-2", "40", "47-1", "49-1", "49-2", "50-1", "50-2")
    TARGET_ITEM_GROUPS = {
        "47": ("47-1",),
        "49": ("49-1", "49-2"),
        "50": ("50-1", "50-2"),
    }
    REPORT_LIST_RE = re.compile(
        r"reportList:\s*JSON\.parse\('(?P<payload>(?:\\'|[^'])*)'\)",
        re.DOTALL,
    )

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126 Safari/537.36 kr-gov-job-mcp/0.1"
                ),
                "X-Requested-With": "XMLHttpRequest",
            },
        )

    async def __aenter__(self) -> AlioDisclosureClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search_institutions(
        self,
        *,
        keyword: str | None = None,
        institution_code: str | None = None,
        page: int = 1,
    ) -> AlioInstitutionSearchResult:
        """Search ALIO public institutions by name or ALIO institution id."""

        data = await self._post_json(
            self.INSTITUTION_LIST_PATH,
            self._clean_form(
                {
                    "apbaNa": keyword,
                    "apba_id": institution_code,
                    "pageNo": page,
                }
            ),
            referer="/guide/publicAgencyList.do",
        )
        organ_list = self._expect_mapping(data.get("organList"), "organList")
        rows = organ_list.get("result") or []
        if not isinstance(rows, list):
            raise AlioDisclosureClientError("ALIO institution list result was not a list")

        page_info = organ_list.get("page") if isinstance(organ_list.get("page"), dict) else {}
        return AlioInstitutionSearchResult(
            page=page,
            total_count=self._to_int(page_info.get("totalCount")) or len(rows),
            institutions=[
                self.normalize_institution(row) for row in rows if isinstance(row, dict)
            ],
            raw=dict(data),
        )

    async def fetch_institution_detail(self, institution_code: str) -> AlioInstitution:
        """Fetch an ALIO institution detail by apbaId."""

        data = await self._get_json(
            self.INSTITUTION_DETAIL_PATH,
            {"apbaId": institution_code},
            referer=f"/organ/organDisclosureDtl.do?apbaId={institution_code}",
        )
        if not isinstance(data, dict):
            raise AlioDisclosureClientError("ALIO institution detail was not an object")
        return self.normalize_institution(data)

    async def list_point_items(
        self,
        *,
        kind: AlioPointKind,
        institution_name: str | None = None,
        keyword: str | None = None,
        keyword_type: str = "apbaNa",
        page: int = 1,
        limit: int = 8,
        sort_type: str | None = None,
    ) -> AlioPointSearchResult:
        """Fetch national assembly or audit/inspection point items."""

        word = institution_name if institution_name is not None else keyword
        data = await self._get_json(
            self.POINT_LIST_PATH,
            self._clean_form(
                {
                    "reportFormNo": self.POINT_REPORT_FORM_NO[kind],
                    "countPerPage": limit,
                    "pageNo": page,
                    "type": keyword_type,
                    "word": word,
                    "sortType": sort_type,
                }
            ),
            referer=self._point_list_referer(kind),
        )
        rows = data.get("result") or []
        if not isinstance(rows, list):
            raise AlioDisclosureClientError("ALIO point list result was not a list")

        return AlioPointSearchResult(
            kind=kind,
            page=page,
            limit=limit,
            total_count=self._to_int(data.get("totalCnt")) or len(rows),
            items=[self.normalize_point(row, kind=kind) for row in rows if isinstance(row, dict)],
            raw=dict(data),
        )

    async def list_general_status_reports(
        self,
        *,
        institution_code: str,
        institution_type: str | None = None,
        page: int = 1,
    ) -> AlioReportSearchResult:
        """Fetch the report list for the ALIO general status item."""

        data = await self._post_json(
            self.GENERAL_REPORT_LIST_PATH,
            self._clean_form(
                {
                    "pageNo": page,
                    "apbaId": institution_code,
                    "apbaType": institution_type,
                    "reportFormRootNo": self.GENERAL_STATUS_REPORT_FORM_ROOT_NO,
                    "search_word": "",
                    "search_flag": "title",
                    "bid_type": "",
                    "enfc_istt": "",
                }
            ),
            referer=self.item_organ_list_url(
                institution_code,
                self.GENERAL_STATUS_REPORT_FORM_ROOT_NO,
                absolute=False,
            ),
        )
        rows = data.get("result") or []
        if not isinstance(rows, list):
            raise AlioDisclosureClientError("ALIO general status report result was not a list")
        page_info = data.get("page") if isinstance(data.get("page"), dict) else {}

        return AlioReportSearchResult(
            report_form_root_no=self.GENERAL_STATUS_REPORT_FORM_ROOT_NO,
            page=page,
            total_count=self._to_int(page_info.get("totalCount")) or len(rows),
            reports=[
                self.normalize_report_disclosure(row, source_url=self.item_report_url(row))
                for row in rows
                if isinstance(row, dict)
            ],
            raw=dict(data),
        )

    async def list_regular_item_reports(
        self,
        *,
        institution_code: str,
        report_form_root_no: str,
    ) -> AlioReportSearchResult:
        """Fetch an ALIO regular item report list for one institution."""

        data = await self._post_json(
            self.REGULAR_REPORT_LIST_PATH,
            {
                "apbaType": [],
                "jidtDptm": [],
                "area": [],
                "apbaId": institution_code,
                "reportFormRootNo": report_form_root_no,
                "quart": "",
            },
            referer=self.item_organ_list_url(
                institution_code,
                report_form_root_no,
                absolute=False,
            ),
        )
        rows = data.get("organList") or []
        if not isinstance(rows, list):
            raise AlioDisclosureClientError("ALIO regular item organList was not a list")

        return AlioReportSearchResult(
            report_form_root_no=report_form_root_no,
            total_count=self._to_int(data.get("totalCnt")) or len(rows),
            reports=[
                self.normalize_report_disclosure(row, source_url=self.item_report_url(row))
                for row in rows
                if isinstance(row, dict)
            ],
            raw=dict(data),
        )

    async def list_occasional_item_reports(
        self,
        *,
        institution_code: str,
        report_form_root_no: str,
        institution_type: str | None = None,
        page: int = 1,
        keyword: str = "",
        keyword_type: str = "title",
    ) -> AlioReportSearchResult:
        """Fetch an ALIO occasional item board/report list for one institution."""

        _report_root, enforcement = self._split_report_form_root(report_form_root_no)
        data = await self._post_json(
            self.OCCASIONAL_REPORT_LIST_PATH,
            self._clean_form(
                {
                    "pageNo": page,
                    "apbaId": institution_code,
                    "apbaType": institution_type,
                    "reportFormRootNo": report_form_root_no,
                    "search_word": keyword,
                    "search_flag": keyword_type,
                    "bid_type": "",
                    "enfc_istt": enforcement,
                }
            ),
            referer=self.item_organ_list_url(
                institution_code,
                report_form_root_no,
                absolute=False,
            ),
        )
        rows = data.get("result") or []
        if not isinstance(rows, list):
            raise AlioDisclosureClientError("ALIO occasional item result was not a list")
        page_info = data.get("page") if isinstance(data.get("page"), dict) else {}

        return AlioReportSearchResult(
            report_form_root_no=report_form_root_no,
            page=page,
            total_count=self._to_int(page_info.get("totalCount")) or len(rows),
            reports=[
                self.normalize_report_disclosure(row, source_url=self.item_board_url(row))
                for row in rows
                if isinstance(row, dict)
            ],
            raw=dict(data),
        )

    async def list_item_reports(
        self,
        *,
        institution_code: str,
        item: AlioDisclosureItemConfig,
        institution_type: str | None = None,
        page: int = 1,
    ) -> AlioReportSearchResult:
        """Fetch the list for a verified ALIO item report target."""

        if item.kind == "regular":
            return await self.list_regular_item_reports(
                institution_code=institution_code,
                report_form_root_no=item.report_form_root_no,
            )
        return await self.list_occasional_item_reports(
            institution_code=institution_code,
            report_form_root_no=item.report_form_root_no,
            institution_type=institution_type,
            page=page,
        )

    async def list_quarterly_report_disclosures(
        self,
        *,
        institution_code: str,
        quarter: int = 0,
    ) -> AlioReportSearchResult:
        """Fetch regular report disclosures from the quarterly report page."""

        html = await self._get_text(
            self.QUARTERLY_REPORT_PATH,
            {"apbaId": institution_code, "nowQuarter": quarter},
            referer=f"/organ/organDisclosureDtl.do?apbaId={institution_code}",
        )
        rows = self.extract_quarterly_report_rows(html)
        reports = [
            self.normalize_report_disclosure(
                row,
                source_url=self.item_report_term_url(
                    institution_code=institution_code,
                    report_form_root_no=self._to_text(row.get("reportFormNo")) or "",
                    disclosure_no=self._to_text(row.get("disclosureNo")),
                ),
            )
            for row in rows
            if isinstance(row, dict)
        ]
        return AlioReportSearchResult(
            report_form_root_no="quarterly",
            reports=reports,
            total_count=len(reports),
            raw={"html": html, "reportList": rows},
        )

    async def fetch_report_files(self, disclosure_no: str) -> list[AlioReportFile]:
        """Fetch files attached to a disclosure report."""

        data = await self._get_json(
            self.REPORT_FILES_PATH,
            {"disclosureNo": disclosure_no},
            referer=f"/item/itemReport.do?seq={disclosure_no}&disclosureNo={disclosure_no}",
        )
        if not isinstance(data, list):
            raise AlioDisclosureClientError("ALIO report files response was not a list")
        return [
            self.normalize_report_file(row)
            for row in data
            if isinstance(row, dict) and self._to_text(row.get("fileNo"))
        ]

    async def fetch_report_html(self, disclosure_no: str) -> str:
        """Fetch the HTML body for a disclosure report."""

        return await self._get_text(
            self.REPORT_RIGHT_PATH,
            {"disclosureNo": disclosure_no},
            referer=f"/item/itemReport.do?seq={disclosure_no}&disclosureNo={disclosure_no}",
            accept="text/html, */*; q=0.01",
        )

    async def fetch_board_report_html(self, report: AlioReportDisclosure) -> str:
        """Fetch the HTML detail page for an ALIO occasional board item."""

        report_form_no = self._to_text(report.raw.get("reportFormNo") or report.report_form_no)
        if not report_form_no:
            raise AlioDisclosureClientError("ALIO board report had no reportFormNo")
        params = self.item_board_params(report.raw)
        return await self._get_text(
            f"/item/itemBoard{report_form_no}.do",
            params,
            referer=self.item_organ_list_url(
                report.institution_id or self._to_text(report.raw.get("apbaId")) or "",
                report_form_no,
                absolute=False,
            ),
            accept="text/html, */*; q=0.01",
        )

    @classmethod
    def extract_quarterly_report_rows(cls, html: str) -> list[dict[str, Any]]:
        """Extract the server-rendered reportList JSON embedded in quarterlyReport.do."""

        match = cls.REPORT_LIST_RE.search(html)
        if not match:
            raise AlioDisclosureClientError("ALIO quarterly report page did not include reportList")

        json_text = match.group("payload").replace("\\'", "'").replace("\\/", "/")
        try:
            rows = json.loads(json_text)
        except ValueError as exc:
            raise AlioDisclosureClientError("ALIO quarterly reportList was not valid JSON") from exc

        if not isinstance(rows, list):
            raise AlioDisclosureClientError("ALIO quarterly reportList was not a list")
        return [row for row in rows if isinstance(row, dict)]

    @classmethod
    def normalize_institution(cls, raw: Mapping[str, Any]) -> AlioInstitution:
        institution_code = cls._to_text(raw.get("apbaId")) or ""
        return AlioInstitution(
            id=institution_code,
            name=cls._to_text(raw.get("apbaNa") or raw.get("dcsrApbaNa")),
            type_name=cls._to_text(raw.get("typeNa") or raw.get("apbaTypeNa")),
            ministry_name=cls._to_text(raw.get("jidtNa") or raw.get("jidtDptmNa") or raw.get("cd")),
            ceo=cls._to_text(raw.get("ceo")),
            established_date=cls._to_date(raw.get("fdate")),
            region=cls._to_text(raw.get("addrCd")),
            address=cls._to_text(raw.get("addr1")),
            homepage_url=cls._normalize_url(raw.get("homepage")),
            main_business=cls._normalize_multiline(raw.get("contents")),
            disclosure_start_date=cls._to_date(raw.get("reportFormUseStrtDt")),
            submission_no=cls._to_text(raw.get("submissionNo")),
            source_url=cls.institution_detail_url(institution_code) if institution_code else None,
            raw=dict(raw),
        )

    @classmethod
    def normalize_point(cls, raw: Mapping[str, Any], *, kind: AlioPointKind) -> AlioPointItem:
        point_id = cls._to_text(raw.get("submissionNo")) or ""
        detail_path = cls.POINT_DETAIL_PATH[kind]
        return AlioPointItem(
            id=point_id,
            kind=kind,
            report_form_no=cls._to_text(raw.get("reportFormNo")),
            institution_id=cls._to_text(raw.get("apbaId")),
            institution_name=cls._to_text(raw.get("apbaNa") or raw.get("pname")),
            title=cls._normalize_multiline(raw.get("rtitle")),
            registered_date=cls._to_date(raw.get("idate")),
            action_plan_date=cls._to_date(raw.get("pdate") or raw.get("actnPlanRegYmd")),
            action_result_date=cls._to_date(raw.get("rdate") or raw.get("actnResRegYmd")),
            enforcement_start_date=cls._to_date(raw.get("enfcBgngYmd")),
            enforcement_end_date=cls._to_date(raw.get("enfcEndYmd")),
            source_url=cls._absolute_url(f"{detail_path}?seq={point_id}") if point_id else None,
            attachments=cls._normalize_point_attachments(raw),
            raw=dict(raw),
        )

    @classmethod
    def normalize_report_disclosure(
        cls,
        raw: Mapping[str, Any],
        *,
        source_url: str | None = None,
    ) -> AlioReportDisclosure:
        disclosure_no = cls._to_text(raw.get("disclosureNo") or raw.get("seq")) or ""
        report_form_no = cls._to_text(raw.get("reportFormNo"))
        institution_id = cls._to_text(raw.get("apbaId"))
        submission_no = cls._to_text(raw.get("submissionNo"))
        report_kind = cls._to_text(raw.get("reportGbn") or raw.get("gbn"))
        if report_kind == "Y":
            report_kind = "susi_report"
        elif report_kind == "N":
            report_kind = "susi_board"
        elif report_kind == "1":
            report_kind = "regular_report"

        return AlioReportDisclosure(
            disclosure_no=disclosure_no,
            report_form_no=report_form_no,
            title=cls._to_text(raw.get("title") or raw.get("rtitle")),
            report_kind=report_kind,
            criterion_year=cls._to_int(raw.get("critYyyy")),
            disclosed_date=cls._to_date(raw.get("idate")),
            institution_id=institution_id,
            institution_name=cls._to_text(raw.get("pname") or raw.get("apbaNa")),
            submission_no=submission_no,
            source_url=source_url,
            attachments=cls.normalize_report_file_refs(
                raw.get("files"),
                disclosure_no=disclosure_no,
                report_form_no=report_form_no,
                institution_id=institution_id,
                submission_no=submission_no,
            ),
            raw=dict(raw),
        )

    @classmethod
    def normalize_report_file(cls, raw: Mapping[str, Any]) -> AlioReportFile:
        file_no = cls._to_text(raw.get("fileNo")) or ""
        disclosure_no = cls._to_text(raw.get("disclosureNo"))
        submission_no = cls._to_text(raw.get("submissionNo"))
        return AlioReportFile(
            file_no=file_no,
            disclosure_no=disclosure_no,
            report_form_no=cls._to_text(raw.get("reportFormNo")),
            institution_id=cls._to_text(raw.get("apbaId")),
            submission_no=submission_no,
            original_name=cls._to_text(raw.get("orcpFileNa") or raw.get("fileName")),
            save_name=cls._to_text(raw.get("saveFileNa")),
            save_path=cls._to_text(raw.get("savePath")),
            file_type=cls._to_text(raw.get("fileType")),
            file_size=cls._to_int(raw.get("fileSize")),
            download_url=cls.report_file_download_url(
                file_no=file_no,
                disclosure_no=disclosure_no,
                submission_no=submission_no,
            ),
            raw=dict(raw),
        )

    @classmethod
    def normalize_report_file_refs(
        cls,
        value: Any,
        *,
        disclosure_no: str | None = None,
        report_form_no: str | None = None,
        institution_id: str | None = None,
        submission_no: str | None = None,
    ) -> list[AlioReportFile]:
        text = cls._to_text(value)
        if not text:
            return []

        files: list[AlioReportFile] = []
        for entry in text.split("|"):
            entry = entry.strip()
            if not entry or entry == "@":
                continue
            file_no_text, separator, name_text = entry.partition("@")
            file_no = cls._to_text(file_no_text)
            if not file_no:
                continue
            original_name = cls._to_text(name_text) if separator else None
            files.append(
                AlioReportFile(
                    file_no=file_no,
                    disclosure_no=cls._to_text(disclosure_no),
                    report_form_no=cls._to_text(report_form_no),
                    institution_id=cls._to_text(institution_id),
                    submission_no=cls._to_text(submission_no),
                    original_name=original_name,
                    download_url=cls.report_file_download_url(
                        file_no=file_no,
                        disclosure_no=disclosure_no,
                        submission_no=submission_no,
                    ),
                    raw={"files": text, "entry": entry},
                )
            )
        return files

    @classmethod
    def report_file_download_url(
        cls,
        *,
        file_no: str | None,
        disclosure_no: str | None = None,
        submission_no: str | None = None,
    ) -> str | None:
        file_no = cls._to_text(file_no)
        if not file_no:
            return None
        query = cls._clean_form({"f": file_no, "d": disclosure_no, "s": submission_no})
        return cls._absolute_url(f"/download/file.json?{urlencode(query)}")

    @classmethod
    def item_report_url(cls, raw: Mapping[str, Any]) -> str | None:
        disclosure_no = cls._to_text(raw.get("disclosureNo") or raw.get("seq"))
        if not disclosure_no:
            return None
        return cls._absolute_url(
            f"/item/itemReport.do?seq={disclosure_no}&disclosureNo={disclosure_no}"
        )

    @classmethod
    def item_board_params(cls, raw: Mapping[str, Any]) -> dict[str, str]:
        report_form_no = cls._to_text(raw.get("reportFormNo")) or ""
        return cls._clean_form(
            {
                "disclosureNo": raw.get("disclosureNo"),
                "apbaId": raw.get("apbaId"),
                "nowcode": report_form_no,
                "reportFormNo": report_form_no,
                "table_name": raw.get("tableName"),
                "idx_name": raw.get("idxName"),
                "idx": raw.get("idx"),
                "reportGbn": raw.get("reportGbn") or "N",
                "bid_type": raw.get("bidType"),
            }
        )

    @classmethod
    def item_board_url(cls, raw: Mapping[str, Any]) -> str | None:
        report_form_no = cls._to_text(raw.get("reportFormNo"))
        if not report_form_no:
            return None
        query = urlencode(cls.item_board_params(raw))
        return cls._absolute_url(f"/item/itemBoard{report_form_no}.do?{query}")

    @classmethod
    def item_organ_list_url(
        cls,
        institution_code: str,
        report_form_root_no: str,
        *,
        absolute: bool = True,
    ) -> str:
        path = (
            f"/item/itemOrganList.do?apbaId={institution_code}"
            f"&reportFormRootNo={report_form_root_no}"
        )
        return cls._absolute_url(path) if absolute else path

    @classmethod
    def item_report_term_url(
        cls,
        *,
        institution_code: str,
        report_form_root_no: str,
        disclosure_no: str | None = None,
    ) -> str:
        query = urlencode(
            cls._clean_form(
                {
                    "apbaId": institution_code,
                    "reportFormRootNo": report_form_root_no,
                    "disclosureNo": disclosure_no,
                }
            )
        )
        return cls._absolute_url(f"/item/itemReportTerm.do?{query}")

    @classmethod
    def institution_detail_url(cls, institution_code: str) -> str:
        return cls._absolute_url(f"/organ/organDisclosureDtl.do?apbaId={institution_code}")

    async def _get_json(
        self,
        path: str,
        params: Mapping[str, Any],
        *,
        referer: str,
    ) -> Any:
        response = await self._request("GET", path, params=params, referer=referer)
        return self._json_data(response)

    async def _post_json(
        self,
        path: str,
        body: Mapping[str, Any],
        *,
        referer: str,
    ) -> Any:
        response = await self._request("POST", path, json=body, referer=referer)
        return self._json_data(response)

    async def _get_text(
        self,
        path: str,
        params: Mapping[str, Any],
        *,
        referer: str,
        accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    ) -> str:
        response = await self._request(
            "GET",
            path,
            params=params,
            referer=referer,
            headers={"Accept": accept},
        )
        return response.text

    async def _request(
        self,
        method: str,
        path: str,
        *,
        referer: str,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        request_headers = {"Referer": self._absolute_url(referer)}
        if json is not None:
            request_headers["Content-Type"] = "application/json;charset=UTF-8"
        if headers:
            request_headers.update(headers)

        try:
            response = await self._client.request(
                method,
                self._absolute_url(path),
                params=params,
                json=json,
                headers=request_headers,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AlioDisclosureClientError(f"ALIO request failed: {exc}") from exc
        return response

    @classmethod
    def _json_data(cls, response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError as exc:
            raise AlioDisclosureClientError("ALIO response was not JSON") from exc

        if not isinstance(payload, dict):
            raise AlioDisclosureClientError("ALIO response root was not an object")

        status = cls._to_text(payload.get("status"))
        if status and status != "success":
            message = payload.get("message") or "unknown error"
            raise AlioDisclosureClientError(f"ALIO returned status={status}: {message}")
        return payload.get("data")

    @staticmethod
    def _expect_mapping(value: Any, name: str) -> Mapping[str, Any]:
        if not isinstance(value, dict):
            raise AlioDisclosureClientError(f"ALIO response did not contain {name}")
        return value

    @classmethod
    def _normalize_point_attachments(cls, raw: Mapping[str, Any]) -> list[AlioPointAttachment]:
        attachments: list[AlioPointAttachment] = []
        for slot in ("filedata1", "filedata2", "filedata3"):
            text = cls._to_text(raw.get(slot))
            if not text:
                continue
            parts = text.split("**")
            if len(parts) < 5:
                attachments.append(AlioPointAttachment(slot=slot, raw=text))
                continue
            save_path = cls._to_text(parts[3])
            save_name = cls._to_text(parts[1])
            original_name = cls._to_text(parts[2])
            query = cls._clean_form(
                {
                    "spath": save_path,
                    "sfile": save_name,
                    "dfile": original_name,
                }
            )
            attachments.append(
                AlioPointAttachment(
                    slot=slot,
                    save_name=save_name,
                    original_name=original_name,
                    save_path=save_path,
                    submission_no=cls._to_text(parts[4]),
                    download_url=cls._absolute_url(f"/download/pfile.json?{urlencode(query)}"),
                )
            )
        return attachments

    @classmethod
    def _point_list_referer(cls, kind: AlioPointKind) -> str:
        return "/occasional/nationalAssemblyList.do"

    @staticmethod
    def _split_report_form_root(report_form_root_no: str) -> tuple[str, str | None]:
        if "-" not in report_form_root_no:
            return report_form_root_no, None
        report_root, enforcement = report_form_root_no.split("-", 1)
        return report_root, enforcement or None

    @classmethod
    def _absolute_url(cls, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        if path_or_url.startswith("//"):
            return f"https:{path_or_url}"
        if not path_or_url.startswith("/"):
            path_or_url = f"/{path_or_url}"
        return f"{cls.BASE_URL}{path_or_url}"

    @staticmethod
    def _clean_form(form: Mapping[str, Any]) -> dict[str, str]:
        return {
            key: str(value)
            for key, value in form.items()
            if value is not None and str(value).strip() != ""
        }

    @staticmethod
    def _normalize_url(value: Any) -> str | None:
        text = AlioDisclosureClient._to_text(value)
        if not text:
            return None
        if text.startswith(("http://", "https://")):
            return text
        return f"https://{text}"

    @staticmethod
    def _normalize_multiline(value: Any) -> str | None:
        text = AlioDisclosureClient._to_text(value)
        if not text:
            return None
        text = text.replace("&cr;", "\n").replace("\r\n", "\n").replace("\r", "\n")
        return "\n".join(line.strip() for line in text.split("\n") if line.strip())

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
            return int(str(value).replace(",", "").strip())
        except ValueError:
            return None

    @staticmethod
    def _to_date(value: Any) -> str | None:
        text = AlioDisclosureClient._to_text(value)
        if not text:
            return None
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) == 8:
            return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
        return text
