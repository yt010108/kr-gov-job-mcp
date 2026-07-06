import json
from pathlib import Path

from kr_gov_job_mcp.schemas import (
    ApplicantProfile,
    InstitutionStrategy,
    InstitutionWeakness,
    JobDetail,
    JobFitReport,
    NcsKsaMapping,
)


ROOT = Path(__file__).resolve().parents[1]


def test_kisa_demo_input_uses_known_output_schema() -> None:
    payload = json.loads((ROOT / "examples" / "kisa-demo-input.json").read_text())

    assert ApplicantProfile.model_validate(payload["applicant_profile"])
    assert payload["expected_output_schema"] == "JobFitReport"


def test_kisa_demo_output_matches_job_fit_report_schema() -> None:
    payload = json.loads((ROOT / "examples" / "kisa-demo-output.json").read_text())

    report = JobFitReport.model_validate(payload)

    assert report.institution_name == "한국인터넷진흥원"
    assert report.job_detail.verification_notes
    assert report.preparation_priorities[0].priority == "P0"


def test_shared_schema_json_can_be_generated() -> None:
    for model in (
        JobDetail,
        NcsKsaMapping,
        InstitutionStrategy,
        InstitutionWeakness,
        JobFitReport,
    ):
        schema = model.model_json_schema()

        assert schema["title"] == model.__name__
