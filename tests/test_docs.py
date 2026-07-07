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


def test_alio_pagination_policy_doc_covers_high_volume_controls() -> None:
    text = Path("docs/alio-pagination-policy.md").read_text(encoding="utf-8")

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
