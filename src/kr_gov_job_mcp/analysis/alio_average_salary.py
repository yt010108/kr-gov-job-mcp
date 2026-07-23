"""Read employee average compensation from ALIO regular disclosures."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from kr_gov_job_mcp.clients.alio_disclosure_client import (
    AlioDisclosureClient,
    AlioDisclosureClientError,
)
from kr_gov_job_mcp.schemas.alio import AlioInstitution, AlioReportDisclosure


_AVERAGE_COMPENSATION_LABELS = frozenset({"1인당평균보수", "1인당평균보수액"})
_YEAR_HEADER_RE = re.compile(r"(?P<year>(?:19|20)\d{2})\s*년?\s*(?P<basis>결산|예산)?")


@dataclass(frozen=True)
class AverageSalaryRecord:
    """One annual average-compensation value disclosed by ALIO."""

    year: int
    amount_thousand_krw: int
    basis: str | None
    header: str
    label: str
    employment_group: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "amount_krw": self.amount_thousand_krw * 1_000,
            "amount_thousand_krw": self.amount_thousand_krw,
            "basis": self.basis,
            "header": self.header,
            "label": self.label,
            "employment_group": self.employment_group,
            "unit": "KRW",
        }


@dataclass
class AlioAverageSalaryResult:
    """Average-salary data and provenance for one ALIO institution."""

    institution_id: str | None = None
    institution_name: str | None = None
    requested_year: int | None = None
    records: list[AverageSalaryRecord] = field(default_factory=list)
    report: AlioReportDisclosure | None = None
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        selected = self._selected_record()
        report = self.report
        return {
            "source": "alio_regular_disclosure",
            "query": {
                "institution_name": self.institution_name,
                "alio_id": self.institution_id,
                "year": self.requested_year,
            },
            "institution": {
                "id": self.institution_id,
                "name": self.institution_name,
            },
            "average_salary": selected.as_dict() if selected else None,
            "salary_history": [record.as_dict() for record in self.records],
            "report": {
                "name": "직원 평균보수",
                "report_form_root_no": AlioDisclosureClient.AVERAGE_SALARY_REPORT_FORM_ROOT_NO,
                "report_form_no": report.report_form_no if report else None,
                "criterion_year": report.criterion_year if report else None,
                "disclosure_no": report.disclosure_no if report else None,
                "source_url": report.source_url if report else None,
            },
            "warnings": self.warnings,
        }

    def _selected_record(self) -> AverageSalaryRecord | None:
        if self.requested_year is not None:
            return next((record for record in self.records if record.year == self.requested_year), None)
        completed = [record for record in self.records if record.basis == "결산"]
        if completed:
            return max(completed, key=lambda record: record.year)
        return max(self.records, key=lambda record: record.year, default=None)


def fetch_alio_average_salary_sync(
    *,
    institution_name: str,
    alio_id: str | None = None,
    year: int | None = None,
) -> AlioAverageSalaryResult:
    """Fetch ALIO average compensation from a synchronous MCP tool handler."""

    return asyncio.run(
        fetch_alio_average_salary(
            institution_name=institution_name,
            alio_id=alio_id,
            year=year,
        )
    )


async def fetch_alio_average_salary(
    *,
    institution_name: str,
    alio_id: str | None = None,
    year: int | None = None,
    client: AlioDisclosureClient | None = None,
) -> AlioAverageSalaryResult:
    """Fetch the ALIO 2060 average-compensation disclosure for one institution."""

    owns_client = client is None
    active_client = client or AlioDisclosureClient()
    result = AlioAverageSalaryResult(requested_year=year)
    try:
        institution = await _resolve_institution(
            active_client,
            institution_name=institution_name,
            alio_id=alio_id,
            warnings=result.warnings,
        )
        if institution is None:
            return result

        result.institution_id = institution.id
        result.institution_name = institution.name or institution_name
        try:
            reports = await active_client.list_regular_item_reports(
                institution_code=institution.id,
                report_form_root_no=AlioDisclosureClient.AVERAGE_SALARY_REPORT_FORM_ROOT_NO,
            )
        except AlioDisclosureClientError as exc:
            result.warnings.append(f"ALIO 직원 평균보수 report list failed: {exc}")
            return result

        report = next((item for item in reports.reports if item.disclosure_no), None)
        if report is None:
            result.warnings.append("ALIO 직원 평균보수 returned 0 reports")
            return result
        result.report = report
        try:
            report_html = await active_client.fetch_report_html(report.disclosure_no)
        except AlioDisclosureClientError as exc:
            result.warnings.append(f"ALIO 직원 평균보수 html failed: {exc}")
            return result

        result.records = extract_average_salary_records(report_html)
        if not result.records:
            result.warnings.append("ALIO 직원 평균보수 table had no usable 1인당 평균 보수 values")
        elif year is not None and not any(record.year == year for record in result.records):
            result.warnings.append(
                f"ALIO 직원 평균보수 has no value for requested year {year}; no fallback was used."
            )
        elif year is None and not any(record.basis == "결산" for record in result.records):
            result.warnings.append(
                "ALIO 직원 평균보수 has no 결산 value; the latest available estimate was selected."
            )
    finally:
        if owns_client:
            await active_client.aclose()
    return result


async def _resolve_institution(
    client: AlioDisclosureClient,
    *,
    institution_name: str,
    alio_id: str | None,
    warnings: list[str],
) -> AlioInstitution | None:
    if alio_id:
        try:
            return await client.fetch_institution_detail(alio_id)
        except AlioDisclosureClientError as exc:
            warnings.append(f"ALIO institution detail failed for {alio_id}: {exc}")

    try:
        search = await client.search_institutions(keyword=institution_name, institution_code=alio_id)
    except AlioDisclosureClientError as exc:
        warnings.append(f"ALIO institution search failed: {exc}")
        return None

    selected = _select_institution(search.institutions, institution_name, alio_id)
    if selected is None:
        warnings.append(f"ALIO institution not found: {institution_name}")
        return None
    try:
        return await client.fetch_institution_detail(selected.id)
    except AlioDisclosureClientError as exc:
        warnings.append(f"ALIO institution detail failed for {selected.id}: {exc}")
        return selected


def extract_average_salary_records(html_text: str) -> list[AverageSalaryRecord]:
    """Extract the 1인당 평균 보수 row from ALIO's regular-disclosure table."""

    rows = _extract_table_rows(html_text)
    records: list[AverageSalaryRecord] = []
    for row_index, row in enumerate(rows):
        if not row or _normalize_label(row[0]) not in _AVERAGE_COMPENSATION_LABELS:
            continue
        header_match = _nearest_year_headers(rows, row_index)
        if header_match is None:
            continue
        header_index, headers = header_match
        employment_group = _nearest_employment_group(rows, header_index)
        for header, value in zip(headers[1:], row[1:], strict=False):
            match = _YEAR_HEADER_RE.search(header)
            amount = _parse_amount(value)
            if match is None or amount is None:
                continue
            records.append(
                AverageSalaryRecord(
                    year=int(match.group("year")),
                    amount_thousand_krw=amount,
                    basis=match.group("basis"),
                    header=header,
                    label=row[0],
                    employment_group=employment_group,
                )
            )
    return records


