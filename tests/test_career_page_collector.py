import asyncio

from kr_gov_job_mcp.collectors.career_page import CareerPageCollector
from kr_gov_job_mcp.collectors.raw_store import RawSampleStore
from kr_gov_job_mcp.schemas.career_page import CareerPageLink, CareerPageSnapshot


class FakeCareerPageClient:
    async def fetch_snapshot(self, url: str) -> tuple[CareerPageSnapshot, str]:
        return (
            CareerPageSnapshot(
                source_url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                title="채용 공고",
                page_type="institution_board_detail",
                body_text_preview="채용 공고 본문",
                links=[
                    CareerPageLink(
                        url="https://example.test/file.pdf",
                        text="공고문",
                        kind="attachment_candidate",
                    )
                ],
            ),
            "<html><title>채용 공고</title></html>",
        )


def test_career_page_collector_writes_html_and_metadata_samples(tmp_path) -> None:
    async def run() -> None:
        collector = CareerPageCollector(client=FakeCareerPageClient())  # type: ignore[arg-type]
        store = RawSampleStore(tmp_path)

        result = await collector.collect_raw(
            query={
                "job_id": "302423",
                "institution_name": "창업진흥원",
                "source_url": "https://example.test/job",
            },
            sample_store=store,
        )

        assert result.errors == []
        assert result.normalized_count == 1
        assert len(result.raw_sample_paths) == 2
        samples = [store.read_sample(path) for path in result.raw_sample_paths]
        assert {sample.raw_type for sample in samples} == {"html", "metadata"}
        metadata = next(sample for sample in samples if sample.raw_type == "metadata")
        assert metadata.payload["page_type"] == "institution_board_detail"
        assert metadata.metadata["attachment_candidate_count"] == 1

    asyncio.run(run())


def test_career_page_collector_requires_url(tmp_path) -> None:
    async def run() -> None:
        collector = CareerPageCollector(client=FakeCareerPageClient())  # type: ignore[arg-type]
        result = await collector.collect_raw(query={}, sample_store=RawSampleStore(tmp_path))

        assert result.raw_sample_paths == []
        assert result.errors == ["source_url or url is required"]

    asyncio.run(run())
