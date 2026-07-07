"""Generate a conservative, evidence-backed job fit preparation report."""

from __future__ import annotations

from collections.abc import Iterable

from kr_gov_job_mcp.schemas.job import JobAlioAttachment, JobAlioDetail
from kr_gov_job_mcp.schemas.job_fit import (
    ApplicantReadinessInput,
    InstitutionMaterialCheck,
    JobFitEvidenceSource,
    JobFitInstitutionSignal,
    JobFitPreparationItem,
    JobFitPreparationReport,
    JobFitVerificationNote,
)


def generate_job_fit_report(
    job_detail: JobAlioDetail,
    *,
    applicant: ApplicantReadinessInput | None = None,
    institution_signals: Iterable[JobFitInstitutionSignal] = (),
) -> JobFitPreparationReport:
    """Create a preparation report without inventing unsupported claims."""

    applicant = applicant or ApplicantReadinessInput()
    signals = list(institution_signals)
    verification_notes: list[JobFitVerificationNote] = []
    evidence_links = [_job_posting_evidence(job_detail)]
    preparation_items = _preparation_items(job_detail, signals, verification_notes)
    knowledge_gaps = _knowledge_gaps(job_detail, applicant)
    materials = _institution_materials(signals)
    for item in [*preparation_items, *knowledge_gaps]:
        evidence_links.extend(item.evidence)

    for signal in signals:
        evidence_links.extend(signal.evidence)
        if not signal.evidence:
            verification_notes.append(
                JobFitVerificationNote(
                    field="institution_signals.evidence",
                    reason=f"{signal.title} 기관 signal에 연결된 근거가 없습니다.",
                    suggested_check="기관 분석 입력의 evidence URL과 excerpt를 연결합니다.",
                )
            )

    return JobFitPreparationReport(
        job_id=job_detail.id,
        institution_name=job_detail.institution_name,
        job_title=job_detail.title,
        applicant_target_role=applicant.target_role,
        preparation_items=preparation_items,
        knowledge_gaps=knowledge_gaps,
        institution_materials_to_check=materials,
        evidence_links=_dedupe_evidence(evidence_links),
        verification_notes=verification_notes,
    )


def _preparation_items(
    job_detail: JobAlioDetail,
    institution_signals: list[JobFitInstitutionSignal],
    verification_notes: list[JobFitVerificationNote],
) -> list[JobFitPreparationItem]:
    items: list[JobFitPreparationItem] = []
    job_evidence = _job_posting_evidence(job_detail)
    duty_attachments = _duty_description_attachments(job_detail.attachments)

    if duty_attachments:
        items.append(
            JobFitPreparationItem(
                priority="P0",
                title="직무기술서에서 요구역량 확정",
                rationale="K/S/A와 직무수행능력은 직무기술서 원문 근거가 있어야 합니다.",
                recommended_actions=[
                    "직무기술서 첨부를 열어 필요지식, 필요기술, 직무수행태도를 표로 정리합니다.",
                    "NCS 코드와 직무기술서의 직무분류가 같은지 대조합니다.",
                ],
                evidence=[_attachment_evidence(attachment) for attachment in duty_attachments],
            )
        )
    else:
        verification_notes.append(
            JobFitVerificationNote(
                field="duty_description_attachments",
                reason="잡알리오 상세에서 직무기술서 첨부 후보를 찾지 못했습니다.",
                suggested_check="잡알리오 상세의 공고 첨부파일을 확인합니다.",
            )
        )

    if job_detail.ncs_codes or job_detail.ncs_categories:
        items.append(
            JobFitPreparationItem(
                priority="P0",
                title="NCS 분류와 공고 요구사항 연결",
                rationale="공고의 NCS 코드와 표시명은 준비 범위를 좁히는 1차 기준입니다.",
                recommended_actions=[
                    "NCS 표시명별 대표 직무능력을 확인합니다.",
                    "지원자격, 우대사항, 전형절차와 NCS 분류가 만나는 지점을 표시합니다.",
                ],
                evidence=[_ncs_evidence(job_detail)],
            )
        )
    else:
        verification_notes.append(
            JobFitVerificationNote(
                field="ncs_codes",
                reason="공고 상세에 NCS 코드나 표시명이 없습니다.",
                suggested_check="직무기술서 첨부파일에서 NCS 분류를 확인합니다.",
            )
        )

    source_field_evidence = _source_field_evidence(job_detail)
    if source_field_evidence:
        items.append(
            JobFitPreparationItem(
                priority="P1",
                title="지원자격과 우대사항 대응 사례 준비",
                rationale="공고 본문 필드는 지원 준비 판단의 직접 기준입니다.",
                recommended_actions=[
                    "지원자격과 우대사항을 충족 근거, 보완 필요, 확인 필요로 나눕니다.",
                    "전형절차별로 증빙 가능한 경험을 연결합니다.",
                ],
                evidence=source_field_evidence,
            )
        )
    else:
        verification_notes.append(
            JobFitVerificationNote(
                field="job_detail.source_fields",
                reason="지원자격, 우대사항, 전형절차 본문이 비어 있습니다.",
                suggested_check="잡알리오 상세 원문을 다시 확인합니다.",
            )
        )

    if institution_signals:
        signal_evidence = [evidence for signal in institution_signals for evidence in signal.evidence]
        items.append(
            JobFitPreparationItem(
                priority="P1",
                title="기관 사업 방향과 직무 연결",
                rationale="기관 signal은 직무 경험을 기관의 최근 방향과 연결하는 근거입니다.",
                recommended_actions=[
                    "기관 signal마다 공고 직무와 연결되는 키워드를 하나씩 고릅니다.",
                    "근거가 약한 signal은 준비 리포트 근거로 쓰기 전에 원문을 확인합니다.",
                ],
                evidence=signal_evidence,
                verification_notes=[
                    JobFitVerificationNote(
                        field="institution_signals",
                        reason="기관 signal은 분석 후보이므로 최종 문장 작성 전 원문 확인이 필요합니다.",
                        suggested_check="ALIO, Cleaneye, 기관 홈페이지 URL과 excerpt를 다시 봅니다.",
                    )
                ],
            )
        )
    else:
        verification_notes.append(
            JobFitVerificationNote(
                field="institution_signals",
                reason="기관 사업 방향 또는 개선 과제 signal이 없습니다.",
                suggested_check="기관 분석 입력에서 ALIO, Cleaneye, 기관 홈페이지 evidence를 먼저 연결합니다.",
            )
        )

    if job_detail.source_url:
        items.append(
            JobFitPreparationItem(
                priority="P2",
                title="기관 원문 공고 최종 대조",
                rationale="Job-ALIO 요약과 기관 원문 공고가 다를 수 있습니다.",
                recommended_actions=["접수 링크, 첨부파일, 마감일, 전형절차를 기관 원문에서 재확인합니다."],
                evidence=[job_evidence],
            )
        )
    return items


