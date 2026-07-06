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
        "기관 채용 페이지",
        "보도자료",
        "데모 재현 흐름",
    ]:
        assert phrase in text


def test_readme_links_collector_workflow_doc() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "docs/collector-workflow.md" in text
