import asyncio

import pytest

from kr_gov_job_mcp.clients.alio_disclosure_client import AlioDisclosureItemConfig
from kr_gov_job_mcp.schemas.alio import (
    AlioInstitution,
    AlioInstitutionSearchResult,
    AlioReportDisclosure,
    AlioReportSearchResult,
)
from kr_gov_job_mcp.tools.institution_analysis import (
    _collect_alio_institution_context,
    create_analyze_institution_strategy_tool,
    create_analyze_institution_weakness_tool,
    create_collect_institution_context_tool,
)


class FakeAlioContextClient:
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
                    id=institution_code or "C0399",
                    name=keyword or "한국인터넷진흥원",
                    type_name="준정부기관",
                    source_url="https://www.alio.go.kr/organ/organDisclosureDtl.do?apbaId=C0399",
                    raw={"apbaId": institution_code or "C0399", "apbaType": "A2004"},
                )
            ],
            raw={"organList": {"result": []}},
        )

    async def fetch_institution_detail(self, institution_code: str) -> AlioInstitution:
        return AlioInstitution(
            id=institution_code,
            name="한국인터넷진흥원",
            type_name="준정부기관",
            ministry_name="과학기술정보통신부",
            homepage_url="https://www.kisa.or.kr",
            main_business="정보보호 산업 지원 및 디지털 신뢰 기반 조성",
            source_url=f"https://www.alio.go.kr/organ/organDisclosureDtl.do?apbaId={institution_code}",
            raw={"apbaId": institution_code, "apbaType": "A2004"},
        )

    async def list_item_reports(
        self,
        *,
        institution_code: str,
        item: AlioDisclosureItemConfig,
        institution_type: str | None = None,
        page: int = 1,
    ) -> AlioReportSearchResult:
        title = "정보보호 산업 육성 사업" if item.item_no == "40" else "보안 운영 개선 요구"
        return AlioReportSearchResult(
            report_form_root_no=item.report_form_root_no,
            page=page,
            total_count=1,
            reports=[
                AlioReportDisclosure(
                    disclosure_no=f"{item.report_form_root_no}-2026",
                    report_form_no=item.report_form_root_no,
                    title=title,
                    disclosed_date="2026-03-31",
                    institution_id=institution_code,
                    source_url=f"https://www.alio.go.kr/example/{item.report_form_root_no}",
                    raw={"disclosureNo": f"{item.report_form_root_no}-2026"},
                )
            ],
            raw={"result": []},
        )


def test_collect_institution_context_returns_alio_evidence_and_analysis_signals() -> None:
    async def run() -> None:
        analysis_input = await _collect_alio_institution_context(
            client=FakeAlioContextClient(),  # type: ignore[arg-type]
            institution_name="한국인터넷진흥원",
            institution_code=None,
            year=2026,
            sources=["alio", "homepage"],
        )

        assert analysis_input.alio_id == "C0399"
        assert analysis_input.identity_candidates[0].source_id == "C0399"
        assert any(evidence.source_type == "alio_disclosure" for evidence in analysis_input.evidence)
        assert any(evidence.source_type == "institution_homepage" for evidence in analysis_input.evidence)
        assert {signal.category for signal in analysis_input.signals} == {
            "business_direction",
            "improvement_task",
        }

        strategy = create_analyze_institution_strategy_tool().handler(
            {
                "institution_name": analysis_input.institution_name,
                "year": 2026,
                "job_family": "정보보호",
                "evidence": [item.model_dump(mode="json") for item in analysis_input.evidence],
                "signals": [item.model_dump(mode="json") for item in analysis_input.signals],
            }
        )
        weakness = create_analyze_institution_weakness_tool().handler(
            {
                "institution_name": analysis_input.institution_name,
                "year": 2026,
                "evidence": [item.model_dump(mode="json") for item in analysis_input.evidence],
                "signals": [item.model_dump(mode="json") for item in analysis_input.signals],
            }
        )

        assert strategy["strategy_signals"][0]["category"] == "business_direction"
        assert weakness["weakness_signals"][0]["category"] == "improvement_task"

    asyncio.run(run())


def test_collect_institution_context_tool_serializes_context_payload() -> None:
    def fake_collect_context(**_kwargs):
        return asyncio.run(
            _collect_alio_institution_context(
                client=FakeAlioContextClient(),  # type: ignore[arg-type]
                institution_name="한국인터넷진흥원",
                institution_code=None,
                year=2026,
                sources=["alio", "homepage"],
            )
        )

    tool = create_collect_institution_context_tool(collect_context=fake_collect_context)

    result = tool.handler(
        {
            "institution_name": "한국인터넷진흥원",
            "year": 2026,
            "sources": ["alio", "homepage"],
        }
    )

    assert result["source"] == "institution_context"
    assert result["query"]["sources"] == ["alio", "homepage"]
    assert result["alio_id"] == "C0399"
    assert result["evidence"]
    assert result["signals"]
    assert result["warnings"] == []


def test_collect_institution_context_rejects_invalid_arguments() -> None:
    tool = create_collect_institution_context_tool(
        collect_context=lambda **_kwargs: pytest.fail("collector should not run")
    )

    with pytest.raises(ValueError, match="institution_name is required"):
        tool.handler({})

    with pytest.raises(ValueError, match="unsupported collect_institution_context arguments"):
        tool.handler({"institution_name": "한국인터넷진흥원", "extra": True})

    with pytest.raises(ValueError, match="unsupported institution context source"):
        tool.handler({"institution_name": "한국인터넷진흥원", "sources": ["unknown"]})

    with pytest.raises(ValueError, match="institution_code and alio_id conflict"):
        tool.handler(
            {
                "institution_name": "한국인터넷진흥원",
                "institution_code": "C0399",
                "alio_id": "C0000",
            }
        )
