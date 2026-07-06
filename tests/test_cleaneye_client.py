import asyncio
from urllib.parse import parse_qs

import httpx

from kr_gov_job_mcp.clients.cleaneye_client import CleaneyeClient


def test_search_public_enterprises_posts_form_and_normalizes_rows() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/user/selectNewEntSearchList.do"
            body = parse_qs(request.content.decode())
            assert body["entName"] == ["서울교통공사"]
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "entId": "2017000008",
                            "entName": "서울교통공사",
                            "entKind": "006001",
                        }
                    ],
                    "resultExcludeEntKindList": [],
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = CleaneyeClient(http_client=http_client)
            result = await client.search_public_enterprises(keyword="서울교통공사")

        assert result.total_count == 1
        assert result.institutions[0].id == "2017000008"
        assert result.institutions[0].kind == "local_public_enterprise"
        assert result.institutions[0].source_url.endswith("/user/itemGongsi.do")

    asyncio.run(run())


def test_search_invested_or_contributed_normalizes_rows() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/user/selectIptEntSearchList.do"
            body = parse_qs(request.content.decode())
            assert body["insttNm"] == ["서울시립교향악단"]
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "insttCode": "B000261",
                            "insttNm": "서울시립교향악단",
                            "entKind": "012002",
                        }
                    ],
                    "resultExcludeIptEntKindList": [],
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = CleaneyeClient(http_client=http_client)
            result = await client.search_invested_or_contributed(keyword="서울시립교향악단")

        assert result.institutions[0].id == "B000261"
        assert result.institutions[0].kind == "local_invested_contributed"
        assert result.institutions[0].source_url.endswith("/user/iptItemGongsi.do")

    asyncio.run(run())


def test_item_metadata_and_disclosure_html_use_confirmed_endpoints() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/user/selectItemIdCheck.do":
                return httpx.Response(
                    200,
                    json={
                        "data": {
                            "itemNo": "1_1",
                            "itemId": "commStatus",
                            "itemNm": "일반현황",
                            "portalActionUrl": "/user/empCommStatus.do",
                            "useYn": "Y",
                        }
                    },
                )
            assert request.url.path == "/user/empCommStatus.do"
            body = parse_qs(request.content.decode())
            assert body["entId"] == ["2017000008"]
            assert body["entName"] == ["서울교통공사"]
            assert body["itemId"] == ["commStatus"]
            return httpx.Response(200, text="<html><title>서울교통공사 일반현황</title></html>")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = CleaneyeClient(http_client=http_client)
            item = await client.fetch_item_metadata(item_no="1_1", kind="local_public_enterprise")
            html = await client.fetch_disclosure_html(
                institution=client.normalize_institution(
                    {"entId": "2017000008", "entName": "서울교통공사", "entKind": "006001"},
                    kind="local_public_enterprise",
                ),
                item=item,
            )

        assert item.item_id == "commStatus"
        assert item.action_url.endswith("/user/empCommStatus.do")
        assert "서울교통공사" in html

    asyncio.run(run())
