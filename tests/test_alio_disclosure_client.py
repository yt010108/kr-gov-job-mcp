import asyncio
import json

import httpx

from kr_gov_job_mcp.clients.alio_disclosure_client import AlioDisclosureClient


def test_search_institutions_posts_json_and_normalizes_response() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/organ/findOrganApbaList.json"
            assert json.loads(request.content) == {
                "apbaNa": "한국인터넷진흥원",
                "pageNo": "1",
            }
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "organList": {
                            "page": {"totalCount": 1},
                            "result": [
                                {
                                    "apbaId": "C0399",
                                    "apbaNa": "한국인터넷진흥원",
                                    "typeNa": "준정부기관(위탁집행형)",
                                    "jidtNa": "과학기술정보통신부",
                                    "ceo": "이상중",
                                    "fdate": "20090723",
                                    "homepage": "www.kisa.or.kr",
                                    "contents": "o 침해사고 대응&cr;o 개인정보보호",
                                    "reportFormUseStrtDt": "20260401",
                                    "submissionNo": "2026061810422592",
                                }
                            ],
                        }
                    },
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AlioDisclosureClient(http_client=http_client)
            result = await client.search_institutions(keyword="한국인터넷진흥원")

        institution = result.institutions[0]
        assert result.total_count == 1
        assert institution.id == "C0399"
        assert institution.established_date == "2009-07-23"
        assert institution.homepage_url == "https://www.kisa.or.kr"
        assert institution.main_business == "o 침해사고 대응\no 개인정보보호"
        assert institution.source_url.endswith("/organ/organDisclosureDtl.do?apbaId=C0399")

    asyncio.run(run())


def test_list_point_items_normalizes_attachments_and_source_urls() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/occasional/findPointList.json"
            assert request.url.params["reportFormNo"] == "B1210"
            assert request.url.params["word"] == "한국인터넷진흥원"
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "totalCnt": 1,
                        "result": [
                            {
                                "submissionNo": "2025051210195015",
                                "reportFormNo": "B1210",
                                "apbaId": "C0399",
                                "apbaNa": "한국인터넷진흥원",
                                "rtitle": "서울 잔류 인원을 지방 본사로 통합",
                                "idate": "2025.05.12",
                                "pdate": "2025.10.24",
                                "rdate": "2025.10.24",
                                "enfcBgngYmd": "2024.10.10",
                                "enfcEndYmd": "2024.10.10",
                                "filedata1": (
                                    "1**17470391234504665.hwp**국정감사 결과보고서.hwp"
                                    "**/report/2025/05/12/2025051210195015/"
                                    "**2025051210195015"
                                ),
                            }
                        ],
                    },
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AlioDisclosureClient(http_client=http_client)
            result = await client.list_point_items(
                kind="national_assembly",
                institution_name="한국인터넷진흥원",
                limit=1,
            )

        item = result.items[0]
        assert result.total_count == 1
        assert item.id == "2025051210195015"
        assert item.registered_date == "2025-05-12"
        assert item.source_url.endswith("/occasional/nationalAssemblyDtl.do?seq=2025051210195015")
        assert item.attachments[0].original_name == "국정감사 결과보고서.hwp"
        assert "/download/pfile.json?" in item.attachments[0].download_url

    asyncio.run(run())


