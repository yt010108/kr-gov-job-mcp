import asyncio
from datetime import datetime
from inspect import signature

from kr_gov_job_mcp.analysis.alio_institution_context import (
    extract_board_fields,
    extract_main_business_rows,
    fetch_alio_institution_context,
    fetch_alio_institution_context_sync,
    summarize_main_business,
)
from kr_gov_job_mcp.clients.alio_disclosure_client import AlioDisclosureClient
from kr_gov_job_mcp.schemas.alio import (
    AlioInstitution,
    AlioReportDisclosure,
    AlioReportSearchResult,
)


class _FakeAlioClient:
    TARGET_ITEM_REPORTS = AlioDisclosureClient.TARGET_ITEM_REPORTS

    def __init__(self, reports_by_item: dict[str, list[AlioReportDisclosure]]) -> None:
        self._reports_by_item = reports_by_item

    async def fetch_institution_detail(self, institution_code: str) -> AlioInstitution:
        return AlioInstitution(
            id=institution_code,
            name="테스트 기관",
            main_business="연도와 무관한 기관 상세 주요사업",
            raw={"apbaType": "기금관리형"},
        )

    async def list_item_reports(self, *, item, **_kwargs) -> AlioReportSearchResult:  # type: ignore[no-untyped-def]
        reports = self._reports_by_item.get(item.item_no, [])
        return AlioReportSearchResult(
            report_form_root_no=item.report_form_root_no,
            total_count=len(reports),
            reports=reports,
        )

    async def fetch_report_html(self, _disclosure_no: str) -> str:
        return """
        <table>
          <tr><th>사업구분</th><th>2024년 결산</th><th>2025년 예산</th></tr>
          <tr><td>핵심사업</td><td>100</td><td>200</td></tr>
        </table>
        """

    async def fetch_board_report_html(self, _report: AlioReportDisclosure) -> str:
        return """
        <li><p class="tit"><span>지적사항</span></p>
        <div class="con"><p>개선이 필요한 사항</p></div></li>
        """


class _PagedFakeAlioClient(_FakeAlioClient):
    def __init__(self, pages_by_item: dict[str, list[list[AlioReportDisclosure]]]) -> None:
        super().__init__({})
        self._pages_by_item = pages_by_item
        self.requested_pages: list[tuple[str, int]] = []

    async def list_item_reports(
        self, *, item, page: int = 1, **_kwargs
    ) -> AlioReportSearchResult:  # type: ignore[no-untyped-def]
        self.requested_pages.append((item.item_no, page))
        pages = self._pages_by_item.get(item.item_no, [])
        reports = pages[page - 1] if page <= len(pages) else []
        return AlioReportSearchResult(
            report_form_root_no=item.report_form_root_no,
            page=page,
            total_count=sum(len(current_page) for current_page in pages),
            reports=reports,
        )


def _report(
    disclosure_no: str,
    disclosed_date: str | None,
    *,
    criterion_year: int | None = None,
) -> AlioReportDisclosure:
    return AlioReportDisclosure(
        disclosure_no=disclosure_no,
        title=disclosure_no,
        criterion_year=criterion_year,
        disclosed_date=disclosed_date,
        report_form_no="FORM",
        source_url=f"https://alio.go.kr/{disclosure_no}",
    )


def _fetch_context(
    reports_by_item: dict[str, list[AlioReportDisclosure]],
    *,
    year: int | None,
    client: _FakeAlioClient | None = None,
):
    return asyncio.run(
        fetch_alio_institution_context(
            institution_name="테스트 기관",
            alio_id="C0001",
            year=year,
            client=client or _FakeAlioClient(reports_by_item),
        )
    )


def test_extract_main_business_rows_and_summary() -> None:
    html = """
    <table>
      <tr>
        <th>사업구분</th><th>2025년 결산</th><th>2026년 예산</th><th>비고</th>
      </tr>
      <tr>
        <td>운영</td><td>6,806</td><td>8,966</td><td>운영.hwp</td>
      </tr>
      <tr>
        <td>사업<br/>수탁사업</td><td>50,448</td><td>56,012</td><td>사업.hwp</td>
      </tr>
      <tr><td>기준일</td><td>2025년 12월 31일</td></tr>
    </table>
    """

    rows = extract_main_business_rows(html)
    summary = summarize_main_business(rows, "보건의료데이터 표준화")

    assert rows[0]["name"] == "운영"
    assert rows[0]["growth_amount"] == 2160
    assert rows[1]["name"] == "사업 수탁사업"
    assert rows[1]["latest_amount"] == 56012
    assert summary is not None
    assert "가장 큰 규모는 사업 수탁사업" in summary
    assert "가장 높은 성장성은 운영" in summary


