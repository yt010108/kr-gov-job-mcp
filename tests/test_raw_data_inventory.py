import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_raw_data_inventory_example_has_expected_sources_and_types() -> None:
    payload = json.loads((ROOT / "examples" / "raw-data-inventory.json").read_text(encoding="utf-8"))

    assert payload["inventory_version"] == "2026-07-07"
    assert set(payload["raw_sample_types"]) == {
        "list",
        "detail",
        "attachment",
        "html",
        "pdf_text",
        "api_response",
        "metadata",
        "other",
    }
    assert {source["source"] for source in payload["sources"]} == {
        "job_alio",
        "alio_disclosure",
        "cleaneye",
        "career_page",
    }


def test_each_inventory_source_separates_observed_and_candidate_fields() -> None:
    payload = json.loads((ROOT / "examples" / "raw-data-inventory.json").read_text(encoding="utf-8"))

    for source in payload["sources"]:
        assert source["stable_fields"]
        assert "often_missing_fields" in source
        assert "source_specific_fields" in source
        assert source["temporary_normalized_candidates"]
        assert set(source["raw_types"]).issubset(set(payload["raw_sample_types"]))


def test_inventory_doc_mentions_every_source_and_raw_type() -> None:
    payload = json.loads((ROOT / "examples" / "raw-data-inventory.json").read_text(encoding="utf-8"))
    doc = (ROOT / "docs" / "raw-data-inventory.md").read_text(encoding="utf-8")

    for raw_type in payload["raw_sample_types"]:
        assert f"`{raw_type}`" in doc
    for source in payload["sources"]:
        assert source["source"].replace("_", "-") in doc.lower() or source["source"] in doc
