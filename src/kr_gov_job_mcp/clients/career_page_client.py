"""Generic client for institution career page snapshots."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from kr_gov_job_mcp.schemas.career_page import CareerPageLink, CareerPageSnapshot


class CareerPageClientError(RuntimeError):
    """Raised when an institution career page cannot be inspected."""


class CareerPageClient:
    """Fetch and lightly inspect Job-ALIO source URLs without site-specific parsing."""

    ATTACHMENT_HINTS = (
        ".hwp",
        ".hwpx",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".zip",
        "attach",
        "atch",
        "download",
        "file",
    )
    APPLY_HINTS = (
        "apply",
        "application",
        "입사지원",
        "지원하기",
        "온라인접수",
        "접수",
        "fairyhr",
        "recruiter.co.kr",
    )
    DEDICATED_RECRUIT_HOSTS = ("fairyhr.com", "recruiter.co.kr", "saramin.co.kr")

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
        user_agent: str = "kr-gov-job-mcp/0.1 (career-page-observation)",
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

    async def __aenter__(self) -> CareerPageClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_snapshot(self, url: str) -> tuple[CareerPageSnapshot, str]:
        clean_url = self._to_text(url)
        if clean_url is None:
            raise CareerPageClientError("career page URL is required")
        try:
            response = await self._client.get(clean_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CareerPageClientError(f"career page request failed: {exc}") from exc

        html = response.text
        parsed = self.parse_html(html, base_url=str(response.url))
        snapshot = CareerPageSnapshot(
            source_url=clean_url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            title=parsed.title,
            page_type=self.classify_page(str(response.url), parsed),
            body_text_preview=parsed.body_text_preview,
            links=parsed.links,
        )
        return snapshot, html

    @classmethod
    def parse_html(cls, html: str, *, base_url: str) -> "_CareerPageHtmlSummary":
        parser = _CareerPageHtmlParser(base_url=base_url)
        parser.feed(html)
        parser.close()
        body_text = cls._squash_space(" ".join(parser.body_parts))
        return _CareerPageHtmlSummary(
            title=cls._squash_space(" ".join(parser.title_parts)),
            body_text_preview=body_text[:1000] if body_text else None,
            links=cls._dedupe_links(parser.links),
        )

    @classmethod
    def classify_page(cls, final_url: str, parsed: "_CareerPageHtmlSummary") -> str:
        host = urlparse(final_url).netloc.lower()
        path = urlparse(final_url).path.lower()
        if any(host.endswith(recruit_host) for recruit_host in cls.DEDICATED_RECRUIT_HOSTS):
            return "dedicated_recruitment_platform"
        if any(token in path for token in ("recruitdtl", "announcement/detail", "incruit")):
            return "institution_recruit_detail"
        if any(link.kind == "attachment_candidate" for link in parsed.links):
            return "institution_board_detail"
        if "recruit" in path or "채용" in (parsed.title or ""):
            return "career_landing_or_dynamic_page"
        return "unknown"

    @classmethod
    def _classify_link(cls, href: str, text: str | None) -> str:
        haystack = f"{href} {text or ''}".lower()
        if any(hint in haystack for hint in cls.ATTACHMENT_HINTS):
            return "attachment_candidate"
        if any(hint in haystack for hint in cls.APPLY_HINTS):
            return "apply_candidate"
        return "other"

    @classmethod
    def _dedupe_links(cls, links: list[CareerPageLink]) -> list[CareerPageLink]:
        deduped: dict[tuple[str, str], CareerPageLink] = {}
        for link in links:
            key = (link.url, link.kind)
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


class _CareerPageHtmlSummary:
    def __init__(
        self,
        *,
        title: str | None,
        body_text_preview: str | None,
        links: list[CareerPageLink],
    ) -> None:
        self.title = title
        self.body_text_preview = body_text_preview
        self.links = links


class _CareerPageHtmlParser(HTMLParser):
    def __init__(self, *, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.links: list[CareerPageLink] = []
        self._anchor_stack: list[dict[str, Any]] = []
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag == "a":
            href = attr_map.get("href")
            if not href or href.startswith(("javascript:", "#", "mailto:", "tel:")):
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
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "a" and self._anchor_stack:
            anchor = self._anchor_stack.pop()
            text = CareerPageClient._squash_space(" ".join(anchor["text_parts"]))
            self.links.append(
                CareerPageLink(
                    url=anchor["url"],
                    text=text,
                    kind=CareerPageClient._classify_link(anchor["url"], text),
                )
            )

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
            return
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self.body_parts.append(text)
            if self._anchor_stack:
                self._anchor_stack[-1]["text_parts"].append(text)
