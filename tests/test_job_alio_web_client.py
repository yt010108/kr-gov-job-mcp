import asyncio

import httpx

from kr_gov_job_mcp.clients.job_alio_web_client import JobAlioWebClient


def test_normalize_summary_maps_job_alio_fields() -> None:
    summary = JobAlioWebClient.normalize_summary(
        {
            "recrutPblntSn": 302423,
            "instNm": "창업진흥원",
            "pblntInstCd": "B552909",
            "recrutPbancTtl": "2026년 제2차 신규직원 채용 공고",
            "pbancBgngYmd": "20260706",
            "pbancEndYmd": "20260720",
            "ongoingYn": "Y",
            "ncsCdLst": "R600020,R600021",
            "ncsCdNmLst": "정보통신,사업관리",
            "hireTypeNmLst": "무기계약직",
            "recrutSeNm": "경력",
            "recrutNope": "2",
            "workRgnNmLst": "대전,세종",
            "srcUrl": "https://example.test/job",
        }
    )

    assert summary.id == "302423"
    assert summary.institution_name == "창업진흥원"
    assert summary.start_date == "2026-07-06"
    assert summary.end_date == "2026-07-20"
    assert summary.is_ongoing is True
    assert summary.ncs_codes == ["R600020", "R600021"]
    assert summary.ncs_categories == ["정보통신", "사업관리"]
    assert summary.headcount == 2
    assert summary.work_regions == ["대전", "세종"]


def test_search_jobs_posts_ajax_form_and_normalizes_response() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path.endswith("/recrutInquiryAjaxList.do")
            body = request.content.decode()
            assert "pageNo=1" in body
            assert "numOfRows=1" in body
            assert "ongoingYn=Y" in body
            return httpx.Response(
                200,
                json={
                    "data": {
                        "resultCode": "1",
                        "totalCount": 1,
                        "result": [
                            {
                                "recrutPblntSn": 302423,
                                "instNm": "창업진흥원",
                                "recrutPbancTtl": "채용 공고",
                                "pbancBgngYmd": "20260706",
                                "pbancEndYmd": "20260720",
                                "ongoingYn": "Y",
                            }
                        ],
                    }
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = JobAlioWebClient(http_client=http_client)
            result = await client.search_jobs(keyword="정보", limit=1)

        assert result.total_count == 1
        assert result.jobs[0].id == "302423"
        assert result.jobs[0].title == "채용 공고"

    asyncio.run(run())


def test_fetch_job_detail_normalizes_attachments_and_steps() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path.endswith("/recrutInquiryAjaxDetail.do")
            assert request.content.decode() == "sn=302423"
            return httpx.Response(
                200,
                json={
                    "data": {
                        "resultCode": "1",
                        "result": {
                            "recrutPblntSn": 302423,
                            "instNm": "창업진흥원",
                            "recrutPbancTtl": "채용 공고",
                            "files": [
                                {
                                    "sortNo": 1,
                                    "recrutAtchFileNo": 3060250,
                                    "atchFileNm": "공고문.hwpx",
                                    "atchFileType": "A",
                                    "url": "https://example.test/file",
                                }
                            ],
                            "steps": [
                                {
                                    "sortNo": 0,
                                    "recrutStepSn": 1237448,
                                    "recrutPbancTtl": "서류전형",
                                    "recrutNope": "2",
                                    "aplyNope": "10",
                                    "cmpttRt": "5.0",
                                }
                            ],
                        },
                    }
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = JobAlioWebClient(http_client=http_client)
            detail = await client.fetch_job_detail("302423")

        assert detail.id == "302423"
        assert detail.attachments[0].name == "공고문.hwpx"
        assert detail.steps[0].title == "서류전형"
        assert detail.steps[0].competition_rate == 5.0

    asyncio.run(run())