def test_extract_board_fields_keeps_point_and_action_plan_separate() -> None:
    html = """
    <li>
      <p class="tit"><span>지적사항</span></p>
      <div class="con"><div class="terms-list"><p>데이터가 안전하게 관리될 수 있도록 노력할 것</p></div></div>
    </li>
    <li>
      <p class="tit"><span>지적사항 첨부파일</span></p>
      <div class="con"><div class="bt-list"><p><a>지적사항.hwpx</a></p></div></div>
    </li>
    <li>
      <p class="tit"><span>시정조치 계획</span></p>
      <div class="con"><div class="terms-list"><p>DR센터 구축 컨설팅 추진<br/>후속 예산확보</p></div></div>
    </li>
    """

    fields = extract_board_fields(html)

    assert fields["지적사항"] == "데이터가 안전하게 관리될 수 있도록 노력할 것"
    assert fields["지적사항 첨부파일"] == "지적사항.hwpx"
    assert fields["시정조치 계획"] == "DR센터 구축 컨설팅 추진 후속 예산확보"


def test_context_year_filter_keeps_source_order_and_provenance() -> None:
    context = _fetch_context(
        {
            "40": [_report("main-2024", "2024-12-31"), _report("main-2025", "2025.01.02")],
            "47-1": [
                _report("point-2024", "2024-12-31"),
                _report("point-2025-a", "2025-02-03"),
                _report("point-2025-b", "2025-02-04"),
                _report("point-2025-c", "2025-02-05"),
                _report("point-2025-d", "2025-02-06"),
                _report("point-2025-e", "2025-02-07"),
                _report("point-2025-f", "2025-02-08"),
            ],
            "50-1": [
                _report("research-2024", "2024-12-31"),
                _report("research-50-1-a", "2025-03-04"),
                _report("research-50-1-b", "2025-03-05"),
                _report("research-50-1-c", "2025-03-06"),
                _report("research-50-1-d", "2025-03-07"),
            ],
            "50-2": [
                _report("research-50-2-a", "2025-04-06"),
                _report("research-50-2-b", "2025-04-07"),
            ],
        },
        year=2025,
    )

    assert [evidence.source_id for evidence in context.evidence] == [
        "main-2025",
        "point-2025-a",
        "point-2025-b",
        "point-2025-c",
        "point-2025-d",
        "point-2025-e",
        "research-50-1-a",
        "research-50-1-b",
        "research-50-1-c",
        "research-50-1-d",
        "research-50-2-a",
    ]
    assert {evidence.evidence_year for evidence in context.evidence} == {2025}
    assert context.evidence[0].collected_at == "2025.01.02"
    assert all(
        evidence.collected_at == evidence.fields["disclosed_date"]
        for evidence in context.evidence
    )
    assert all(
        datetime.fromisoformat(evidence.retrieved_at or "").tzinfo is not None
        for evidence in context.evidence
    )
    assert all(evidence.disclosed_at is None for evidence in context.evidence)
    assert context.evidence[0].fields["disclosed_date"] == "2025.01.02"


def test_context_year_filter_uses_regular_criterion_year_without_inventing_timestamp() -> None:
    regular_report = AlioDisclosureClient.normalize_report_disclosure(
        {
            "apbaId": "C0001",
            "apbaNa": "테스트 기관",
            "reportFormNo": "31501",
            "critYyyy": "2025",
            "submissionNo": "2026041310382324",
            "disclosureNo": "2026041303151983",
        },
        source_url="https://alio.go.kr/2026041303151983",
    )

    context = _fetch_context({"40": [regular_report]}, year=2025)

    evidence = context.evidence[0]
    assert evidence.source_id == "2026041303151983"
    assert evidence.evidence_year == 2025
    assert evidence.fields["criterion_year"] == 2025
    assert evidence.fields["disclosed_date"] is None
    assert evidence.disclosed_at is None
    assert evidence.collected_at is None
    assert datetime.fromisoformat(evidence.retrieved_at or "").tzinfo is not None
    assert not any("no fallback was used" in warning for warning in context.warnings)


