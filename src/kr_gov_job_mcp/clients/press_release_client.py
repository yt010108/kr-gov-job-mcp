"""Generic client for public institution press release pages."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

import httpx

from kr_gov_job_mcp.schemas.press_release import (
    PressReleaseDetail,
    PressReleaseEvidenceSource,
    PressReleaseLink,
    PressReleaseListItem,
)


class PressReleaseClientError(RuntimeError):
    """Raised when a press release page cannot be inspected."""


class PressReleaseClient:
    """Fetch and lightly parse public press release list/detail pages."""

    DEFAULT_STRATEGY_KEYWORDS = (
        "디지털",
        "보안",
        "정보보호",
        "개인정보",
        "데이터",
        "전산",
        "사이버",
        "클라우드",
        "AI",
        "인공지능",
        "블록체인",
        "N2SF",
        "망 보안",
    )
    DETAIL_LINK_HINTS = (
        "postSeq=",
        "nttSn=",
        "list_no=",
        "boardDetail",
        "boardView",
        "boardNo=",
        "selectNttInfo",
        "/form?",
        "seq=",
    )
    ATTACHMENT_HINTS = (
        ".hwp",
        ".hwpx",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".zip",
        ".jpg",
        ".jpeg",
        ".png",
        "attach",
        "atch",
        "download",
        "file",
    )
    FILE_EXTENSION_HINTS = (
        ".hwp",
        ".hwpx",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".zip",
        ".jpg",
        ".jpeg",
        ".png",
    )
    DATE_PATTERN = re.compile(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})")
    FN_DETAIL_PATTERN = re.compile(
        r"fn_Detail\(\s*['\"](?P<board_mng_no>[^'\"]+)['\"]\s*,\s*"
        r"['\"](?P<board_no>[^'\"]+)['\"]\s*\)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
        user_agent: str = "kr-gov-job-mcp/0.1 (press-release-observation)",
    ) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "User-Agent": user_agent,
            },
        )

    async def __aenter__(self) -> PressReleaseClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_list(
        self,
        url: str,
        *,
        limit: int = 5,
    ) -> tuple[list[PressReleaseListItem], str]:
        clean_url = self._to_text(url)
        if clean_url is None:
            raise PressReleaseClientError("press release list URL is required")
        html = await self._get_text(clean_url)
        return self.parse_list(html, base_url=clean_url, limit=limit), html

    async def fetch_detail(
        self,
        item: PressReleaseListItem,
        *,
        keywords: tuple[str, ...] | list[str] | None = None,
    ) -> tuple[PressReleaseDetail, str]:
        html = await self._get_text(item.url)
        return (
            self.parse_detail(
                html,
                url=item.url,
                title_hint=item.title,
                published_date_hint=item.published_date,
                keywords=tuple(keywords or self.DEFAULT_STRATEGY_KEYWORDS),
            ),
            html,
        )

    async def _get_text(self, url: str) -> str:
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PressReleaseClientError(f"press release request failed: {exc}") from exc
        return response.text

    @classmethod
    def parse_list(cls, html: str, *, base_url: str, limit: int = 5) -> list[PressReleaseListItem]:
        parser = _PressReleaseListParser(base_url=base_url)
        parser.feed(html)
        parser.close()

        items: list[PressReleaseListItem] = []
        seen_urls: set[str] = set()
        for row in parser.rows:
            date = cls._first_date(row.text)
            for link in row.links:
                if not cls._looks_like_detail_link(link.url) or not link.text:
                    continue
                if link.url in seen_urls:
                    continue
                seen_urls.add(link.url)
                items.append(
                    PressReleaseListItem(
                        title=cls._without_first_date(link.text),
                        url=link.url,
                        published_date=date,
                        raw_text=row.text,
                    )
                )
                break
            if len(items) >= limit:
                return items

        for link in parser.links:
            if len(items) >= limit:
                break
            if link.url in seen_urls or not cls._looks_like_detail_link(link.url) or not link.text:
                continue
            seen_urls.add(link.url)
            items.append(
                PressReleaseListItem(
                    title=cls._without_first_date(link.text),
                    url=link.url,
                    published_date=cls._first_date(link.text),
                )
            )
        return items

    @classmethod
    def parse_detail(
        cls,
        html: str,
        *,
        url: str,
        title_hint: str,
        published_date_hint: str | None = None,
        keywords: tuple[str, ...] | list[str] | None = None,
    ) -> PressReleaseDetail:
        parser = _PressReleaseDetailParser(base_url=url)
        parser.feed(html)
        parser.close()
        body_text = cls._squash_space(" ".join(parser.body_parts))
        title = title_hint or parser.heading or parser.title or url
        published_date = published_date_hint or cls._first_date(body_text or "")
        matched_keywords = cls.match_keywords(
            " ".join(part for part in (title, body_text) if part),
            keywords=keywords or cls.DEFAULT_STRATEGY_KEYWORDS,
        )
        return PressReleaseDetail(
            title=title,
            url=url,
            published_date=published_date,
            body_text_preview=body_text[:1500] if body_text else None,
            links=cls._dedupe_links(parser.links),
            matched_keywords=matched_keywords,
        )

    @classmethod
    def to_evidence_source(
        cls,
        detail: PressReleaseDetail,
        *,
        institution_name: str | None = None,
    ) -> PressReleaseEvidenceSource:
        return PressReleaseEvidenceSource(
            institution_name=institution_name,
            title=detail.title,
            url=detail.url,
            published_date=detail.published_date,
            matched_keywords=detail.matched_keywords,
            excerpt=detail.body_text_preview,
        )

    @classmethod
    def match_keywords(
        cls,
        text: str,
        *,
        keywords: tuple[str, ...] | list[str],
    ) -> list[str]:
        lower_text = text.lower()
        matches: list[str] = []
        for keyword in keywords:
            lower_keyword = keyword.lower()
            if lower_keyword.isascii() and lower_keyword.replace(" ", "").isalnum():
                pattern = rf"(?<![a-z0-9]){re.escape(lower_keyword)}(?![a-z0-9])"
                if re.search(pattern, lower_text):
                    matches.append(keyword)
            elif lower_keyword in lower_text:
                matches.append(keyword)
        return list(dict.fromkeys(matches))

    @classmethod
    def _classify_link(cls, href: str, text: str | None) -> str:
        lower_text = (text or "").lower()
        fragment = urlsplit(href).fragment.lower()
        if fragment:
            has_file_name = any(hint in lower_text for hint in cls.FILE_EXTENSION_HINTS)
            if "fnpostattachdownload" in fragment and (
                has_file_name or "첨부파일" in (text or "")
            ):
                return "attachment_candidate"
            return "other"

        haystack = f"{href} {text or ''}".lower()
        if any(hint in haystack for hint in cls.ATTACHMENT_HINTS):
            return "attachment_candidate"
        return "other"

    @classmethod
    def _looks_like_detail_link(cls, url: str) -> bool:
        lower_url = url.lower()
        return any(hint.lower() in lower_url for hint in cls.DETAIL_LINK_HINTS)

    @classmethod
    def _javascript_detail_url(cls, href: str, *, base_url: str) -> str | None:
        match = cls.FN_DETAIL_PATTERN.search(href)
        if not match:
            return None

        parsed = urlsplit(base_url)
        parent = parsed.path.rsplit("/", maxsplit=1)[0]
        detail_path = f"{parent}/boardView.do"
        query = urlencode(
            {
                "boardMngNo": match.group("board_mng_no"),
                "boardNo": match.group("board_no"),
            }
        )
        return urlunsplit((parsed.scheme, parsed.netloc, detail_path, query, ""))

    @classmethod
    def _first_date(cls, text: str) -> str | None:
        match = cls.DATE_PATTERN.search(text)
        if not match:
            return None
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    @classmethod
    def _without_first_date(cls, text: str | None) -> str:
        if not text:
            return ""
        match = cls.DATE_PATTERN.search(text)
        if not match:
            return text
        return cls._squash_space(f"{text[: match.start()]} {text[match.end() :]}") or text

    @classmethod
    def _dedupe_links(cls, links: list[PressReleaseLink]) -> list[PressReleaseLink]:
        deduped: dict[tuple[str, str, str | None], PressReleaseLink] = {}
        for link in links:
            key = (link.url, link.kind, link.text)
            if key not in deduped:
                deduped[key] = link
        return list(deduped.values())

    @staticmethod
    def _squash_space(value: str) -> str | None:
        text = re.sub(r"\s+", " ", value).strip()
        return text or None

    @staticmethod
    def _to_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class _ParsedRow:
    def __init__(self, *, text: str, links: list[PressReleaseLink]) -> None:
        self.text = text
        self.links = links


class _PressReleaseListParser(HTMLParser):
    def __init__(self, *, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.rows: list[_ParsedRow] = []
        self.links: list[PressReleaseLink] = []
        self._row_stack: list[dict[str, Any]] = []
        self._anchor_stack: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        if tag == "tr":
            self._row_stack.append({"text_parts": [], "links": []})
        if tag == "a":
            href = attr_map.get("href")
            if not href or href.startswith(("#", "mailto:", "tel:")):
                return
            if href.startswith("javascript:"):
                detail_url = PressReleaseClient._javascript_detail_url(href, base_url=self.base_url)
                if not detail_url:
                    return
                href = detail_url
            self._anchor_stack.append(
                {
                    "url": urljoin(self.base_url, href),
                    "text_parts": [attr_map.get("title") or attr_map.get("aria-label") or ""],
                }
            )

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._anchor_stack:
            anchor = self._anchor_stack.pop()
            text = PressReleaseClient._squash_space(" ".join(anchor["text_parts"]))
            link = PressReleaseLink(url=anchor["url"], text=text)
            self.links.append(link)
            if self._row_stack:
                self._row_stack[-1]["links"].append(link)
        if tag == "tr" and self._row_stack:
            row = self._row_stack.pop()
            text = PressReleaseClient._squash_space(" ".join(row["text_parts"])) or ""
            self.rows.append(_ParsedRow(text=text, links=row["links"]))

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._anchor_stack:
            self._anchor_stack[-1]["text_parts"].append(text)
        if self._row_stack:
            self._row_stack[-1]["text_parts"].append(text)


class _PressReleaseDetailParser(HTMLParser):
    def __init__(self, *, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title: str | None = None
        self.heading: str | None = None
        self.body_parts: list[str] = []
        self.links: list[PressReleaseLink] = []
        self._in_title = False
        self._in_heading = False
        self._skip_depth = 0
        self._anchor_stack: list[dict[str, Any]] = []
        self._heading_parts: list[str] = []
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        if tag == "title":
            self._in_title = True
        if tag in {"h1", "h2"}:
            self._in_heading = True
        if tag in {"script", "style", "noscript", "header", "nav", "footer", "aside"}:
            self._skip_depth += 1
        if tag == "a":
            if self._skip_depth:
                return
            href = attr_map.get("href")
            if not href or href.startswith(("javascript:", "mailto:", "tel:")):
                return
            if href.startswith("#") and not self._is_download_fragment(href, attr_map):
                return
            self._anchor_stack.append(
                {
                    "url": urljoin(self.base_url, href),
                    "text_parts": [attr_map.get("title") or attr_map.get("aria-label") or ""],
                }
            )

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
            self.title = PressReleaseClient._squash_space(" ".join(self._title_parts))
        if tag in {"h1", "h2"}:
            self._in_heading = False
            if self.heading is None:
                self.heading = PressReleaseClient._squash_space(" ".join(self._heading_parts))
            self._heading_parts = []
        if (
            tag in {"script", "style", "noscript", "header", "nav", "footer", "aside"}
            and self._skip_depth
        ):
            self._skip_depth -= 1
        if tag == "a" and self._anchor_stack:
            anchor = self._anchor_stack.pop()
            text = PressReleaseClient._squash_space(" ".join(anchor["text_parts"]))
            self.links.append(
                PressReleaseLink(
                    url=anchor["url"],
                    text=text,
                    kind=PressReleaseClient._classify_link(anchor["url"], text),
                )
            )

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self._title_parts.append(text)
        if self._in_heading:
            self._heading_parts.append(text)
        if self._skip_depth:
            return
        self.body_parts.append(text)
        if self._anchor_stack:
            self._anchor_stack[-1]["text_parts"].append(text)

    @staticmethod
    def _is_download_fragment(href: str, attr_map: dict[str, str]) -> bool:
        haystack = f"{href} {attr_map.get('onclick', '')} {attr_map.get('title', '')}".lower()
        return "fnpostattachdownload" in haystack
