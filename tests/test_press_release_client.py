import asyncio

import httpx

from kr_gov_job_mcp.clients.press_release_client import PressReleaseClient


LIST_HTML = """
<table>
  <tr>
    <td>958</td>
    <td><a href="/402/form?postSeq=2605&page=1">안전한 개인정보 활용 연구 착수</a></td>
    <td>2026-06-26</td>
  </tr>
  <tr>
    <td>957</td>
    <td><a href="/402/form?postSeq=2606&page=1">블록체인 설명자료</a></td>
    <td>2026.06.25</td>
  </tr>
</table>
"""


DETAIL_HTML = """
<html>
  <head><title>보도자료</title></head>
  <body>
    <h1>안전한 개인정보 활용 연구 착수</h1>
    <p>개인정보와 데이터 활용을 안전하게 지원하는 연구개발을 시작한다.</p>
    <a href="/download/file.pdf">첨부파일</a>
  </body>
</html>
"""


def test_parse_press_release_list_extracts_detail_links_and_dates() -> None:
    items = PressReleaseClient.parse_list(
        LIST_HTML,
        base_url="https://www.kisa.or.kr/402",
        limit=2,
    )

    assert len(items) == 2
    assert items[0].title == "안전한 개인정보 활용 연구 착수"
    assert items[0].url == "https://www.kisa.or.kr/402/form?postSeq=2605&page=1"
    assert items[0].published_date == "2026-06-26"
    assert items[1].published_date == "2026-06-25"


def test_parse_press_release_detail_builds_evidence_candidate() -> None:
    detail = PressReleaseClient.parse_detail(
        DETAIL_HTML,
        url="https://www.kisa.or.kr/402/form?postSeq=2605&page=1",
        title_hint="안전한 개인정보 활용 연구 착수",
        published_date_hint="2026-06-26",
    )
    evidence = PressReleaseClient.to_evidence_source(detail, institution_name="한국인터넷진흥원")

    assert detail.matched_keywords == ["개인정보", "데이터"]
    assert detail.attachment_candidates[0].url == "https://www.kisa.or.kr/download/file.pdf"
    assert evidence.source_type == "press_release"
    assert evidence.institution_name == "한국인터넷진흥원"


def test_ascii_keyword_matching_uses_token_boundaries() -> None:
    assert PressReleaseClient.match_keywords(
        "main service and email guidance",
        keywords=("AI", "데이터"),
    ) == []
    assert PressReleaseClient.match_keywords(
        "AI 기반 데이터 분석",
        keywords=("AI", "데이터"),
    ) == ["AI", "데이터"]


def test_fetch_list_and_detail_use_http_client() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/402":
                return httpx.Response(200, text=LIST_HTML)
            if request.url.path == "/402/form":
                return httpx.Response(200, text=DETAIL_HTML)
            raise AssertionError(request.url)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        ) as http_client:
            client = PressReleaseClient(http_client=http_client)
            items, _html = await client.fetch_list("https://www.kisa.or.kr/402", limit=1)
            detail, _detail_html = await client.fetch_detail(items[0])

        assert len(items) == 1
        assert detail.title == "안전한 개인정보 활용 연구 착수"

    asyncio.run(run())
