from kr_gov_job_mcp.analysis import (
    generate_institution_interview_report,
    prepare_institution_analysis_input,
)
from kr_gov_job_mcp.schemas.institution import InstitutionEvidence, InstitutionSignalCandidate


def test_generate_institution_interview_report_builds_cards_from_three_materials() -> None:
    major_business = InstitutionEvidence(
        title="ALIO 주요사업",
        source_type="alio_disclosure",
        url="https://example.test/alio/40",
        excerpt="가장 큰 규모는 보건의료정보 표준화 사업입니다.",
        fields={"source_type": "major_business", "alio_item_no": "40"},
    )
    research = InstitutionEvidence(
        title="보건의료데이터 정책 연구",
        source_type="alio_disclosure",
        url="https://example.test/alio/50",
        excerpt="연구보고서를 직무 관심도 근거로 활용할 수 있습니다.",
        fields={"source_type": "policy_research", "alio_item_no": "50-1"},
    )
    audit_point = InstitutionEvidence(
        title="국회 지적사항",
        source_type="alio_disclosure",
        url="https://example.test/alio/47",
        excerpt="공적 항공 마일리지 사용 현황을 점검하고 관리할 것",
        fields={"source_type": "audit_point", "alio_item_no": "47-1"},
    )
    analysis_input = prepare_institution_analysis_input(
        institution_name="(재)한국보건의료정보원",
        alio_id="C1304",
        evidence=[major_business, research, audit_point],
        signals=[
            InstitutionSignalCandidate(
                category="business_direction",
                title="주요사업",
                summary=major_business.excerpt,
                evidence=[major_business],
            ),
            InstitutionSignalCandidate(
                category="job_connection",
                title="연구보고서",
                summary=research.excerpt,
                evidence=[research],
            ),
            InstitutionSignalCandidate(
                category="improvement_task",
                title="국회 지적사항",
                summary=audit_point.excerpt,
                evidence=[audit_point],
            ),
        ],
    )

    report = generate_institution_interview_report(
        analysis_input,
        year=2026,
        target_role="보건의료정보",
        focus_areas=["지원동기", "기관이해", "개선과제", "입사후포부"],
    )

    assert [card.question_type for card in report.interview_cards] == [
        "지원동기",
        "기관 현안 이해",
        "개선과제",
        "입사후포부",
    ]
    assert report.materials_to_check == ["주요사업", "연구/정책 자료", "국회 지적사항"]
    assert "채용공고" in report.excluded_for_now
    improvement_card = next(card for card in report.interview_cards if card.question_type == "개선과제")
    assert improvement_card.evidence == [audit_point]
    assert improvement_card.safe_framing is not None
    assert "비판" in improvement_card.answer_strategy
    assert "보건의료정보" in improvement_card.sample_answer_sentence


def test_generate_institution_interview_report_keeps_missing_evidence_as_notes() -> None:
    analysis_input = prepare_institution_analysis_input(institution_name="한국인터넷진흥원")

    report = generate_institution_interview_report(
        analysis_input,
        year=2026,
        target_role="정보보호",
    )

    assert [card.question_type for card in report.interview_cards] == [
        "지원동기",
        "기관 현안 이해",
        "직무 관심도",
        "입사후포부",
        "상황면접",
    ]
    assert all(card.evidence == [] for card in report.interview_cards)
    assert all(card.sample_answer_sentence is None for card in report.interview_cards)
    note_fields = {note.field for note in report.verification_notes}
    assert "evidence" in note_fields
    assert "strategy_signals" in note_fields
    assert "weakness_signals" in note_fields
    assert "interview_cards.지원동기.evidence" in note_fields
    assert "interview_cards.직무 관심도.evidence" in note_fields
    assert "interview_cards.상황면접.evidence" not in note_fields
    situation_card = report.interview_cards[-1]
    assert situation_card.question_type == "상황면접"
    assert "예상하지 못한 문제" in situation_card.likely_question
    assert "상황 파악" in situation_card.answer_strategy
    assert situation_card.sample_answer_sentence is None
    assert situation_card.evidence == []


def test_situational_interview_card_does_not_reuse_institution_evidence() -> None:
    evidence = InstitutionEvidence(
        title="기관 연구자료",
        source_type="alio_disclosure",
        excerpt="기관 연구자료의 공개 요약",
        fields={"source_type": "policy_research"},
    )
    analysis_input = prepare_institution_analysis_input(
        institution_name="한국인터넷진흥원",
        evidence=[evidence],
        signals=[
            InstitutionSignalCandidate(
                category="job_connection",
                title="연구자료",
                summary=evidence.excerpt,
                evidence=[evidence],
            )
        ],
    )

    report = generate_institution_interview_report(
        analysis_input,
        target_role="정보통신",
        focus_areas=["상황면접"],
    )

    card = report.interview_cards[0]
    assert card.question_type == "상황면접"
    assert "어떤 업무에 관심" not in card.likely_question
    assert card.evidence == []
    assert card.sample_answer_sentence is None
    assert "꾸며내지" in card.caution
