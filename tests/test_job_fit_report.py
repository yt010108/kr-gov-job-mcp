from kr_gov_job_mcp.analysis import generate_job_fit_report
from kr_gov_job_mcp.schemas.job import JobAlioAttachment, JobAlioDetail
from kr_gov_job_mcp.schemas.job_fit import (
    ApplicantReadinessInput,
    JobFitEvidenceSource,
    JobFitInstitutionSignal,
    JobFitPreparationReport,
)


def test_generate_job_fit_report_links_job_ncs_duty_and_institution_evidence() -> None:
    detail = JobAlioDetail(
        id="302181",
        institution_name="한국재정정보원",
        title="2026년도 제4차 채용",
        source_url="https://example.test/job",
        ncs_codes=["R600002", "R600025"],
        ncs_categories=["경영.회계.사무", "연구"],
        qualification="관련 분야 지식 필요",
        preferred_conditions="정보보호 자격 우대",
        screening_procedure="서류전형, 면접전형",
        attachments=[
            JobAlioAttachment(
                name="NCS 직무기술서.zip",
                file_type="C",
                url="https://example.test/duty.zip",
            )
        ],
    )
    signal = JobFitInstitutionSignal(
        title="디지털 재정 플랫폼 고도화",
        summary="ALIO 주요사업 기반 signal",
        evidence=[
            JobFitEvidenceSource(
                title="ALIO 주요사업",
                source_type="institution_signal",
                url="https://example.test/alio",
                excerpt="디지털 재정 플랫폼 고도화",
            )
        ],
    )

    report = generate_job_fit_report(
        detail,
        applicant=ApplicantReadinessInput(
            target_role="전산",
            known_skills=["정보보호"],
        ),
        institution_signals=[signal],
    )

    assert JobFitPreparationReport.model_validate(report.model_dump())
    assert report.job_id == "302181"
    assert {item.priority for item in report.preparation_items} >= {"P0", "P1"}
    assert any("직무기술서" in item.title for item in report.preparation_items)
    assert any(item.source_type == "duty_description" for item in report.evidence_links)
    assert any(item.source_type == "ncs" for item in report.evidence_links)
    assert any(item.source_type == "institution_signal" for item in report.evidence_links)
    assert report.institution_materials_to_check


def test_generate_job_fit_report_adds_verification_notes_for_missing_inputs() -> None:
    detail = JobAlioDetail(id="1", title="공고")

    report = generate_job_fit_report(detail)

    fields = {note.field for note in report.verification_notes}
    assert "duty_description_attachments" in fields
    assert "ncs_codes" in fields
    assert "job_detail.source_fields" in fields
    assert "institution_signals" in fields


def test_generate_job_fit_report_marks_signal_without_evidence() -> None:
    detail = JobAlioDetail(
        id="1",
        ncs_codes=["R600002"],
        ncs_categories=["경영.회계.사무"],
        qualification="지원자격",
        attachments=[JobAlioAttachment(name="직무기술서.pdf", file_type="C")],
    )
    signal = JobFitInstitutionSignal(title="근거 없는 signal")

    report = generate_job_fit_report(detail, institution_signals=[signal])

    assert any(note.field == "institution_signals.evidence" for note in report.verification_notes)
    item = next(item for item in report.preparation_items if "기관 사업 방향" in item.title)
    assert item.verification_notes
