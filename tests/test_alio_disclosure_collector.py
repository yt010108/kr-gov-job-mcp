import asyncio

from kr_gov_job_mcp.clients.alio_disclosure_client import AlioDisclosureItemConfig
from kr_gov_job_mcp.collectors.alio_disclosure import AlioDisclosureCollector
from kr_gov_job_mcp.collectors.raw_store import RawSampleStore
from kr_gov_job_mcp.schemas.alio import (
    AlioInstitution,
    AlioInstitutionSearchResult,
    AlioReportDisclosure,
    AlioReportFile,
    AlioReportSearchResult,
)


class FakeAlioDisclosureClient:
    async def search_institutions(
        self,
        *,
        keyword: str | None = None,
        institution_code: str | None = None,
        page: int = 1,
    ) -> AlioInstitutionSearchResult:
        return AlioInstitutionSearchResult(
            page=page,
            total_count=1,
            institutions=[
                AlioInstitution(
                    id="C0399",
                    name=keyword or "KISA",
                    type_name="quasi-government",
                    raw={"apbaId": "C0399", "apbaNa": keyword, "apbaType": "A2004"},
                )
            ],
            raw={"organList": {"result": [{"apbaId": "C0399", "apbaType": "A2004"}]}},
        )

    async def fetch_institution_detail(self, institution_code: str) -> AlioInstitution:
        return AlioInstitution(
            id=institution_code,
            name="KISA",
            main_business="security and internet",
            raw={"apbaId": institution_code, "apbaNa": "KISA", "contents": "security"},
        )

    async def list_item_reports(
        self,
        *,
        institution_code: str,
        item: AlioDisclosureItemConfig,
        institution_type: str | None = None,
        page: int = 1,
    ) -> AlioReportSearchResult:
        raw_key = "organList" if item.kind == "regular" else "result"
        disclosure_no = f"{item.report_form_root_no}-1"
        return AlioReportSearchResult(
            report_form_root_no=item.report_form_root_no,
            page=page,
            total_count=1,
            reports=[
                AlioReportDisclosure(
                    disclosure_no=disclosure_no,
                    report_form_no=item.report_form_root_no,
                    title=item.name,
                    institution_id=institution_code,
                    source_url=f"https://www.alio.go.kr/example/{item.report_form_root_no}",
                    raw={
                        "disclosureNo": disclosure_no,
                        "reportFormNo": item.report_form_root_no,
                        "apbaId": institution_code,
                        "tableName": "COMM_BOARD",
                        "idxName": "BOARD_NO",
                        "idx": disclosure_no,
                        "reportGbn": "N" if item.kind == "occasional" else "Y",
                    },
                )
            ],
            raw={raw_key: [{"disclosureNo": disclosure_no}], "page": {"totalCount": 1}},
        )

    async def fetch_report_files(self, disclosure_no: str) -> list[AlioReportFile]:
        return [
            AlioReportFile(
                file_no="101",
                disclosure_no=disclosure_no,
                original_name=f"{disclosure_no}.pdf",
                raw={"fileNo": "101", "disclosureNo": disclosure_no},
            )
        ]

    async def fetch_report_html(self, disclosure_no: str) -> str:
        return f"<div>{disclosure_no}</div>"

    async def fetch_board_report_html(self, report: AlioReportDisclosure) -> str:
        return f"<article>{report.report_form_no}</article>"


def test_alio_disclosure_collector_writes_raw_samples(tmp_path) -> None:
    async def run() -> None:
        collector = AlioDisclosureCollector(client=FakeAlioDisclosureClient())  # type: ignore[arg-type]
        store = RawSampleStore(tmp_path)

        result = await collector.collect_raw(
            query={"institution_name": "KISA"},
            sample_store=store,
        )

        assert result.errors == []
        assert result.normalized_count == 8
        assert len(result.raw_sample_paths) == 19

        sample_types = {store.read_sample(path).raw_type for path in result.raw_sample_paths}
        assert sample_types == {"list", "detail", "attachment", "html", "metadata"}

        metadata_samples = [
            store.read_sample(path)
            for path in result.raw_sample_paths
            if store.read_sample(path).raw_type == "metadata"
        ]
        assert metadata_samples[0].payload["item_reports"]["40"]["report_form_root_no"] == "31501"
        assert metadata_samples[0].payload["excluded_item_reports"]["47-2"] == "감사원 지적사항"

    asyncio.run(run())


def test_alio_disclosure_collector_expands_item_groups(tmp_path) -> None:
    async def run() -> None:
        collector = AlioDisclosureCollector(client=FakeAlioDisclosureClient())  # type: ignore[arg-type]
        store = RawSampleStore(tmp_path)

        result = await collector.collect_raw(
            query={"institution_name": "KISA", "item_numbers": "49,50"},
            sample_store=store,
        )

        assert result.errors == []
        list_sample_ids = [
            store.read_sample(path).sample_id
            for path in result.raw_sample_paths
            if store.read_sample(path).raw_type == "list"
        ]
        assert any("item-49-1-B1030-reports" in sample_id for sample_id in list_sample_ids)
        assert any("item-49-2-7030-reports" in sample_id for sample_id in list_sample_ids)
        assert any("item-50-1-B1040-reports" in sample_id for sample_id in list_sample_ids)
        assert any("item-50-2-B1260-reports" in sample_id for sample_id in list_sample_ids)

    asyncio.run(run())


def test_alio_disclosure_collector_requires_institution_identifier(tmp_path) -> None:
    async def run() -> None:
        collector = AlioDisclosureCollector(client=FakeAlioDisclosureClient())  # type: ignore[arg-type]
        result = await collector.collect_raw(query={}, sample_store=RawSampleStore(tmp_path))

        assert result.raw_sample_paths == []
        assert result.errors == ["institution_name or institution_code is required"]

    asyncio.run(run())

