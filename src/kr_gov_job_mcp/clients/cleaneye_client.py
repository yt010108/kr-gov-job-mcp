"""Cleaneye public web client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from kr_gov_job_mcp.schemas.cleaneye import (
    CleaneyeDisclosureItem,
    CleaneyeInstitution,
    CleaneyeInstitutionKind,
    CleaneyeInstitutionSearchResult,
)


class CleaneyeClientError(RuntimeError):
    """Raised when Cleaneye returns an unusable response."""


class CleaneyeClient:
    """Client for confirmed public Cleaneye disclosure endpoints."""

    BASE_URL = "https://www.cleaneye.go.kr"

    PUBLIC_SEARCH_PATH = "/user/selectNewEntSearchList.do"
    PUBLIC_ITEM_TREE_PATH = "/user/selectNewItemEntList.do"
    PUBLIC_ITEM_META_PATH = "/user/selectItemIdCheck.do"

    INVESTED_SEARCH_PATH = "/user/selectIptEntSearchList.do"
    INVESTED_ITEM_TREE_PATH = "/user/selectIptItemEntList.do"
    INVESTED_ITEM_META_PATH = "/user/selectIptItemIdCheck.do"

    PUBLIC_HOME_PATH = "/user/itemGongsi.do"
    INVESTED_HOME_PATH = "/user/iptItemGongsi.do"

    PUBLIC_DEFAULT_CONTEXT = {
        "fixedYear": "2025",
        "pastYear": "2021",
        "beyondYear": "2029",
        "openedDate": "2026.05.29",
        "openedDateHalf": "2025",
        "fixedHalfYear": "2024",
        "pastHalfYear": "2020",
        "dtFlagHalf": "B",
        "openedDateQuarter": "2026",
        "fixedQuarterYear": "2026",
        "pastQuarterYear": "2022",
        "dtFlagQuarter": "C",
    }
    INVESTED_DEFAULT_CONTEXT = {
        "fixedYear": "2024",
        "pastYear": "2020",
        "beyondYear": "2028",
        "openedDate": "2025.07.31",
        "openedDateQuarter": "2026",
        "fixedQuarterYear": "2026",
        "pastQuarterYear": "2022",
        "dtFlagQuarter": "C",
    }

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
                "User-Agent": "kr-gov-job-mcp/0.1 (cleaneye-observation)",
                "X-Requested-With": "XMLHttpRequest",
            },
        )

    async def __aenter__(self) -> CleaneyeClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search_public_enterprises(
        self,
        *,
        keyword: str | None = None,
        kind_code: str | None = None,
    ) -> CleaneyeInstitutionSearchResult:
        data = await self._post_json(
            self.PUBLIC_SEARCH_PATH,
            {"entName": keyword or "", "entKind": kind_code or ""},
            referer="/itemTop.do",
        )
        rows = data.get("data") or []
        if not isinstance(rows, list):
            raise CleaneyeClientError("Cleaneye public enterprise search data was not a list")
        return CleaneyeInstitutionSearchResult(
            kind="local_public_enterprise",
            total_count=len(rows),
            institutions=[
                self.normalize_institution(row, kind="local_public_enterprise")
                for row in rows
                if isinstance(row, dict)
            ],
            raw=dict(data),
        )

    async def search_invested_or_contributed(
        self,
        *,
        keyword: str | None = None,
        institution_class: str | None = None,
        kind_code: str | None = None,
    ) -> CleaneyeInstitutionSearchResult:
        data = await self._post_json(
            self.INVESTED_SEARCH_PATH,
            {
                "insttNm": keyword or "",
                "iptEntKind": institution_class or "",
                "entGubun": kind_code or "",
            },
            referer="/iptItemTop.do",
        )
        rows = data.get("data") or []
        if not isinstance(rows, list):
            raise CleaneyeClientError("Cleaneye invested institution search data was not a list")
        return CleaneyeInstitutionSearchResult(
            kind="local_invested_contributed",
            total_count=len(rows),
            institutions=[
                self.normalize_institution(row, kind="local_invested_contributed")
                for row in rows
                if isinstance(row, dict)
            ],
            raw=dict(data),
        )

    async def fetch_item_tree(
        self,
        *,
        institution_id: str,
        kind: CleaneyeInstitutionKind,
    ) -> dict[str, Any]:
        if kind == "local_public_enterprise":
            return await self._post_json(
                self.PUBLIC_ITEM_TREE_PATH,
                {"entId": institution_id},
                referer="/itemLeft.do",
            )
        return await self._post_json(
            self.INVESTED_ITEM_TREE_PATH,
            {"entId": institution_id},
            referer="/iptListLeft.do",
        )

    async def fetch_item_metadata(
        self,
        *,
        item_no: str,
        kind: CleaneyeInstitutionKind,
    ) -> CleaneyeDisclosureItem:
        if kind == "local_public_enterprise":
            data = await self._post_json(
                self.PUBLIC_ITEM_META_PATH,
                {"item": item_no},
                referer="/itemTop.do",
            )
        else:
            data = await self._post_json(
                self.INVESTED_ITEM_META_PATH,
                {"item": item_no},
                referer="/iptItemTop.do",
            )
        row = data.get("data")
        if not isinstance(row, dict):
            raise CleaneyeClientError(f"Cleaneye item metadata was missing for item={item_no}")
        return self.normalize_disclosure_item(row)

    async def fetch_disclosure_html(
        self,
        *,
        institution: CleaneyeInstitution,
        item: CleaneyeDisclosureItem,
    ) -> str:
        if not item.action_url:
            raise CleaneyeClientError(f"Cleaneye item has no action URL: {item.item_no}")

        context = (
            self.PUBLIC_DEFAULT_CONTEXT
            if institution.kind == "local_public_enterprise"
            else self.INVESTED_DEFAULT_CONTEXT
        )
        form = {
            **context,
            "entId": institution.id,
            "entName": institution.name or "",
            "entKind": institution.kind_code or "",
            "itemId": item.item_id or "",
        }
        return await self._post_text(
            item.action_url,
            form,
            referer=(
                "/itemLeft.do"
                if institution.kind == "local_public_enterprise"
                else "/iptListLeft.do"
            ),
        )

    @classmethod
    def normalize_institution(
        cls,
        raw: Mapping[str, Any],
        *,
        kind: CleaneyeInstitutionKind,
    ) -> CleaneyeInstitution:
        if kind == "local_public_enterprise":
            institution_id = cls._to_text(raw.get("entId")) or ""
            name = cls._to_text(raw.get("entName"))
        else:
            institution_id = cls._to_text(raw.get("insttCode")) or ""
            name = cls._to_text(raw.get("insttNm"))
        return CleaneyeInstitution(
            id=institution_id,
            name=name,
            kind=kind,
            kind_code=cls._to_text(raw.get("entKind")),
            source_url=cls.home_url(kind),
            raw=dict(raw),
        )

    @classmethod
    def normalize_disclosure_item(cls, raw: Mapping[str, Any]) -> CleaneyeDisclosureItem:
        action_path = cls._to_text(raw.get("portalActionUrl"))
        return CleaneyeDisclosureItem(
            item_no=cls._to_text(raw.get("itemNo")) or "",
            item_id=cls._to_text(raw.get("itemId")),
            name=cls._to_text(raw.get("itemNm")),
            action_url=cls._absolute_url(action_path) if action_path else None,
            use_yn=cls._to_text(raw.get("useYn")),
            raw=dict(raw),
        )

    @classmethod
    def home_url(cls, kind: CleaneyeInstitutionKind) -> str:
        if kind == "local_public_enterprise":
            return cls._absolute_url(cls.PUBLIC_HOME_PATH)
        return cls._absolute_url(cls.INVESTED_HOME_PATH)

    async def _post_json(
        self,
        path: str,
        form: Mapping[str, Any],
        *,
        referer: str,
    ) -> dict[str, Any]:
        response = await self._request("POST", path, form=form, referer=referer)
        try:
            payload = response.json()
        except ValueError as exc:
            raise CleaneyeClientError("Cleaneye response was not JSON") from exc
        if not isinstance(payload, dict):
            raise CleaneyeClientError("Cleaneye response root was not an object")
        return payload

    async def _post_text(
        self,
        path: str,
        form: Mapping[str, Any],
        *,
        referer: str,
    ) -> str:
        response = await self._request(
            "POST",
            path,
            form=form,
            referer=referer,
            headers={"Accept": "text/html, */*; q=0.01"},
        )
        return response.text

    async def _request(
        self,
        method: str,
        path: str,
        *,
        form: Mapping[str, Any],
        referer: str,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        request_headers = {"Referer": self._absolute_url(referer)}
        if headers:
            request_headers.update(headers)
        try:
            response = await self._client.request(
                method,
                self._absolute_url(path),
                data=self._clean_form(form),
                headers=request_headers,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CleaneyeClientError(f"Cleaneye request failed: {exc}") from exc
        return response

    @classmethod
    def _absolute_url(cls, path_or_url: str) -> str:
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url
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
    def _to_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
