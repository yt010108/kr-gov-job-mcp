import asyncio

from kr_gov_job_mcp.collectors.alio_disclosure import AlioDisclosureCollector
from kr_gov_job_mcp.collectors.raw_store import RawSampleStore
from kr_gov_job_mcp.schemas.alio import (
    AlioInstitution,
    AlioInstitutionSearchResult,
    AlioPointItem,
    AlioPointKind,
    AlioPointSearchResult,
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
                    name=keyword or "한국인터넷진흥원",
                    type_name="준정부기관(위탁집행형)",
                    raw={"apbaId": "C0399", "apbaNa": keyword, "apbaType": "A2004"},
                )
            ],
            raw={"organList": {"result": [{"apbaId": "C0399", "apbaType": "A2004"}]}},
        )

    async def fetch_institution_detail(self, institution_code: str) -> AlioInstitution:
        return AlioInstitution(
            id=institution_code,
            name="한국인터넷진흥원",
            main_business="o 침해사고 대응",
            raw={"apbaId": institution_code, "apbaNa": "한국인터넷진흥원", "contents": "o 침해사고 대응"},
        )

    async def list_point_items(
        self,
        *,
        kind: AlioPointKind,
        institution_name: str | None = None,
        keyword: str | None = None,
        keyword_type: str = "apbaNa",
        page: int = 1,
        limit: int = 8,
        sort_type: str | None = None,
    ) -> AlioPointSearchResult:
        return AlioPointSearchResult(
            kind=kind,
            page=page,
            limit=limit,
            total_count=1,
            items=[
                AlioPointItem(
                    id=f"{kind}-1",
                    kind=kind,
                    institution_id="C0399",
                    institution_name=institution_name,
                    raw={"submissionNo": f"{kind}-1"},
                )
            ],
            raw={"result": [{"submissionNo": f"{kind}-1"}], "totalCnt": 1},
        )

    async def list_general_status_reports(
        self,
        *,
        institution_code: str,
        institution_type: str | None = None,
        page: int = 1,
    ) -> AlioReportSearchResult:
        return AlioReportSearchResult(
            report_form_root_no="10105",
            page=page,
            total_count=1,
            reports=[
                AlioReportDisclosure(
                    disclosure_no="general-1",
                    report_form_no="10105",
                    title="일반현황",
                    institution_id=institution_code,
                    raw={"disclosureNo": "general-1"},
                )
            ],
            raw={"result": [{"disclosureNo": "general-1"}]},
        )

    async def list_quarterly_report_disclosures(
        self,
        *,
        institution_code: str,
        quarter: int = 0,
    ) -> AlioReportSearchResult:
        return AlioReportSearchResult(
            report_form_root_no="quarterly",
            total_count=1,
            reports=[
                AlioReportDisclosure(
                    disclosure_no="main-1",
                    report_form_no="31501",
                    title="주요사업",
                    institution_id=institution_code,
                    raw={"disclosureNo": "main-1", "reportFormNo": "31501"},
                )
            ],
            raw={"html": "<script></script>", "reportList": [{"disclosureNo": "main-1"}]},
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


def test_alio_disclosure_collector_writes_raw_samples(tmp_path) -> None:
    async def run() -> None:
        collector = AlioDisclosureCollector(client=FakeAlioDisclosureClient())  # type: ignore[arg-type]
        store = RawSampleStore(tmp_path)

        result = await collector.collect_raw(
            query={"institution_name": "한국인터넷진흥원", "point_limit": 1},
            sample_store=store,
        )

        assert result.errors == []
        assert result.normalized_count == 5
        assert len(result.raw_sample_paths) == 11

        sample_types = {store.read_sample(path).raw_type for path in result.raw_sample_paths}
        assert sample_types == {"list", "detail", "attachment", "html", "metadata"}

        metadata_samples = [
            store.read_sample(path)
            for path in result.raw_sample_paths
            if store.read_sample(path).raw_type == "metadata"
        ]
        assert metadata_samples[0].payload["main_business"].endswith(
            "reportFormRootNo=31501"
        )

    asyncio.run(run())


def test_alio_disclosure_collector_requires_institution_identifier(tmp_path) -> None:
    async def run() -> None:
        collector = AlioDisclosureCollector(client=FakeAlioDisclosureClient())  # type: ignore[arg-type]
        result = await collector.collect_raw(query={}, sample_store=RawSampleStore(tmp_path))

        assert result.raw_sample_paths == []
        assert result.errors == ["institution_name or institution_code is required"]

    asyncio.run(run())
