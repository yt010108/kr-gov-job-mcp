"""Build institution analysis evidence from live ALIO disclosure data."""

from __future__ import annotations

import asyncio
import html
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

from kr_gov_job_mcp.clients.alio_disclosure_client import (
    AlioDisclosureClient,
    AlioDisclosureClientError,
    AlioDisclosureItemConfig,
)
from kr_gov_job_mcp.codes import find_job_alio_codes
from kr_gov_job_mcp.schemas.alio import AlioInstitution, AlioReportDisclosure, AlioReportSearchResult
from kr_gov_job_mcp.schemas.institution import (
    InstitutionEvidence,
    InstitutionIdentityCandidate,
    InstitutionSignalCandidate,
)


_STRATEGY_ITEM_NUMBERS = ("40", "50-1", "50-2")
_WEAKNESS_ITEM_NUMBERS = ("47-1",)
_MAX_POINT_REPORTS = 5
_MAX_RESEARCH_REPORTS = 5


@dataclass
class AlioInstitutionContext:
    """Evidence bundle resolved from ALIO for one institution."""

    institution_id: str | None = None
    institution_name: str | None = None
    identity_candidates: list[InstitutionIdentityCandidate] = field(default_factory=list)
    evidence: list[InstitutionEvidence] = field(default_factory=list)
    signals: list[InstitutionSignalCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def fetch_alio_institution_context_sync(
    *,
    institution_name: str,
    alio_id: str | None = None,
    year: int | None = None,
) -> AlioInstitutionContext:
    """Fetch ALIO context from a synchronous tool handler."""

    return asyncio.run(
        fetch_alio_institution_context(
            institution_name=institution_name,
            alio_id=alio_id,
            year=year,
        )
    )


async def fetch_alio_institution_context(
    *,
    institution_name: str,
    alio_id: str | None = None,
    year: int | None = None,
    client: AlioDisclosureClient | None = None,
) -> AlioInstitutionContext:
    """Fetch strategy and weakness evidence from ALIO item disclosures."""

    owns_client = client is None
    active_client = client or AlioDisclosureClient()
    context = AlioInstitutionContext()
    retrieved_at = datetime.now(timezone.utc).isoformat()

    try:
        institution, institution_type = await _resolve_institution(
            active_client,
            institution_name=institution_name,
            alio_id=alio_id,
            context=context,
        )
        if institution is None:
            return context

        context.institution_id = institution.id
        context.institution_name = institution.name
        context.identity_candidates.append(
            InstitutionIdentityCandidate(
                name=institution.name or institution_name,
                source_type="alio_disclosure",
                source_id=institution.id,
                code_type="apbaId",
                source_url=institution.source_url,
                confidence="high",
            )
        )

        await _append_main_business_context(
            active_client,
            context,
            institution,
            institution_type,
            year=year,
            retrieved_at=retrieved_at,
        )
        await _append_point_context(
            active_client,
            context,
            institution,
            institution_type,
            year=year,
            retrieved_at=retrieved_at,
        )
        await _append_research_context(
            active_client,
            context,
            institution,
            institution_type,
            year=year,
            retrieved_at=retrieved_at,
        )
    finally:
        if owns_client:
            await active_client.aclose()

    return context


async def _resolve_institution(
    client: AlioDisclosureClient,
    *,
    institution_name: str,
    alio_id: str | None,
    context: AlioInstitutionContext,
) -> tuple[AlioInstitution | None, str | None]:
    institution_type: str | None = None
    selected: AlioInstitution | None = None
    resolver_id = alio_id or _resolve_institution_code_from_lookup(institution_name, context)

    if resolver_id:
        try:
            detail = await client.fetch_institution_detail(resolver_id)
            return detail, _text(detail.raw.get("apbaType"))
        except AlioDisclosureClientError as exc:
            context.warnings.append(
                f"ALIO institution detail failed for resolver code {resolver_id}: {exc}"
            )

    try:
        search = await client.search_institutions(
            keyword=institution_name,
            institution_code=resolver_id,
            page=1,
        )
        selected = _select_institution(search.institutions, institution_name, resolver_id)
        institution_type = _text(selected.raw.get("apbaType")) if selected else None
    except AlioDisclosureClientError as exc:
        context.warnings.append(f"ALIO institution search failed: {exc}")

    target_id = resolver_id or (selected.id if selected else None)
    if not target_id:
        context.warnings.append(f"ALIO institution not found: {institution_name}")
        return None, institution_type

    try:
        detail = await client.fetch_institution_detail(target_id)
    except AlioDisclosureClientError as exc:
        context.warnings.append(f"ALIO institution detail failed for {target_id}: {exc}")
        return selected, institution_type

    return detail, institution_type or _text(detail.raw.get("apbaType"))


def _resolve_institution_code_from_lookup(
    institution_name: str,
    context: AlioInstitutionContext,
) -> str | None:
    matches = find_job_alio_codes(
        code_type="institution",
        query=institution_name,
        limit=1,
    )
    if not matches:
        return None

    candidate, score = matches[0]
    if candidate.code is None:
        context.warnings.append(
            "Job-ALIO 기관명 resolver returned a candidate without code; falling back to ALIO search."
        )
        return None
    if score < 0.9:
        context.warnings.append(
            f"Job-ALIO 기관명 resolver score was low ({score:.2f}); falling back to ALIO search."
        )
        return None
    return candidate.code


def _select_institution(
    institutions: Sequence[AlioInstitution],
    institution_name: str,
    alio_id: str | None,
) -> AlioInstitution | None:
    if alio_id:
        for institution in institutions:
            if institution.id == alio_id:
                return institution
    normalized_target = _normalize_name(institution_name)
    for institution in institutions:
        if _normalize_name(institution.name or "") == normalized_target:
            return institution
    return institutions[0] if institutions else None


async def _append_main_business_context(
    client: AlioDisclosureClient,
    context: AlioInstitutionContext,
    institution: AlioInstitution,
    institution_type: str | None,
    *,
    year: int | None,
    retrieved_at: str,
) -> None:
    item = client.TARGET_ITEM_REPORTS["40"]
    try:
        reports = await _list_context_reports(
            client,
            institution=institution,
            institution_type=institution_type,
            item=item,
            year=year,
        )
    except AlioDisclosureClientError as exc:
        context.warnings.append(f"ALIO item 40 주요사업 failed: {exc}")
        return

    if not reports.reports:
        context.warnings.append("ALIO item 40 주요사업 returned 0 reports")

    selected_reports = _select_reports_for_year(
        reports.reports,
        year=year,
        context=context,
        source_label="ALIO item 40 주요사업",
    )
    report = selected_reports[0] if selected_reports else None
    if year is not None and report is None:
        return
    rows: list[dict[str, Any]] = []
    if report and report.disclosure_no:
        try:
            rows = extract_main_business_rows(await client.fetch_report_html(report.disclosure_no))
        except AlioDisclosureClientError as exc:
            context.warnings.append(f"ALIO item 40 주요사업 html failed: {exc}")

    summary = summarize_main_business(rows, institution.main_business)
    if not summary:
        return

    evidence = InstitutionEvidence(
        title="ALIO 주요사업",
        source_type="alio_disclosure",
        url=report.source_url if report else institution.source_url,
        source_id=report.disclosure_no if report else institution.id,
        excerpt=summary,
        fields={
            "source_type": "major_business",
            "alio_item_no": "40",
            "report_form_root_no": item.report_form_root_no,
            "total_count": reports.total_count,
            "criterion_year": report.criterion_year if report else None,
            "disclosed_date": report.disclosed_date if report else None,
            "business_rows": rows,
            "institution_main_business": institution.main_business,
        },
        collected_at=report.disclosed_date if report else None,
        evidence_year=_report_year(report),
        disclosed_at=_report_disclosed_at(report),
        retrieved_at=retrieved_at,
    )
    context.evidence.append(evidence)
    context.signals.append(
        InstitutionSignalCandidate(
            category="business_direction",
            title="ALIO 주요사업",
            summary=summary,
            evidence=[evidence],
        )
    )


async def _append_point_context(
    client: AlioDisclosureClient,
    context: AlioInstitutionContext,
    institution: AlioInstitution,
    institution_type: str | None,
    *,
    year: int | None,
    retrieved_at: str,
) -> None:
    item = client.TARGET_ITEM_REPORTS["47-1"]
    try:
        reports = await _list_context_reports(
            client,
            institution=institution,
            institution_type=institution_type,
            item=item,
            year=year,
        )
    except AlioDisclosureClientError as exc:
        context.warnings.append(f"ALIO item 47-1 국회지적사항 failed: {exc}")
        return

    selected_reports = _select_reports_for_year(
        reports.reports,
        year=year,
        context=context,
        source_label="ALIO item 47-1 국회지적사항",
    )
    if not selected_reports:
        if not reports.reports:
            context.warnings.append("ALIO item 47-1 국회지적사항 returned 0 reports")
        return

    for report in selected_reports[:_MAX_POINT_REPORTS]:
        fields: dict[str, str] = {}
        try:
            fields = extract_board_fields(await client.fetch_board_report_html(report))
        except AlioDisclosureClientError as exc:
            context.warnings.append(f"ALIO item 47-1 board html failed: {exc}")

        point_text = fields.get("지적사항") or report.title or "국회지적사항"
        plan_text = fields.get("시정조치 계획") or fields.get("시정조치계획")
        excerpt = point_text if not plan_text else f"{point_text} / 조치계획: {plan_text}"
        evidence = _report_evidence(
            report,
            title=report.title or "ALIO 국회지적사항",
            excerpt=excerpt,
            source_type="audit_point",
            item_no="47-1",
            total_count=reports.total_count,
            retrieved_at=retrieved_at,
            extra_fields={"board_fields": fields},
        )
        context.evidence.append(evidence)
        context.signals.append(
            InstitutionSignalCandidate(
                category="improvement_task",
                title=report.title or "ALIO 국회지적사항",
                summary=point_text,
                evidence=[evidence],
            )
        )


async def _append_research_context(
    client: AlioDisclosureClient,
    context: AlioInstitutionContext,
    institution: AlioInstitution,
    institution_type: str | None,
    *,
    year: int | None,
    retrieved_at: str,
) -> None:
    reports_by_item: list[tuple[str, AlioReportDisclosure, int | None]] = []
    for item_no in ("50-1", "50-2"):
        item = client.TARGET_ITEM_REPORTS[item_no]
        try:
            reports = await _list_context_reports(
                client,
                institution=institution,
                institution_type=institution_type,
                item=item,
                year=year,
            )
        except AlioDisclosureClientError as exc:
            context.warnings.append(f"ALIO item {item_no} {item.name} failed: {exc}")
            continue
        selected_reports = _select_reports_for_year(
            reports.reports,
            year=year,
            context=context,
            source_label=f"ALIO item {item_no} {item.name}",
        )
        if not selected_reports:
            if not reports.reports:
                context.warnings.append(f"ALIO item {item_no} {item.name} returned 0 reports")
            continue
        reports_by_item.extend(
            (item_no, report, reports.total_count) for report in selected_reports
        )

    for item_no, report, total_count in reports_by_item[:_MAX_RESEARCH_REPORTS]:
        item = client.TARGET_ITEM_REPORTS[item_no]
        title = report.title or item.name
        excerpt = f"{item.name}: {title}"
        if report.disclosed_date:
            excerpt = f"{excerpt} ({report.disclosed_date})"
        evidence = _report_evidence(
            report,
            title=title,
            excerpt=excerpt,
            source_type="policy_research",
            item_no=item_no,
            total_count=total_count,
            retrieved_at=retrieved_at,
            extra_fields={"research_kind": item.name},
        )
        context.evidence.append(evidence)
        context.signals.append(
            InstitutionSignalCandidate(
                category="job_connection",
                title=title,
                summary=(
                    f"연구보고서 소재로 직무 관심과 기여 의지를 연결할 수 있습니다: {title}"
                ),
                evidence=[evidence],
            )
        )


def _report_evidence(
    report: AlioReportDisclosure,
    *,
    title: str,
    excerpt: str,
    source_type: str,
    item_no: str,
    total_count: int | None,
    retrieved_at: str,
    extra_fields: dict[str, Any] | None = None,
) -> InstitutionEvidence:
    fields = {
        "source_type": source_type,
        "alio_item_no": item_no,
        "report_form_no": report.report_form_no,
        "total_count": total_count,
        "criterion_year": report.criterion_year,
        "disclosed_date": report.disclosed_date,
    }
    if extra_fields:
        fields.update(extra_fields)
    return InstitutionEvidence(
        title=title,
        source_type="alio_disclosure",
        url=report.source_url,
        source_id=_report_source_id(report),
        collected_at=report.disclosed_date,
        evidence_year=_report_year(report),
        disclosed_at=_report_disclosed_at(report),
        retrieved_at=retrieved_at,
        excerpt=excerpt,
        fields=fields,
    )


async def _list_context_reports(
    client: AlioDisclosureClient,
    *,
    institution: AlioInstitution,
    institution_type: str | None,
    item: AlioDisclosureItemConfig,
    year: int | None,
) -> AlioReportSearchResult:
    first_page = await client.list_item_reports(
        institution_code=institution.id,
        institution_type=institution_type,
        item=item,
    )
    if year is None or item.kind == "regular":
        return first_page

    reports = list(first_page.reports)
    total_count = first_page.total_count or len(reports)
    page = 2
    while reports and len(reports) < total_count:
        next_page = await client.list_item_reports(
            institution_code=institution.id,
            institution_type=institution_type,
            item=item,
            page=page,
        )
        if not next_page.reports:
            break
        reports.extend(next_page.reports)
        total_count = max(total_count, next_page.total_count or 0)
        page += 1

    return first_page.model_copy(update={"reports": reports, "total_count": total_count})


def _select_reports_for_year(
    reports: Sequence[AlioReportDisclosure],
    *,
    year: int | None,
    context: AlioInstitutionContext,
    source_label: str,
) -> list[AlioReportDisclosure]:
    if year is None:
        for report in reports:
            if report.disclosed_date and _report_year_from_disclosed_date(report) is None:
                context.warnings.append(
                    f"{source_label} report {_report_source_id(report) or report.title or 'unknown'} "
                    f"has malformed disclosed date {report.disclosed_date!r}; "
                    "its evidence time needs verification."
                )
        return list(reports)

    selected: list[AlioReportDisclosure] = []
    for report in reports:
        evidence_year = _report_year(report)
        if evidence_year is None:
            context.warnings.append(
                f"{source_label} report {_report_source_id(report) or report.title or 'unknown'} "
                f"has no usable criterion year or disclosed date {report.disclosed_date!r}; "
                f"it cannot satisfy requested year {year}."
            )
        elif evidence_year == year:
            selected.append(report)

    if reports and not selected:
        context.warnings.append(
            f"{source_label} has reports but none match requested year {year}; no fallback was used."
        )
    return selected


def _report_disclosed_at(report: AlioReportDisclosure | None) -> str | None:
    if report is None:
        return None
    return _normalize_disclosed_at(report.disclosed_date)[0]


def _report_year(report: AlioReportDisclosure | None) -> int | None:
    if report is None:
        return None
    if report.criterion_year is not None:
        return report.criterion_year
    return _report_year_from_disclosed_date(report)


def _report_year_from_disclosed_date(report: AlioReportDisclosure) -> int | None:
    return _normalize_disclosed_at(report.disclosed_date)[1]


def _normalize_disclosed_at(value: str | None) -> tuple[str | None, int | None]:
    if not value:
        return None, None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        match = re.fullmatch(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
        if not match:
            return None, None
        try:
            parsed = datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
        except ValueError:
            return None, None
    # A calendar date or timezone-naive datetime does not identify an instant.
    # Preserve its year for selection, but do not invent an offset for disclosed_at.
    if parsed.tzinfo is None:
        return None, parsed.year
    return parsed.isoformat(), parsed.year


def extract_main_business_rows(html_text: str) -> list[dict[str, Any]]:
    """Extract the ALIO 40 주요사업 budget table into structured rows."""

    parser = _TableTextParser()
    parser.feed(html_text)
    rows = parser.rows
    header_index = next(
        (index for index, row in enumerate(rows) if row and row[0] == "사업구분"),
        None,
    )
    if header_index is None:
        return []

    headers = rows[header_index]
    parsed_rows: list[dict[str, Any]] = []
    for row in rows[header_index + 1 :]:
        if not row or row[0] in {"기준일", "기관 공시 담당자", "구분"}:
            break
        if len(row) < 2:
            continue
        amounts = {
            header: _parse_amount(cell)
            for header, cell in zip(headers[1:], row[1:], strict=False)
            if "결산" in header or "예산" in header
        }
        amount_values = [(header, value) for header, value in amounts.items() if value is not None]
        if not amount_values:
            continue
        latest_header, latest_amount = amount_values[-1]
        previous_header, previous_amount = amount_values[-2] if len(amount_values) >= 2 else (None, None)
        growth_amount = (
            latest_amount - previous_amount
            if latest_amount is not None and previous_amount not in (None, 0)
            else None
        )
        growth_rate = (
            growth_amount / previous_amount
            if growth_amount is not None and previous_amount not in (None, 0)
            else None
        )
        parsed_rows.append(
            {
                "name": row[0],
                "amounts": amounts,
                "latest_header": latest_header,
                "latest_amount": latest_amount,
                "previous_header": previous_header,
                "previous_amount": previous_amount,
                "growth_amount": growth_amount,
                "growth_rate": growth_rate,
            }
        )
    return parsed_rows


def summarize_main_business(
    rows: Sequence[dict[str, Any]],
    institution_main_business: str | None,
) -> str | None:
    """Summarize scale and growth from ALIO 40 rows."""

    if not rows:
        return _trim(institution_main_business, limit=240)

    latest_rows = [row for row in rows if isinstance(row.get("latest_amount"), int)]
    largest = max(latest_rows, key=lambda row: row["latest_amount"]) if latest_rows else None
    growth_rows = [
        row
        for row in rows
        if isinstance(row.get("growth_amount"), int) and row.get("growth_rate") is not None
    ]
    fastest = max(growth_rows, key=lambda row: row["growth_rate"]) if growth_rows else None

    parts: list[str] = []
    if largest:
        parts.append(
            f"가장 큰 규모는 {largest['name']}으로 "
            f"{largest['latest_header']} {largest['latest_amount']:,}백만원입니다."
        )
    if fastest:
        parts.append(
            f"가장 높은 성장성은 {fastest['name']}으로 "
            f"{fastest['previous_header']} 대비 {fastest['latest_header']} "
            f"{fastest['growth_amount']:+,}백만원({fastest['growth_rate']:+.1%})입니다."
        )
    if institution_main_business:
        parts.append(f"기관 상세 주요사업: {_trim(institution_main_business, limit=180)}")
    return " ".join(parts) if parts else None


def extract_board_fields(html_text: str) -> dict[str, str]:
    """Extract label/value pairs from an ALIO board detail page."""

    fields: dict[str, str] = {}
    pattern = re.compile(
        r"<li>\s*<p class=\"tit\">.*?<span>\s*(?P<label>[^<]+?)\s*</span>.*?</p>"
        r"\s*<div class=\"con\">(?P<value>.*?)</div>\s*</li>",
        re.DOTALL,
    )
    for match in pattern.finditer(html_text):
        label = _clean_html(match.group("label"))
        value = _clean_html(match.group("value"))
        if label and value:
            fields[label] = value
    return fields


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
            self._current_row.append(_collapse_text("".join(self._current_cell)))
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            if any(self._current_row):
                self.rows.append(self._current_row)
            self._current_row = None


def _clean_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    return _collapse_text(html.unescape(value))


def _report_source_id(report: AlioReportDisclosure) -> str | None:
    if report.disclosure_no and set(report.disclosure_no) != {"0"}:
        return report.disclosure_no
    return report.submission_no or report.disclosure_no or None


def _collapse_text(value: str) -> str:
    return " ".join(value.replace("\r", "\n").split())


def _parse_amount(value: str) -> int | None:
    normalized = value.replace(",", "").strip()
    if normalized in {"", "-"}:
        return None
    try:
        return int(normalized)
    except ValueError:
        return None


def _trim(value: str | None, *, limit: int) -> str | None:
    if not value:
        return None
    text = _collapse_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