def test_context_preserves_timezone_aware_disclosed_timestamp() -> None:
    context = _fetch_context(
        {"40": [_report("main-2025", "2025-01-02T09:30:00+09:00")]},
        year=2025,
    )

    evidence = context.evidence[0]
    assert evidence.evidence_year == 2025
    assert evidence.disclosed_at == "2025-01-02T09:30:00+09:00"
    assert evidence.collected_at == "2025-01-02T09:30:00+09:00"


def test_context_without_year_keeps_existing_source_order() -> None:
    context = _fetch_context(
        {
            "40": [_report("main-first", "2024-12-31"), _report("main-second", "2025-01-02")],
            "47-1": [_report("point-first", "2024-12-31"), _report("point-second", "2025-02-03")],
            "50-1": [_report("research-50-1-first", "2024-12-31")],
            "50-2": [_report("research-50-2-first", "2025-04-06")],
        },
        year=None,
    )

    assert [evidence.source_id for evidence in context.evidence] == [
        "main-first",
        "point-first",
        "point-second",
        "research-50-1-first",
        "research-50-2-first",
    ]
    assert not any("no fallback was used" in warning for warning in context.warnings)


def test_context_year_filter_reads_later_occasional_pages() -> None:
    client = _PagedFakeAlioClient(
        {
            "40": [[_report("main-2025", "2025-01-02")]],
            "47-1": [
                [_report("point-2026", "2026-02-03")],
                [_report("point-2025", "2025-02-04")],
            ],
            "50-1": [
                [_report("research-2026", "2026-03-05")],
                [_report("research-2025", "2025-03-06")],
            ],
            "50-2": [[]],
        }
    )

    context = _fetch_context({}, year=2025, client=client)

    assert [evidence.source_id for evidence in context.evidence] == [
        "main-2025",
        "point-2025",
        "research-2025",
    ]
    assert ("47-1", 2) in client.requested_pages
    assert ("50-1", 2) in client.requested_pages


def test_context_year_filter_warns_and_does_not_fall_back_to_other_year() -> None:
    context = _fetch_context(
        {
            "40": [_report("main-2024", "2024-12-31")],
            "47-1": [_report("point-2024", "2024-12-31")],
            "50-1": [_report("research-50-1-2024", "2024-12-31")],
            "50-2": [_report("research-50-2-2024", "2024-12-31")],
        },
        year=2025,
    )

    assert context.evidence == []
    assert all("none match requested year 2025; no fallback was used" in warning for warning in context.warnings)
    assert len(context.warnings) == 4


def test_context_year_filter_warns_for_malformed_disclosed_date() -> None:
    context = _fetch_context(
        {"40": [_report("main-unknown", "not-a-date")]},
        year=2025,
    )

    assert context.evidence == []
    assert any("no usable criterion year or disclosed date 'not-a-date'" in warning for warning in context.warnings)
    assert any(
        "ALIO item 40 주요사업 has reports but none match requested year 2025" in warning
        for warning in context.warnings
    )


def test_context_warns_when_main_business_reports_are_empty() -> None:
    context = _fetch_context({}, year=2025)

    assert context.evidence == []
    assert "ALIO item 40 주요사업 returned 0 reports" in context.warnings


def test_context_without_year_keeps_malformed_report_and_warns_for_provenance() -> None:
    context = _fetch_context(
        {"40": [_report("main-unknown", "not-a-date")]},
        year=None,
    )

    evidence = context.evidence[0]
    assert evidence.source_id == "main-unknown"
    assert evidence.evidence_year is None
    assert evidence.disclosed_at is None
    assert any("has malformed disclosed date 'not-a-date'" in warning for warning in context.warnings)


def test_context_fetch_functions_accept_optional_year() -> None:
    assert "year" in signature(fetch_alio_institution_context).parameters
    assert "year" in signature(fetch_alio_institution_context_sync).parameters
