import asyncio

from kr_gov_job_mcp.collectors import Collector, JobAlioCollector, RawSampleStore
from kr_gov_job_mcp.schemas.job import (
    JobAlioAttachment,
    JobAlioDetail,
    JobAlioSearchResult,
    JobAlioStep,
    JobAlioSummary,
)


class FakeJobAlioClient:
    def __init__(self) -> None:
        self.search_kwargs = {}
        self.detail_ids: list[str] = []
        self.closed = False

    async def search_jobs(self, **kwargs) -> JobAlioSearchResult:
        self.search_kwargs = kwargs
        return JobAlioSearchResult(
            page=kwargs["page"],
            limit=kwargs["limit"],
            total_count=2,
            jobs=[
                JobAlioSummary(
                    id="302423",
                    institution_name="창업진흥원",
                    title="채용 공고 1",
                    ncs_codes=["R600019"],
                    raw={
                        "recrutPblntSn": 302423,
                        "instNm": "창업진흥원",
                        "recrutPbancTtl": "채용 공고 1",
                        "ncsCdLst": "R600019",
                    },
                ),
                JobAlioSummary(
                    id="302424",
                    institution_name="한국인터넷진흥원",
                    title="채용 공고 2",
                    raw={
                        "recrutPblntSn": 302424,
                        "instNm": "한국인터넷진흥원",
                        "recrutPbancTtl": "채용 공고 2",
                    },
                ),
            ],
        )

    async def fetch_job_detail(self, recruitment_notice_sn: str) -> JobAlioDetail:
        self.detail_ids.append(recruitment_notice_sn)
        return JobAlioDetail(
            id=recruitment_notice_sn,
            institution_name="창업진흥원",
            title="상세 공고",
            ncs_codes=["R600019"],
            attachments=[JobAlioAttachment(name="공고문.pdf")],
            steps=[JobAlioStep(title="서류전형")],
            raw={
                "recrutPblntSn": int(recruitment_notice_sn),
                "instNm": "창업진흥원",
                "files": [{"atchFileNm": "공고문.pdf"}],
                "steps": [{"recrutPbancTtl": "서류전형"}],
                "ncsCdLst": "R600019",
            },
        )

    async def aclose(self) -> None:
        self.closed = True


def test_job_alio_collector_writes_list_and_detail_samples(tmp_path) -> None:
    async def run() -> None:
        client = FakeJobAlioClient()
        collector = JobAlioCollector(client=client, default_detail_limit=1)
        store = RawSampleStore(tmp_path)

        result = await collector.collect_raw(
            query={"keyword": "보안", "limit": "2", "detail_limit": 1},
            sample_store=store,
        )

        assert isinstance(collector, Collector)
        assert client.search_kwargs["keyword"] == "보안"
        assert client.search_kwargs["limit"] == 2
        assert client.detail_ids == ["302423"]
        assert result.source == "job_alio"
        assert result.normalized_count == 2
        assert len(result.raw_sample_paths) == 2

        list_sample = store.read_sample(result.raw_sample_paths[0])
        assert list_sample.raw_type == "list"
        assert list_sample.payload["total_count"] == 2
        assert list_sample.metadata["field_names"] == [
            "instNm",
            "ncsCdLst",
            "recrutPbancTtl",
            "recrutPblntSn",
        ]

        detail_sample = store.read_sample(result.raw_sample_paths[1])
        assert detail_sample.raw_type == "detail"
        assert detail_sample.metadata["attachment_count"] == 1
        assert detail_sample.metadata["step_count"] == 1

    asyncio.run(run())


def test_job_alio_collector_can_skip_detail_collection(tmp_path) -> None:
    async def run() -> None:
        client = FakeJobAlioClient()
        collector = JobAlioCollector(client=client)
        store = RawSampleStore(tmp_path)

        result = await collector.collect_raw(
            query={"limit": 2, "fetch_details": "false"},
            sample_store=store,
        )

        assert client.detail_ids == []
        assert len(result.raw_sample_paths) == 1
        assert result.notes == ["list_rows=2", "details_requested=0", "details_saved=0"]

    asyncio.run(run())
