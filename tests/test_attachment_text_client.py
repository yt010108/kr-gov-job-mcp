import asyncio
from io import BytesIO

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from kr_gov_job_mcp.clients.attachment_text_client import AttachmentTextClient


def _text_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 20 200 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_attachment_text_client_extracts_pdf_text() -> None:
    pdf = _text_pdf("Knowledge: network security")

    async def run() -> object:
        transport = httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "application/pdf"},
                content=pdf,
            )
        )
        async with httpx.AsyncClient(transport=transport) as http_client:
            async with AttachmentTextClient(client=http_client) as client:
                return await client.extract(
                    "https://example.test/duty.pdf",
                    file_name="duty.pdf",
                )

    result = asyncio.run(run())
    assert result.status == "extracted"
    assert "network security" in result.text


def test_attachment_text_client_marks_empty_pdf_for_ocr() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    output = BytesIO()
    writer.write(output)

    async def run() -> object:
        transport = httpx.MockTransport(
            lambda _request: httpx.Response(200, content=output.getvalue())
        )
        async with httpx.AsyncClient(transport=transport) as http_client:
            async with AttachmentTextClient(client=http_client) as client:
                return await client.extract("https://example.test/scan.pdf")

    result = asyncio.run(run())
    assert result.status == "ocr_required"
    assert "OCR" in result.reason


def test_attachment_text_client_rejects_unsupported_and_private_urls() -> None:
    async def run() -> tuple[object, object]:
        async with AttachmentTextClient() as client:
            unsupported = await client.extract(
                "https://example.test/duty.hwpx",
                file_name="duty.hwpx",
            )
            private = await client.extract("http://127.0.0.1/duty.pdf")
            return unsupported, private

    unsupported, private = asyncio.run(run())
    assert unsupported.status == "unsupported_format"
    assert private.status == "download_failed"


def test_attachment_text_client_rejects_oversized_and_fake_pdf_responses() -> None:
    async def run() -> tuple[object, object]:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("large.pdf"):
                return httpx.Response(200, headers={"content-length": "20"}, content=b"%PDF")
            return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"HTML")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            async with AttachmentTextClient(client=http_client, max_bytes=10) as client:
                oversized = await client.extract("https://example.test/large.pdf")
                fake = await client.extract("https://example.test/fake.pdf")
                return oversized, fake

    oversized, fake = asyncio.run(run())
    assert oversized.status == "download_failed"
    assert fake.status == "invalid_pdf"


def test_attachment_text_client_preserves_http_failure_reason() -> None:
    async def run() -> object:
        transport = httpx.MockTransport(lambda _request: httpx.Response(503))
        async with httpx.AsyncClient(transport=transport) as http_client:
            async with AttachmentTextClient(client=http_client) as client:
                return await client.extract("https://example.test/duty.pdf")

    result = asyncio.run(run())
    assert result.status == "download_failed"
    assert "503" in result.reason