def test_quarterly_report_page_exposes_main_business_disclosure() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/organ/quarterlyReport.do"
            return httpx.Response(
                200,
                text=(
                    "<script>var app = new Vue({data:function(){return {"
                    "reportList: JSON.parse('[{\"reportFormNo\":\"31501\","
                    "\"rtitle\":\"주요사업\",\"disclosureNo\":\"2026041303151983\","
                    "\"submissionNo\":\"2026041310382324\",\"gbn\":\"1\","
                    "\"idate\":\"2026.04.13\",\"apbaId\":\"C0399\","
                    "\"pname\":\"한국인터넷진흥원\"}]')}}})</script>"
                ),
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AlioDisclosureClient(http_client=http_client)
            result = await client.list_quarterly_report_disclosures(institution_code="C0399")

        report = result.reports[0]
        assert report.report_form_no == "31501"
        assert report.title == "주요사업"
        assert report.report_kind == "regular_report"
        assert report.source_url.endswith(
            "/item/itemReportTerm.do?apbaId=C0399&reportFormRootNo=31501"
            "&disclosureNo=2026041303151983"
        )

    asyncio.run(run())


def test_list_occasional_item_reports_posts_susi_payload_and_builds_board_url() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/item/itemReportListSusi.json"
            assert json.loads(request.content) == {
                "pageNo": "1",
                "apbaId": "C0399",
                "apbaType": "A2004",
                "reportFormRootNo": "B1020",
                "search_flag": "title",
            }
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "result": [
                            {
                                "disclosureNo": "2026070303204326",
                                "reportFormNo": "B1020",
                                "tableName": "TTB_RECRUIT",
                                "idxName": "IDX",
                                "apbaId": "C0399",
                                "idx": "302324",
                                "reportGbn": "N",
                                "title": "KISA recruitment",
                                "idate": "2026.07.03",
                                "submissionNo": "2026070310430728",
                            }
                        ],
                        "page": {"totalCount": 54},
                    },
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AlioDisclosureClient(http_client=http_client)
            result = await client.list_occasional_item_reports(
                institution_code="C0399",
                institution_type="A2004",
                report_form_root_no="B1020",
            )

        report = result.reports[0]
        assert result.total_count == 54
        assert report.title == "KISA recruitment"
        assert report.source_url is not None
        assert "/item/itemBoardB1020.do?" in report.source_url
        assert "idx=302324" in report.source_url

    asyncio.run(run())


def test_list_regular_item_reports_posts_jung_payload_and_normalizes_rows() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/item/itemOrganListJung.json"
            assert json.loads(request.content) == {
                "apbaType": [],
                "jidtDptm": [],
                "area": [],
                "apbaId": "C0399",
                "reportFormRootNo": "31501",
                "quart": "",
            }
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "totalCnt": 1,
                        "organList": [
                            {
                                "apbaId": "C0399",
                                "apbaNa": "KISA",
                                "reportFormNo": "31501",
                                "submissionNo": "2026041310382324",
                                "disclosureNo": "2026041303151983",
                                "files": "101@main-business.pdf",
                            }
                        ],
                    },
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AlioDisclosureClient(http_client=http_client)
            result = await client.list_regular_item_reports(
                institution_code="C0399",
                report_form_root_no="31501",
            )

        report = result.reports[0]
        assert result.total_count == 1
        assert report.disclosure_no == "2026041303151983"
        assert report.source_url is not None
        assert report.source_url.endswith(
            "/item/itemReport.do?seq=2026041303151983&disclosureNo=2026041303151983"
        )

    asyncio.run(run())


def test_report_files_and_html_fetchers() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/item/itemReportFiles.json":
                assert request.url.params["disclosureNo"] == "2026041303151983"
                return httpx.Response(
                    200,
                    json={
                        "status": "success",
                        "data": [
                            {
                                "reportFormNo": "31501",
                                "disclosureNo": "2026041303151983",
                                "apbaId": "C0399",
                                "submissionNo": "2026041310382324",
                                "fileNo": "101",
                                "orcpFileNa": "01.정보보호및활용.pdf",
                                "saveFileNa": "01.정보보호및활용.pdf",
                                "savePath": "/report/2026/04/13/2026041310382324/",
                                "fileType": "PDF",
                                "fileSize": 0,
                            }
                        ],
                    },
                )
            assert request.url.path == "/item/itemReportRight.do"
            return httpx.Response(200, text="<div>주요사업</div>")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AlioDisclosureClient(http_client=http_client)
            files = await client.fetch_report_files("2026041303151983")
            html = await client.fetch_report_html("2026041303151983")

        assert files[0].file_no == "101"
        assert files[0].download_url.endswith(
            "/download/file.json?f=101&d=2026041303151983&s=2026041310382324"
        )
        assert html == "<div>주요사업</div>"

    asyncio.run(run())


def test_fetch_board_report_html_uses_item_board_path() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/item/itemBoardB1020.do"
            assert request.url.params["idx"] == "302324"
            return httpx.Response(200, text="<article>KISA recruitment</article>")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AlioDisclosureClient(http_client=http_client)
            html = await client.fetch_board_report_html(
                AlioDisclosureClient.normalize_report_disclosure(
                    {
                        "disclosureNo": "2026070303204326",
                        "reportFormNo": "B1020",
                        "tableName": "TTB_RECRUIT",
                        "idxName": "IDX",
                        "apbaId": "C0399",
                        "idx": "302324",
                        "reportGbn": "N",
                    }
                )
            )

        assert html == "<article>KISA recruitment</article>"

    asyncio.run(run())
