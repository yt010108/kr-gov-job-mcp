import asyncio

from kr_gov_job_mcp.analysis.alio_average_salary import (
    AlioAverageSalaryResult,
    AverageSalaryRecord,
    extract_average_salary_records,
    fetch_alio_average_salary,
)
from kr_gov_job_mcp.schemas.alio import AlioInstitution, AlioReportDisclosure, AlioReportSearchResult
from kr_gov_job_mcp.tools.alio_average_salary import create_get_institution_average_salary_tool


_AVERAGE_SALARY_HTML = """
<table>
  <tr><td>정규직(일반정규직)</td><td>(단위: 천원, 명, %)</td></tr>
  <tr><th>구분</th><th>2023년 결산</th><th>2024년 결산</th><th>2025년 결산</th><th>2026년 예산</th></tr>
  <tr><td>기본급</td><td>49,239</td><td>48,837</td><td>48,060</td><td>49,742</td></tr>
  <tr><td>1인당 평균 보수액</td><td>69,671</td><td>68,926</td><td>70,405</td><td>70,938</td></tr>
</table>
"""


class _FakeAlioClient:
    async def fetch_institution_detail(self, institution_code: str) -> AlioInstitution:
        return AlioInstitution(id=institution_code, name="테스트 기관")

    async def list_regular_item_reports(
        self, *, institution_code: str, report_form_root_no: str
    ) -> AlioReportSearchResult:
        assert institution_code == "C0001"
        assert report_form_root_no == "2060"
        report = AlioReportDisclosure(
            disclosure_no="2026041403160074",
            report_form_no="20601",
            criterion_year=2026,
            source_url="https://www.alio.go.kr/item/itemReport.do?seq=2026041403160074",
        )
        return AlioReportSearchResult(
            report_form_root_no=report_form_root_no,
            total_count=1,
            reports=[report],
        )

    async def fetch_report_html(self, disclosure_no: str) -> str:
        assert disclosure_no == "2026041403160074"
        return _AVERAGE_SALARY_HTML


def test_extract_average_salary_records_preserves_settlement_and_budget_basis() -> None:
    records = extract_average_salary_records(_AVERAGE_SALARY_HTML)

    assert [(record.year, record.amount_thousand_krw, record.basis) for record in records] == [
        (2023, 69671, "결산"),
        (2024, 68926, "결산"),
        (2025, 70405, "결산"),
        (2026, 70938, "예산"),
    ]


def test_fetch_average_salary_defaults_to_latest_settlement_and_allows_requested_year() -> None:
    default_result = asyncio.run(
        fetch_alio_average_salary(
            institution_name="테스트 기관",
            alio_id="C0001",
            client=_FakeAlioClient(),  # type: ignore[arg-type]
        )
    )
    planned_result = asyncio.run(
        fetch_alio_average_salary(
            institution_name="테스트 기관",
            alio_id="C0001",
            year=2026,
            client=_FakeAlioClient(),  # type: ignore[arg-type]
        )
    )

    assert default_result.as_dict()["average_salary"] == {
        "year": 2025,
        "amount_krw": 70405000,
        "amount_thousand_krw": 70405,
        "basis": "결산",
        "header": "2025년 결산",
        "label": "1인당 평균 보수액",
        "employment_group": "정규직(일반정규직)",
        "unit": "KRW",
    }
    assert planned_result.as_dict()["average_salary"]["basis"] == "예산"
    assert planned_result.as_dict()["average_salary"]["amount_krw"] == 70938000


def test_fetch_average_salary_does_not_substitute_another_year() -> None:
    result = asyncio.run(
        fetch_alio_average_salary(
            institution_name="테스트 기관",
            alio_id="C0001",
            year=2022,
            client=_FakeAlioClient(),  # type: ignore[arg-type]
        )
    ).as_dict()

    assert result["average_salary"] is None
    assert result["warnings"] == [
        "ALIO 직원 평균보수 has no value for requested year 2022; no fallback was used."
    ]


def test_average_salary_tool_validates_arguments_and_serializes_result() -> None:
    expected = AlioAverageSalaryResult(
        institution_id="C0001",
        institution_name="테스트 기관",
        records=[
            AverageSalaryRecord(
                year=2025,
                amount_thousand_krw=70405,
                basis="결산",
                header="2025년 결산",
                label="1인당 평균 보수",
            )
        ],
    )
    calls = []

    def fake_fetch(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        return expected

    tool = create_get_institution_average_salary_tool(fetch_average_salary=fake_fetch)
    result = tool.handler({"institution_name": " 테스트 기관 ", "apba_id": "C0001"})

    assert calls == [{"institution_name": "테스트 기관", "alio_id": "C0001", "year": None}]
    assert result["average_salary"]["amount_krw"] == 70405000

    try:
        tool.handler({"institution_name": "테스트 기관", "unsupported": True})
    except ValueError as exc:
        assert "unsupported get_institution_average_salary arguments" in str(exc)
    else:
        raise AssertionError("expected invalid argument to be rejected")
