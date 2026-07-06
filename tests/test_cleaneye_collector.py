import asyncio

from kr_gov_job_mcp.collectors.cleaneye import CleaneyeCollector
from kr_gov_job_mcp.collectors.raw_store import RawSampleStore
from kr_gov_job_mcp.schemas.cleaneye import (
    CleaneyeDisclosureItem,
    CleaneyeInstitution,
    CleaneyeInstitutionKind,
    CleaneyeInstitutionSearchResult,
)


class FakeCleaneyeClient:
    async def search_public_enterprises(
        self,
        *,
        keyword: str | None = None,
        kind_code: str | None = None,
    ) -> CleaneyeInstitutionSearchResult:
        return CleaneyeInstitutionSearchResult(
            kind="local_public_enterprise",
            total_count=1,
            institutions=[
                CleaneyeInstitution(
                    id="2017000008",
                    name=keyword,
                    kind="local_public_enterprise",
                    kind_code="006001",
                    raw={"entId": "2017000008", "entName": keyword, "entKind": "006001"},
                )
            ],
            raw={"data": [{"entId": "2017000008", "entName": keyword}]},
        )

    async def search_invested_or_contributed(
        self,
        *,
        keyword: str | None = None,
        institution_class: str | None = None,
        kind_code: str | None = None,
    ) -> CleaneyeInstitutionSearchResult:
        return CleaneyeInstitutionSearchResult(
            kind="local_invested_contributed",
            total_count=1,
            institutions=[
                CleaneyeInstitution(
                    id="B000261",
                    name=keyword,
                    kind="local_invested_contributed",
                    kind_code="012002",
                    raw={"insttCode": "B000261", "insttNm": keyword, "entKind": "012002"},
                )
            ],
            raw={"data": [{"insttCode": "B000261", "insttNm": keyword}]},
        )

    async def fetch_item_tree(
        self,
        *,
        institution_id: str,
        kind: CleaneyeInstitutionKind,
    ) -> dict:
        return {"data": [{"itemId": institution_id, "itemNm": "기관"}]}

    async def fetch_item_metadata(
        self,
        *,
        item_no: str,
        kind: CleaneyeInstitutionKind,
    ) -> CleaneyeDisclosureItem:
        return CleaneyeDisclosureItem(
            item_no=item_no,
            item_id=f"item-{item_no}",
            name=f"항목 {item_no}",
            action_url="https://www.cleaneye.go.kr/user/mock.do",
            raw={"itemNo": item_no, "itemId": f"item-{item_no}"},
        )

    async def fetch_disclosure_html(
        self,
        *,
        institution: CleaneyeInstitution,
        item: CleaneyeDisclosureItem,
    ) -> str:
        return f"<html>{institution.id}:{item.item_no}</html>"


def test_cleaneye_collector_writes_public_enterprise_samples(tmp_path) -> None:
    async def run() -> None:
        collector = CleaneyeCollector(client=FakeCleaneyeClient())  # type: ignore[arg-type]
        store = RawSampleStore(tmp_path)

        result = await collector.collect_raw(
            query={"institution_name": "서울교통공사"},
            sample_store=store,
        )

        assert result.errors == []
        assert result.normalized_count == 5
        assert len(result.raw_sample_paths) == 13
        sample_types = {store.read_sample(path).raw_type for path in result.raw_sample_paths}
        assert sample_types == {"list", "metadata", "html"}

    asyncio.run(run())


def test_cleaneye_collector_supports_invested_kind(tmp_path) -> None:
    async def run() -> None:
        collector = CleaneyeCollector(client=FakeCleaneyeClient())  # type: ignore[arg-type]
        store = RawSampleStore(tmp_path)

        result = await collector.collect_raw(
            query={"institution_name": "서울시립교향악단", "kind": "ipt"},
            sample_store=store,
        )

        assert result.errors == []
        first = store.read_sample(result.raw_sample_paths[0])
        assert first.metadata["kind"] == "local_invested_contributed"

    asyncio.run(run())
