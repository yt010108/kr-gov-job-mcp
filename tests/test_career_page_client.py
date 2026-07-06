import asyncio

import httpx

from kr_gov_job_mcp.clients.career_page_client import CareerPageClient


def test_fetch_snapshot_extracts_title_links_and_page_type() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/board/view"
            return httpx.Response(
                200,
                headers={"content-type": "text/html;charset=UTF-8"},
                text="""
                <html>
                  <head><title>채용 공고 | 기관</title></head>
                  <body>
                    <h1>채용 공고</h1>
                    <a href="/files/notice.pdf" title="공고문 PDF">download</a>
                    <a href="https://example.test/form">입사지원</a>
                    <script>ignored text</script>
                  </body>
                </html>
                """,
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        ) as http_client:
            client = CareerPageClient(http_client=http_client)
            snapshot, html = await client.fetch_snapshot("https://example.test/board/view")

        assert "채용 공고" in html
        assert snapshot.title == "채용 공고 | 기관"
        assert snapshot.page_type == "institution_board_detail"
        assert snapshot.attachment_candidates[0].url == "https://example.test/files/notice.pdf"
        assert snapshot.apply_candidates[0].url == "https://example.test/form"
        assert "ignored text" not in snapshot.body_text_preview

    asyncio.run(run())


def test_classify_dedicated_recruitment_platform() -> None:
    parsed = CareerPageClient.parse_html(
        "<html><body><div id='app'></div></body></html>",
        base_url="https://knuh.fairyhr.com/announcement/detail/123",
    )

    assert (
        CareerPageClient.classify_page(
            "https://knuh.fairyhr.com/announcement/detail/123",
            parsed,
        )
        == "dedicated_recruitment_platform"
    )