def _knowledge_gaps(
    job_detail: JobAlioDetail,
    applicant: ApplicantReadinessInput,
) -> list[JobFitPreparationItem]:
    known_text = " ".join(applicant.known_skills).lower()
    gaps: list[JobFitPreparationItem] = []
    for category in job_detail.ncs_categories:
        if category.lower() in known_text:
            continue
        gaps.append(
            JobFitPreparationItem(
                priority="P1",
                title=f"{category} 관련 직무 지식 점검",
                rationale="지원자가 보유 역량으로 명시하지 않은 NCS 표시명입니다.",
                recommended_actions=[
                    f"{category}에서 공고 직무와 가장 가까운 하위 역량을 확인합니다.",
                    "직무기술서의 필요지식/필요기술과 겹치는 부분을 우선 학습합니다.",
                ],
                evidence=[_ncs_evidence(job_detail)],
                verification_notes=[
                    JobFitVerificationNote(
                        field="applicant.known_skills",
                        reason="보유 역량 텍스트와 NCS 표시명을 단순 비교한 후보입니다.",
                        suggested_check="지원자 실제 경험과 직무기술서 세부 K/S/A를 대조합니다.",
                    )
                ],
            )
        )
    return gaps


def _institution_materials(
    institution_signals: list[JobFitInstitutionSignal],
) -> list[InstitutionMaterialCheck]:
    materials = [
        InstitutionMaterialCheck(
            title="기관 최신 주요사업",
            reason="기관 이해와 직무 연결 판단의 기준 자료입니다.",
            source_hint="ALIO 주요사업, 기관 홈페이지 사업 소개",
        ),
        InstitutionMaterialCheck(
            title="기관 개선 과제",
            reason="기관 개선 과제를 다룰 때 조심스러운 표현 기준이 필요합니다.",
            source_hint="ALIO 국회 지적사항, 경영평가, Cleaneye 감사/평가 항목",
        ),
    ]
    if institution_signals:
        materials.append(
            InstitutionMaterialCheck(
                title="기관 signal 원문",
                reason="보고서 후보 signal의 과장 여부를 확인해야 합니다.",
                source_hint="signal별 evidence URL과 excerpt",
            )
        )
    return materials


def _duty_description_attachments(attachments: list[JobAlioAttachment]) -> list[JobAlioAttachment]:
    return [
        attachment
        for attachment in attachments
        if attachment.file_type == "C" or "직무기술서" in (attachment.name or "").lower()
    ]


def _job_posting_evidence(job_detail: JobAlioDetail) -> JobFitEvidenceSource:
    return JobFitEvidenceSource(
        title="잡알리오 공고 상세",
        source_type="job_posting",
        url=job_detail.source_url,
        excerpt=job_detail.title,
    )


def _attachment_evidence(attachment: JobAlioAttachment) -> JobFitEvidenceSource:
    return JobFitEvidenceSource(
        title=attachment.name or "직무기술서 첨부 후보",
        source_type="duty_description",
        url=attachment.url,
        excerpt=f"file_type={attachment.file_type or 'unknown'}",
    )


def _ncs_evidence(job_detail: JobAlioDetail) -> JobFitEvidenceSource:
    codes = ", ".join(job_detail.ncs_codes)
    categories = ", ".join(job_detail.ncs_categories)
    return JobFitEvidenceSource(
        title="잡알리오 NCS 분류",
        source_type="ncs",
        url=job_detail.source_url,
        excerpt=" / ".join(part for part in (codes, categories) if part),
    )


def _source_field_evidence(job_detail: JobAlioDetail) -> list[JobFitEvidenceSource]:
    fields = [
        ("지원자격", job_detail.qualification),
        ("우대조건", job_detail.preferred_conditions),
        ("가점/우대사항", job_detail.preference),
        ("전형절차", job_detail.screening_procedure),
    ]
    return [
        JobFitEvidenceSource(
            title=title,
            source_type="job_posting",
            url=job_detail.source_url,
            excerpt=value[:500],
        )
        for title, value in fields
        if value
    ]


def _dedupe_evidence(evidence: list[JobFitEvidenceSource]) -> list[JobFitEvidenceSource]:
    deduped: dict[tuple[str, str | None, str | None], JobFitEvidenceSource] = {}
    for item in evidence:
        key = (item.title, item.url, item.excerpt)
        if key not in deduped:
            deduped[key] = item
    return list(deduped.values())
