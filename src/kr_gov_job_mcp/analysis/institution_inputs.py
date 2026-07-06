"""Prepare institution analysis inputs from collected source candidates."""

from __future__ import annotations

import re
from collections.abc import Iterable

from kr_gov_job_mcp.schemas.institution import (
    CleaneyeInstitutionKind,
    InstitutionAnalysisInput,
    InstitutionEvidence,
    InstitutionIdentityCandidate,
    InstitutionSignalCandidate,
    InstitutionVerificationNote,
)


def normalize_institution_name(name: str) -> str:
    """Normalize only whitespace and common bracket spacing; do not drop legal suffixes."""

    text = re.sub(r"\s+", " ", name).strip()
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return text


def prepare_institution_analysis_input(
    *,
    institution_name: str,
    aliases: Iterable[str] = (),
    alio_id: str | None = None,
    cleaneye_id: str | None = None,
    cleaneye_kind: CleaneyeInstitutionKind | None = None,
    identity_candidates: Iterable[InstitutionIdentityCandidate] = (),
    evidence: Iterable[InstitutionEvidence] = (),
    signals: Iterable[InstitutionSignalCandidate] = (),
) -> InstitutionAnalysisInput:
    normalized_name = normalize_institution_name(institution_name)
    alias_list = _unique_preserve_order(
        normalize_institution_name(alias)
        for alias in aliases
        if normalize_institution_name(alias) != normalized_name
    )
    identity_list = list(identity_candidates)
    evidence_list = list(evidence)
    signal_list = list(signals)
    verification_notes = _verification_notes(
        alio_id=alio_id,
        cleaneye_id=cleaneye_id,
        cleaneye_kind=cleaneye_kind,
        identity_candidates=identity_list,
        evidence=evidence_list,
        signals=signal_list,
    )

    return InstitutionAnalysisInput(
        institution_name=institution_name,
        normalized_name=normalized_name,
        aliases=alias_list,
        alio_id=alio_id,
        cleaneye_id=cleaneye_id,
        cleaneye_kind=cleaneye_kind,
        identity_candidates=identity_list,
        evidence=evidence_list,
        signals=signal_list,
        verification_notes=verification_notes,
    )


def _verification_notes(
    *,
    alio_id: str | None,
    cleaneye_id: str | None,
    cleaneye_kind: CleaneyeInstitutionKind | None,
    identity_candidates: list[InstitutionIdentityCandidate],
    evidence: list[InstitutionEvidence],
    signals: list[InstitutionSignalCandidate],
) -> list[InstitutionVerificationNote]:
    notes: list[InstitutionVerificationNote] = []
    if not alio_id and not cleaneye_id and not identity_candidates:
        notes.append(
            InstitutionVerificationNote(
                field="identity_candidates",
                reason="기관명 외에 ALIO 또는 Cleaneye 기관 코드를 아직 확인하지 않았습니다.",
                suggested_check="ALIO apbaId, Cleaneye entId/insttCode, 기관 홈페이지 URL을 대조합니다.",
            )
        )
    if cleaneye_id and cleaneye_kind is None:
        notes.append(
            InstitutionVerificationNote(
                field="cleaneye_kind",
                reason="Cleaneye ID가 있지만 지방공기업/출자출연 구분이 없습니다.",
                suggested_check="Cleaneye 검색 endpoint에서 entId인지 insttCode인지 확인합니다.",
            )
        )
    if not evidence:
        notes.append(
            InstitutionVerificationNote(
                field="evidence",
                reason="기관 분석에 연결할 원문 근거가 없습니다.",
                suggested_check="ALIO, Cleaneye, 기관 홈페이지, 보도자료 raw sample을 먼저 수집합니다.",
            )
        )
    for index, signal in enumerate(signals):
        if not signal.evidence:
            notes.append(
                InstitutionVerificationNote(
                    field=f"signals[{index}].evidence",
                    reason=f"{signal.title} 후보에 연결된 원문 근거가 없습니다.",
                    suggested_check="후보를 만든 출처 URL, 원문 excerpt, 수집 sample path를 연결합니다.",
                )
            )
    return notes


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique
