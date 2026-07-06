import asyncio

from kr_gov_job_mcp.collectors.press_release import PressReleaseCollector
from kr_gov_job_mcp.collectors.raw_store import RawSampleStore
from kr_gov_job_mcp.schemas.press_release import PressReleaseDetail, PressReleaseListItem


class FakePressReleaseClient:
    async def fetch_list(self, url: str, *, limit: int = 5) -> tuple[list[PressReleaseListItem], str]:
        return (
            [
                PressReleaseListItem(
                    title="데이터 보안 보도자료",
                    url="https://example.test/press/1",
                    published_date="2026-06-26",
                )
            ],
            "<html>list</html>",
        )

    async def fetch_detail(
        self,
        item: PressReleaseListItem,
        *,
        keywords: tuple[str, ...] | list[str] | None = None,
    ) -> tuple[PressReleaseDetail, str]:
        return (
            PressReleaseDetail(
                title=item.title,
                url=item.url,
                published_date=item.published_date,
                body_text_preview="데이터 보안 사업을 추진한다.",
                matched_keywords=["데이터", "보안"],
            ),
            "<html>detail</html>",
        )

    def to_evidence_source(self, detail: PressReleaseDetail, *, institution_name: str | None = None):
        from kr_gov_job_mcp.clients.press_release_client import PressReleaseClient

        return PressReleaseClient.to_evidence_source(detail, institution_name=institution_name)


def test_press_release_collector_writes_list_detail_and_evidence_metadata(tmp_path) -> None:
    async def run() -> None:
        collector = PressReleaseCollector(client=FakePressReleaseClient())  # type: ignore[arg-type]
        store = RawSampleStore(tmp_path)

        result = await collector.collect_raw(
            query={
                "institution_name": "한국인터넷진흥원",
                "list_url": "https://example.test/press",
                "limit": 1,
            },
            sample_store=store,
        )

        assert result.errors == []
        assert result.normalized_count == 1
        assert len(result.raw_sample_paths) == 4
        samples = [store.read_sample(path) for path in result.raw_sample_paths]
        assert [sample.raw_type for sample in samples].count("html") == 2
        detail_metadata = samples[-1]
        assert detail_metadata.payload["evidence_source"]["source_type"] == "press_release"
        assert detail_metadata.metadata["matched_keywords"] == ["데이터", "보안"]

    asyncio.run(run())


def test_press_release_collector_requires_list_url(tmp_path) -> None:
    async def run() -> None:
        collector = PressReleaseCollector(client=FakePressReleaseClient())  # type: ignore[arg-type]
        result = await collector.collect_raw(query={}, sample_store=RawSampleStore(tmp_path))

        assert result.raw_sample_paths == []
        assert result.errors == ["list_url or url is required"]

    asyncio.run(run())
