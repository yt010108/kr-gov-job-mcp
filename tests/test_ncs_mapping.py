from kr_gov_job_mcp.analysis import prepare_ncs_mapping_input
from kr_gov_job_mcp.schemas.job import JobAlioAttachment, JobAlioDetail
from kr_gov_job_mcp.schemas.ncs import NcsMappingInput


def test_prepare_ncs_mapping_input_uses_job_alio_fields_and_duty_attachment() -> None:
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
                name="채용 공고문.pdf",
                file_type="A",
                url="https://example.test/a.pdf",
            ),
            JobAlioAttachment(
                name="NCS 직무기술서.zip",
                file_type="C",
                url="https://example.test/c.zip",
            ),
        ],
    )

    prepared = prepare_ncs_mapping_input(detail)

    assert NcsMappingInput.model_validate(prepared.model_dump())
    assert [item.code for item in prepared.ncs_codes] == ["R600002", "R600025"]
    assert prepared.ncs_codes[0].display_name == "경영.회계.사무"
    assert prepared.duty_description_attachments[0].name == "NCS 직무기술서.zip"
    assert {field.field_name for field in prepared.source_fields} == {
        "qualification",
        "preferred_conditions",
        "screening_procedure",
    }
    assert any(note.field == "ksa_candidates" for note in prepared.verification_notes)


def test_prepare_ncs_mapping_input_extracts_explicit_ksa_labels() -> None:
    detail = JobAlioDetail(
        id="302368",
        institution_name="국립중앙의료원",
        title="계약직 전산행정 채용 공고",
        ncs_codes=["R600006"],
        ncs_categories=["보건.의료"],
        attachments=[
            JobAlioAttachment(
                name="직무기술서.pdf",
                file_type="C",
                url="https://example.test/duty.pdf",
            )
        ],
    )
    duty_text = """
    필요지식: 정보보호 법령, 네트워크 기초
    필요기술: 로그 분석; 문서 작성
    직무수행태도: 정확성 / 책임감
    직업기초능력: 문제해결능력
    """

    prepared = prepare_ncs_mapping_input(detail, duty_description_text=duty_text)

    by_category = {(candidate.category, candidate.name) for candidate in prepared.ksa_candidates}
    assert ("knowledge", "정보보호 법령") in by_category
    assert ("knowledge", "네트워크 기초") in by_category
    assert ("skill", "로그 분석") in by_category
    assert ("attitude", "책임감") in by_category
    assert ("basic_competency", "문제해결능력") in by_category
    assert not any(note.field == "ksa_candidates" for note in prepared.verification_notes)


def test_ncs_code_name_mismatch_adds_verification_note() -> None:
    detail = JobAlioDetail(
        id="1",
        ncs_codes=["R600002", "R600025"],
        ncs_categories=["경영.회계.사무"],
    )

    prepared = prepare_ncs_mapping_input(detail)

    assert prepared.ncs_codes[1].display_name is None
    assert any(note.field == "ncs_codes" for note in prepared.verification_notes)


def test_prepare_ncs_mapping_input_separates_flattened_labels() -> None:
    detail = JobAlioDetail(id="1")

    prepared = prepare_ncs_mapping_input(
        detail,
        duty_description_text="필요지식: 보안 법령 필요기술: 로그 분석 직무수행태도: 책임감",
    )

    by_category = {(candidate.category, candidate.name) for candidate in prepared.ksa_candidates}
    assert by_category == {
        ("knowledge", "보안 법령"),
        ("skill", "로그 분석"),
        ("attitude", "책임감"),
    }


def test_prepare_ncs_mapping_input_reads_value_on_line_after_label() -> None:
    detail = JobAlioDetail(id="1")

    prepared = prepare_ncs_mapping_input(
        detail,
        duty_description_text="필요지식:\n정보보호 법령\n필요기술:\n로그 분석",
    )

    assert {(item.category, item.name) for item in prepared.ksa_candidates} == {
        ("knowledge", "정보보호 법령"),
        ("skill", "로그 분석"),
    }
