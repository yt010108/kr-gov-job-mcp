"""Bounded attachment download and PDF text extraction."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from ipaddress import ip_address
from pathlib import PurePosixPath
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader

from kr_gov_job_mcp.schemas.ncs import AttachmentExtractionStatus


MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_EXTRACTED_CHARACTERS = 200_000


@dataclass(frozen=True)
class AttachmentTextResult:
    status: AttachmentExtractionStatus
    text: str | None = None
    media_type: str | None = None
    reason: str | None = None


class AttachmentTextClient:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        max_bytes: int = MAX_ATTACHMENT_BYTES,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._max_bytes = max_bytes

    async def __aenter__(self) -> AttachmentTextClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=20.0, follow_redirects=False)
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def extract(self, url: str, *, file_name: str | None = None) -> AttachmentTextResult:
        validation_error = _validate_public_url(url)
        if validation_error:
            return AttachmentTextResult(status="download_failed", reason=validation_error)

        suffix = PurePosixPath(urlparse(url).path).suffix.lower()
        name_suffix = PurePosixPath(file_name or "").suffix.lower()
        format_suffix = name_suffix or suffix
        if format_suffix in {".hwp", ".hwpx", ".zip"}:
            return AttachmentTextResult(
                status="unsupported_format",
                reason=f"{format_suffix.lstrip('.').upper()} 형식은 자동 본문 추출을 지원하지 않습니다.",
            )

        try:
            if self._client is None:
                raise RuntimeError("AttachmentTextClient must be used as an async context manager")
            async with self._client.stream("GET", url) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    return AttachmentTextResult(
                        status="download_failed",
                        reason=f"첨부 다운로드가 리디렉션되었습니다: {location or '대상 미상'}",
                    )
                response.raise_for_status()
                media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self._max_bytes:
                    return AttachmentTextResult(
                        status="download_failed",
                        media_type=media_type or None,
                        reason="첨부파일이 허용된 최대 크기를 초과합니다.",
                    )
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > self._max_bytes:
                        return AttachmentTextResult(
                            status="download_failed",
                            media_type=media_type or None,
                            reason="첨부파일이 허용된 최대 크기를 초과합니다.",
                        )
                    chunks.append(chunk)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            return AttachmentTextResult(status="download_failed", reason=str(exc))

        content = b"".join(chunks)
        if format_suffix != ".pdf" and media_type != "application/pdf" and not content.startswith(b"%PDF"):
            return AttachmentTextResult(
                status="unsupported_format",
                media_type=media_type or None,
                reason="PDF가 아닌 첨부 형식은 자동 본문 추출을 지원하지 않습니다.",
            )
        if not content.startswith(b"%PDF"):
            return AttachmentTextResult(
                status="invalid_pdf",
                media_type=media_type or None,
                reason="PDF 파일 서명을 확인하지 못했습니다.",
            )
        try:
            reader = PdfReader(BytesIO(content))
            pages = reader.pages[:MAX_PDF_PAGES]
            text = "\n".join(page.extract_text() or "" for page in pages).strip()
        except Exception as exc:  # pypdf exposes several parser-specific exceptions.
            return AttachmentTextResult(
                status="invalid_pdf",
                media_type=media_type or None,
                reason=f"PDF 본문을 읽지 못했습니다: {exc}",
            )
        if not text:
            return AttachmentTextResult(
                status="ocr_required",
                media_type=media_type or None,
                reason="텍스트 레이어가 없어 OCR 또는 원문 수동 확인이 필요합니다.",
            )
        truncated = len(reader.pages) > MAX_PDF_PAGES or len(text) > MAX_EXTRACTED_CHARACTERS
        return AttachmentTextResult(
            status="extracted",
            text=text[:MAX_EXTRACTED_CHARACTERS],
            media_type=media_type or None,
            reason=(
                "PDF가 처리 한도를 초과해 일부 본문만 추출했습니다. 원문 확인이 필요합니다."
                if truncated
                else None
            ),
        )


def _validate_public_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return "첨부 URL은 호스트가 있는 HTTPS 주소여야 합니다."
    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        return "로컬 네트워크 첨부 URL은 요청할 수 없습니다."
    try:
        address = ip_address(hostname)
    except ValueError:
        return None
    if not address.is_global:
        return "공개 인터넷 주소가 아닌 첨부 URL은 요청할 수 없습니다."
    return None
