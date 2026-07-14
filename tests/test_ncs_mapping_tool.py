import pytest

from kr_gov_job_mcp.clients.attachment_text_client import AttachmentTextResult
from kr_gov_job_mcp.schemas.job import JobAlioAttachment, JobAlioDetail
from kr_gov_job_mcp.tools.ncs_mapping import create_map_ncs_competencies_tool


def _detail(*attachments: JobAlioAttachment) -> JobAlioDetail:
    return JobAlioDetail(
        id="302368",
        institution_name="테스트 기관",
        title="정보보호 채용",
        source_url="https://example.test/job",
        ncs_codes=["R600020"],
        ncs_categories=["정보통신"],
        attachments=list(attachments),
    )


def test_map_ncs_competencies_prefers_supplied_text_and_preserves_evidence() -> None:
    calls: list[str] = []
    tool = create_map_ncs_competencies_tool(
        fetch_job_detail=lambda _job_id: _detail(
            JobAlioAttachment(
                name="직무기술서.pdf",
                file_type="C",
                url="https://example.test/duty.pdf",
            )
        ),
        extract_attachment=lambda url, _name: calls.append(url),  # type: ignore[arg-type]
    )

    result = tool.handler(
        {
            "source_job_id": "302368",
            "duty_description_text": "필요지식: 정보보호 법령\n필요기술: 로그 분석",
            "attachment_url": "https://example.test/duty.pdf",
        }
    )

    assert calls == []
    assert result["knowledge"][0]["name"] == "정보보호 법령"
    assert result["skills"][0]["evidence"][0]["url"] == "https://example.test/duty.pdf"
    assert result["attachment_candidates"][0]["extraction_status"] == "provided_text"


def test_map_ncs_competencies_extracts_single_pdf_candidate() -> None:
    tool = create_map_ncs_competencies_tool(
        fetch_job_detail=lambda _job_id: _detail(
            JobAlioAttachment(
                name="직무기술서.pdf",
                file_type="C",
                url="https://example.test/duty.pdf",
            )
        ),
        extract_attachment=lambda _url, _name: AttachmentTextResult(
            status="extracted",
            text="직업기초능력: 문제해결능력\n직무수행태도: 책임감",
        ),
    )

    result = tool.handler({"job_id": "302368"})

    assert result["basic_competencies"][0]["name"] == "문제해결능력"
    assert result["attitudes"][0]["name"] == "책임감"
    assert result["attachment_candidates"][0]["selected"] is True
    assert result["warnings"] == []


def test_map_ncs_competencies_does_not_link_supplied_text_without_attachment_url() -> None:
    tool = create_map_ncs_competencies_tool(
        fetch_job_detail=lambda _job_id: _detail(
            JobAlioAttachment(
                name="직무기술서.pdf",
                file_type="C",
                url="https://example.test/duty.pdf",
            )
        )
    )

    result = tool.handler(
        {"job_id": "302368", "duty_description_text": "필요지식: 정보보호 법령"}
    )

    assert result["knowledge"][0]["evidence"][0]["url"] is None
    assert result["attachment_candidates"][0]["selected"] is False
    assert any(note["field"] == "duty_description_text" for note in result["verification_notes"])


def test_map_ncs_competencies_does_not_choose_between_multiple_candidates() -> None:
    tool = create_map_ncs_competencies_tool(
        fetch_job_detail=lambda _job_id: _detail(
            JobAlioAttachment(name="직무기술서 A.pdf", file_type="C", url="https://x.test/a.pdf"),
            JobAlioAttachment(name="직무기술서 B.pdf", file_type="C", url="https://x.test/b.pdf"),
        ),
        extract_attachment=lambda _url, _name: pytest.fail("must not download"),
    )

    result = tool.handler({"recruitment_notice_sn": "302368"})

    assert all(not item["selected"] for item in result["attachment_candidates"])
    assert any("여러 개" in note["reason"] for note in result["verification_notes"])


def test_map_ncs_competencies_returns_unsupported_format_reason() -> None:
    tool = create_map_ncs_competencies_tool(
        fetch_job_detail=lambda _job_id: _detail(
            JobAlioAttachment(
                name="직무기술서.hwpx",
                file_type="C",
                url="https://example.test/duty.hwpx",
            )
        ),
        extract_attachment=lambda _url, _name: AttachmentTextResult(
            status="unsupported_format",
            reason="HWPX 형식은 자동 본문 추출을 지원하지 않습니다.",
        ),
    )

    result = tool.handler({"job_id": "302368"})

    assert result["attachment_candidates"][0]["extraction_status"] == "unsupported_format"
    assert result["warnings"]
    assert any(note["field"] == "attachment_text" for note in result["verification_notes"])


def test_map_ncs_competencies_does_not_download_unlisted_explicit_url() -> None:
    tool = create_map_ncs_competencies_tool(
        fetch_job_detail=lambda _job_id: _detail(),
        extract_attachment=lambda _url, _name: pytest.fail("must not download"),
    )

    result = tool.handler(
        {"job_id": "302368", "attachment_url": "https://unlisted.test/duty.pdf"}
    )

    assert result["attachment_candidates"][0]["selected"] is False
    assert any(note["field"] == "attachment_url" for note in result["verification_notes"])


def test_map_ncs_competencies_preserves_selection_for_candidate_without_url() -> None:
    tool = create_map_ncs_competencies_tool(
        fetch_job_detail=lambda _job_id: _detail(
            JobAlioAttachment(name="직무기술서.pdf", file_type="C")
        )
    )

    result = tool.handler({"job_id": "302368"})

    assert result["attachment_candidates"][0]["selected"] is True
    assert any(note["field"] == "attachment_url" for note in result["verification_notes"])


def test_map_ncs_competencies_rejects_conflicting_ids_and_unknown_arguments() -> None:
    tool = create_map_ncs_competencies_tool(fetch_job_detail=lambda _job_id: _detail())

    with pytest.raises(ValueError, match="conflicting map_ncs_competencies ids"):
        tool.handler({"job_id": "1", "source_job_id": "2"})
    with pytest.raises(ValueError, match="unsupported map_ncs_competencies arguments"):
        tool.handler({"job_id": "1", "unknown": True})
