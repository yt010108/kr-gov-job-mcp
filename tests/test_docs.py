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


def test_cleaneye_html_structure_doc_covers_parser_targets() -> None:
    text = Path("docs/cleaneye-html-structure.md").read_text(encoding="utf-8")

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
    text = Path("docs/alio-html-structure.md").read_text(encoding="utf-8")

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
