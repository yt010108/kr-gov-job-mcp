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


KEPCO_LIST_HTML = """
<div class="board-list">
  <a href="javascript:fn_Detail('15','3106');">
    복합위기 상황에도 전력수급 이상 없도록... 한전, 안정적 전력공급 위한 비상근무 돌입 2026.07.06
  </a>
  <a href="/home/about/introduce/overview.do">KEPCO 개요</a>
</div>
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


KISA_ATTACHMENT_HTML = """
<html>
  <body>
    <h1>안전한 개인정보 활용 연구 착수</h1>
    <div class="board_detail_attach">
      <a href="#fnPostAttachDownload"
         onclick="javascript:fnPostAttachDownload(402, '2605', 1, 'KO');"
         title="첨부파일 다운로드">260629-KISA-보도자료.pdf (165KB)</a>
      <a href="#fnPostAttachDownload"
         onclick="javascript:fnPostAttachDownload(402, '2605', 2, 'KO');"
         title="첨부파일 다운로드">260629-KISA-보도사진.jpeg (1MB)</a>
    </div>
    <footer>
      <a href="#fnPostAttachDownload"
         onclick="javascript:fnPostAttachDownload(99999999, 1, 1, 'KO');"
         title="소개자료 다운로드 국문">KR</a>
    </footer>
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


def test_parse_press_release_list_supports_kepco_javascript_detail_links() -> None:
    items = PressReleaseClient.parse_list(
        KEPCO_LIST_HTML,
        base_url="https://www.kepco.co.kr/home/media/newsroom/pr/boardList.do",
        limit=2,
    )

    assert len(items) == 1
    assert items[0].url == (
        "https://www.kepco.co.kr/home/media/newsroom/pr/boardView.do"
        "?boardMngNo=15&boardNo=3106"
    )
    assert items[0].published_date == "2026-07-06"
    assert items[0].title == "복합위기 상황에도 전력수급 이상 없도록... 한전, 안정적 전력공급 위한 비상근무 돌입"


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


def test_parse_press_release_detail_detects_kisa_download_fragment_attachment() -> None:
    detail = PressReleaseClient.parse_detail(
        KISA_ATTACHMENT_HTML,
        url="https://www.kisa.or.kr/402/form?postSeq=2605&page=1",
        title_hint="안전한 개인정보 활용 연구 착수",
        published_date_hint="2026-06-26",
    )

    assert len(detail.attachment_candidates) == 2
    assert (
        detail.attachment_candidates[0].url
        == "https://www.kisa.or.kr/402/form?postSeq=2605&page=1#fnPostAttachDownload"
    )
    assert "260629-KISA-보도자료.pdf" in (detail.attachment_candidates[0].text or "")
    assert "260629-KISA-보도사진.jpeg" in (detail.attachment_candidates[1].text or "")


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
