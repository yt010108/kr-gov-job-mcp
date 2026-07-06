"""Job-ALIO public recruitment Ajax client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from kr_gov_job_mcp.schemas.job import (
    JobAlioAttachment,
    JobAlioDetail,
    JobAlioSearchResult,
    JobAlioStep,
    JobAlioSummary,
)


class JobAlioWebClientError(RuntimeError):
    """Raised when Job-ALIO returns an unusable response."""


class JobAlioWebClient:
    """Client for the public Job-ALIO recruitment search page Ajax endpoints."""

    LIST_URL = "https://opendata.alio.go.kr/new/odaApiMng/recrutInquiryAjaxList.do"
    DETAIL_URL = "https://opendata.alio.go.kr/new/odaApiMng/recrutInquiryAjaxDetail.do"
    REFERER = "https://opendata.alio.go.kr/new/odaApiMng/recrutInquiryList.do"
    SUCCESS_RESULT_CODES = {"0", "1", "00", "200"}

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
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": self.REFERER,
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "kr-gov-job-mcp/0.1",
            },
        )

    async def __aenter__(self) -> JobAlioWebClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search_jobs(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        limit: int = 20,
        ongoing_only: bool = True,
        institution_code: str | None = None,
        ncs_code: str | None = None,
        region_code: str | None = None,
        academic_condition_code: str | None = None,
        employment_type_code: str | None = None,
        recruitment_type: str | None = None,
        replacement_only: bool | None = None,
        announcement_start_date: str | None = None,
        announcement_end_date: str | None = None,
        institution_type: str | None = None,
        institution_classification: str | None = None,
    ) -> JobAlioSearchResult:
        """Search recruitment notices from the Job-ALIO public web endpoint."""

        form = self._clean_form(
            {
                "pageNo": page,
                "numOfRows": limit,
                "recrutPbancTtl": keyword,
                "pblntInstCd": institution_code,
                "ncsCdLst": ncs_code,
                "workRgnLst": region_code,
                "acbgCondLst": academic_condition_code,
                "hireTypeLst": employment_type_code,
                "recrutSe": recruitment_type,
                "replmprYn": self._to_yn(replacement_only),
                "ongoingYn": "Y" if ongoing_only else None,
                "pbancBgngYmd": announcement_start_date,
                "pbancEndYmd": announcement_end_date,
                "instType": institution_type,
                "instClsf": institution_classification,
            }
        )
        payload = await self._post_form(self.LIST_URL, form)
        data = self._response_data(payload)
        rows = data.get("result") or []
        if not isinstance(rows, list):
            raise JobAlioWebClientError("Job-ALIO list response did not contain a result list")

        return JobAlioSearchResult(
            page=page,
            limit=limit,
            total_count=self._to_int(data.get("totalCount")) or len(rows),
            jobs=[self.normalize_summary(row) for row in rows if isinstance(row, dict)],
        )

    async def fetch_job_detail(self, recruitment_notice_sn: str | int) -> JobAlioDetail:
        """Fetch a recruitment notice detail by Job-ALIO notice serial number."""

        payload = await self._post_form(
            self.DETAIL_URL,
            {"sn": str(recruitment_notice_sn)},
        )
        data = self._response_data(payload)
        row = data.get("result")
        if not isinstance(row, dict):
            raise JobAlioWebClientError(
                f"Job-ALIO detail response did not contain result for sn={recruitment_notice_sn}"
            )
        return self.normalize_detail(row)

    @classmethod
    def normalize_summary(cls, raw: Mapping[str, Any]) -> JobAlioSummary:
        return JobAlioSummary(
            id=str(raw.get("recrutPblntSn") or ""),
            institution_name=cls._to_text(raw.get("instNm")),
            institution_code=cls._to_text(raw.get("pblntInstCd")),
            title=cls._to_text(raw.get("recrutPbancTtl")),
            start_date=cls._to_date(raw.get("pbancBgngYmd")),
            end_date=cls._to_date(raw.get("pbancEndYmd")),
            is_ongoing=cls._from_yn(raw.get("ongoingYn")),
            ncs_codes=cls._split(raw.get("ncsCdLst")),
            ncs_categories=cls._split(raw.get("ncsCdNmLst")),
            employment_types=cls._split(raw.get("hireTypeNmLst")),
            recruitment_type=cls._to_text(raw.get("recrutSeNm")),
            headcount=cls._to_int(raw.get("recrutNope")),
            work_regions=cls._split(raw.get("workRgnNmLst")),
            source_url=cls._to_text(raw.get("srcUrl")),
            qualification=cls._to_text(raw.get("aplyQlfcCn")),
            preferred_conditions=cls._to_text(raw.get("prefCondCn")),
            preference=cls._to_text(raw.get("prefCn")),
            disqualification_reason=cls._to_text(raw.get("disqlfcRsn")),
            screening_procedure=cls._to_text(raw.get("scrnprcdrMthdExpln")),
            replacement_recruitment=cls._from_yn(raw.get("replmprYn")),
            raw=dict(raw),
        )

    @classmethod
    def normalize_detail(cls, raw: Mapping[str, Any]) -> JobAlioDetail:
        summary = cls.normalize_summary(raw)
        return JobAlioDetail(
            **summary.model_dump(exclude={"raw"}),
            attachments=cls._normalize_attachments(raw.get("files")),
            steps=cls._normalize_steps(raw.get("steps")),
            raw=dict(raw),
        )

    async def _post_form(self, url: str, form: Mapping[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(url, data=form)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise JobAlioWebClientError(f"Job-ALIO request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise JobAlioWebClientError("Job-ALIO response was not JSON") from exc

        if not isinstance(payload, dict):
            raise JobAlioWebClientError("Job-ALIO response root was not an object")
        return payload

    @staticmethod
    def _response_data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        data = payload.get("data")
        if not isinstance(data, dict):
            raise JobAlioWebClientError("Job-ALIO response did not contain data")
        result_code = str(data.get("resultCode", "")).strip()
        if result_code and result_code not in JobAlioWebClient.SUCCESS_RESULT_CODES:
            message = data.get("resultMsg") or "unknown error"
            raise JobAlioWebClientError(f"Job-ALIO returned resultCode={result_code}: {message}")
        return data

    @classmethod
    def _normalize_attachments(cls, files: Any) -> list[JobAlioAttachment]:
        if not isinstance(files, list):
            return []
        return [
            JobAlioAttachment(
                sort_no=cls._to_int(row.get("sortNo")),
                file_no=cls._to_int(row.get("recrutAtchFileNo")),
                name=cls._to_text(row.get("atchFileNm")),
                file_type=cls._to_text(row.get("atchFileType")),
                url=cls._to_text(row.get("url")),
            )
            for row in files
            if isinstance(row, dict)
        ]

    @classmethod
    def _normalize_steps(cls, steps: Any) -> list[JobAlioStep]:
        if not isinstance(steps, list):
            return []
        return [
            JobAlioStep(
                sort_no=cls._to_int(row.get("sortNo")),
                title=cls._to_text(row.get("recrutPbancTtl")),
                step_sn=cls._to_int(row.get("recrutStepSn")),
                min_step_sn=cls._to_int(row.get("minStepSn")),
                max_step_sn=cls._to_int(row.get("maxStepSn")),
                headcount=cls._to_int(row.get("recrutNope")),
                applicant_count=cls._to_int(row.get("aplyNope")),
                competition_rate=cls._to_float(row.get("cmpttRt")),
                occurrence_date=cls._to_date(row.get("rsnOcrnYmd")),
            )
            for row in steps
            if isinstance(row, dict)
        ]

    @staticmethod
    def _clean_form(form: Mapping[str, Any]) -> dict[str, str]:
        return {
            key: str(value)
            for key, value in form.items()
            if value is not None and str(value).strip() != ""
        }

    @staticmethod
    def _split(value: Any) -> list[str]:
        text = JobAlioWebClient._to_text(value)
        if not text:
            return []
        return [part.strip() for part in text.split(",") if part.strip()]

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
    def _to_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(str(value).replace(",", "").strip())
        except ValueError:
            return None

    @staticmethod
    def _to_date(value: Any) -> str | None:
        text = JobAlioWebClient._to_text(value)
        if not text:
            return None
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) != 8:
            return text
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"

    @staticmethod
    def _to_yn(value: bool | None) -> str | None:
        if value is None:
            return None
        return "Y" if value else "N"

    @staticmethod
    def _from_yn(value: Any) -> bool | None:
        text = JobAlioWebClient._to_text(value)
        if text == "Y":
            return True
        if text == "N":
            return False
        return None
