from pathlib import Path


def test_collector_workflow_doc_covers_required_sources() -> None:
    text = Path("docs/collector-workflow.md").read_text(encoding="utf-8")

    for phrase in [
        "로컬 준비",
        "Raw Sample 저장 규칙",
        "필드 인벤토리 작성 규칙",
        "Job-ALIO",
        "ALIO 경영공시",
        "Cleaneye",
        "데모 재현 흐름",
    ]:
        assert phrase in text


def test_readme_links_collector_workflow_doc() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "docs/collector-workflow.md" in text


def test_career_coach_persona_report_references_fixture_and_findings() -> None:
    report = Path("docs/career-coach-persona-test-report.md").read_text(encoding="utf-8")

    assert "../examples/career-coach-personas.json" in report
    assert "../tests/test_public_job_career_coach_execution.py" in report
    for phrase in [
        "beginner_minji",
        "job_search_junho",
        "application_seoyeon",
        "interview_hyeonu",
        "missing_information_jisu",
        "partial_salary_taehun",
        "missing_information_echoes_free_text = true",
        "downstream_error_echoes_secret_text = true",
        "deadline_this_month",
        "MCP Player",
    ]:
        assert phrase in report


def test_alio_pagination_policy_doc_covers_high_volume_controls() -> None:
    text = Path("docs/archive/alio-pagination-policy.md").read_text(encoding="utf-8")

    for phrase in [
        "raw_observation",
        "full_collection",
        "resume_collection",
        "B1030",
        "high_volume_threshold",
        "rate_limited",
        "checkpoint",
        "page metadata",
        "stopped_reason",
    ]:
        assert phrase in text


def test_job_alio_alio_b1020_linking_doc_covers_statuses() -> None:
    text = Path("docs/archive/job-alio-alio-b1020-linking.md").read_text(encoding="utf-8")

    for phrase in [
        "B1020",
        "JobPostingSourceLink",
        "exact_match",
        "strong_candidate",
        "needs_review",
        "source_only_job_alio",
        "source_only_alio",
        "conflict",
        "EvidenceSource",
        "pblntInstCd",
        "apbaId",
    ]:
        assert phrase in text


def test_source_data_erd_doc_covers_core_entities() -> None:
    text = Path("docs/archive/source-data-erd.md").read_text(encoding="utf-8")

    for phrase in [
        "erDiagram",
        "RawSample",
        "Institution",
        "JobPosting",
        "JobPostingAttachment",
        "AlioDisclosureItem",
        "DisclosureReport",
        "DisclosureAttachment",
        "EvidenceSource",
        "disclosureNo",
        "submissionNo",
        "idx",
        "NCS",
    ]:
        assert phrase in text


def test_cleaneye_html_structure_doc_covers_parser_targets() -> None:
    text = Path("docs/archive/cleaneye-html-structure.md").read_text(encoding="utf-8")

    for phrase in [
        "일반현황",
        "경영평가등급",
        "부채규모",
        "사업보고서",
        "신규투자사업",
        "entId",
        "insttCode",
        "공통 파서와 전용 파서 판단",
        "기관 분석 입력 후보",
    ]:
        assert phrase in text


def test_alio_html_structure_doc_covers_parser_targets() -> None:
    text = Path("docs/archive/alio-html-structure.md").read_text(encoding="utf-8")

    for phrase in [
        "B1020",
        "31501",
        "B1210",
        "B1030",
        "7030",
        "B1040",
        "B1260",
        "Parser 구현 범위",
        "ERD/기관분석 입력 승격 후보",
    ]:
        assert phrase in text