def _nearest_year_headers(
    rows: Sequence[list[str]], row_index: int
) -> tuple[int, list[str]] | None:
    for candidate_index in range(row_index - 1, -1, -1):
        candidate = rows[candidate_index]
        if sum(_YEAR_HEADER_RE.search(cell) is not None for cell in candidate[1:]) >= 1:
            return candidate_index, candidate
    return None


def _nearest_employment_group(rows: Sequence[list[str]], header_index: int) -> str | None:
    for candidate in reversed(rows[max(0, header_index - 4) : header_index]):
        if not candidate or len(candidate) > 2:
            continue
        label = candidate[0]
        if _normalize_label(label) in {"", "구분"} or _YEAR_HEADER_RE.search(label):
            continue
        return label
    return None


def _select_institution(
    institutions: Sequence[AlioInstitution],
    institution_name: str,
    alio_id: str | None,
) -> AlioInstitution | None:
    if alio_id:
        matching_id = next((item for item in institutions if item.id == alio_id), None)
        if matching_id is not None:
            return matching_id
    normalized_name = _normalize_label(institution_name)
    exact = next(
        (item for item in institutions if _normalize_label(item.name or "") == normalized_name),
        None,
    )
    return exact or (institutions[0] if institutions else None)


class _TableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = []
        elif tag == "br" and self._current_cell is not None:
            self._current_cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._current_row is not None and self._current_cell is not None:
            self._current_row.append(" ".join("".join(self._current_cell).split()))
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            if any(self._current_row):
                self.rows.append(self._current_row)
            self._current_row = None


def _extract_table_rows(html_text: str) -> list[list[str]]:
    parser = _TableTextParser()
    parser.feed(html_text)
    return parser.rows


def _normalize_label(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", value).casefold()


def _parse_amount(value: str) -> int | None:
    normalized = value.replace(",", "").strip()
    if normalized in {"", "-"}:
        return None
    try:
        return int(normalized)
    except ValueError:
        return None
