"""Normalize user-facing job role names into MVP-safe job families."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


SECURITY_NORMALIZED_JOB_FAMILY = "정보통신"
SECURITY_JOB_ALIASES: Mapping[str, str] = {
    "정보보안": SECURITY_NORMALIZED_JOB_FAMILY,
    "정보보호": SECURITY_NORMALIZED_JOB_FAMILY,
    "침해대응": SECURITY_NORMALIZED_JOB_FAMILY,
    "침해사고 대응": SECURITY_NORMALIZED_JOB_FAMILY,
    "취약점 분석": SECURITY_NORMALIZED_JOB_FAMILY,
    "개인정보보호": SECURITY_NORMALIZED_JOB_FAMILY,
    "정보통신 보안": SECURITY_NORMALIZED_JOB_FAMILY,
    "웹 보안": SECURITY_NORMALIZED_JOB_FAMILY,
    "네트워크 보안": SECURITY_NORMALIZED_JOB_FAMILY,
    "보안": SECURITY_NORMALIZED_JOB_FAMILY,
}
SAFE_JOB_PREPARATION_CONTEXT: dict[str, Any] = {
    "purpose": "public_sector_job_interview_preparation",
    "allowed_outputs": [
        "motivation",
        "institution_understanding",
        "job_competency",
        "behavioral_questions",
        "situational_questions",
        "preparation_checklist",
    ],
    "disallowed_outputs": [
        "exploit_steps",
        "payload_generation",
        "unauthorized_access_guidance",
        "malware_or_evasion_procedure",
    ],
}


def normalize_job_role(
    *,
    target_role: str | None = None,
    job_family: str | None = None,
    query: str | None = None,
    known_skills: Iterable[str] | None = None,
    preparation_notes: str | None = None,
) -> dict[str, Any]:
    """Normalize security job aliases to the Job-ALIO/NCS information-communication family."""

    original_known_skills = [skill for skill in (known_skills or []) if skill]
    field_values = {
        "target_role": [target_role],
        "job_family": [job_family],
        "query": [query],
        "known_skills": original_known_skills,
        "preparation_notes": [preparation_notes],
    }
    matched_aliases, matched_fields = _find_security_aliases(field_values)
    is_security_role = bool(matched_aliases)

    normalized_job_family = _normalized_job_family(
        is_security_role=is_security_role,
        target_role=target_role,
        job_family=job_family,
    )
    normalized_target_role = _normalized_target_role(
        is_security_role=is_security_role,
        target_role=target_role,
        job_family=job_family,
    )

    return {
        "original_target_role": target_role,
        "original_job_family": job_family,
        "original_query": query,
        "original_known_skills": original_known_skills,
        "original_preparation_notes": preparation_notes,
        "normalized_target_role": normalized_target_role,
        "normalized_job_family": normalized_job_family,
        "is_security_role": is_security_role,
        "matched_aliases": matched_aliases,
        "matched_fields": matched_fields,
        "normalization_reason": _normalization_reason(
            is_security_role=is_security_role,
            matched_aliases=matched_aliases,
            normalized_job_family=normalized_job_family,
        ),
        "recommended_next_arguments": _recommended_next_arguments(
            target_role=target_role,
            job_family=job_family,
            normalized_target_role=normalized_target_role,
            normalized_job_family=normalized_job_family,
            is_security_role=is_security_role,
            matched_aliases=matched_aliases,
        ),
        "safe_context": SAFE_JOB_PREPARATION_CONTEXT,
        "warnings": [],
    }


def _find_security_aliases(
    field_values: Mapping[str, Iterable[str | None]],
) -> tuple[list[str], dict[str, list[str]]]:
    matched_aliases: list[str] = []
    matched_fields: dict[str, list[str]] = {}
    seen_aliases: set[str] = set()

    for field, values in field_values.items():
        for value in values:
            if not value:
                continue
            compact_value = _compact(value)
            matched_for_value: list[str] = []
            for alias in sorted(
                SECURITY_JOB_ALIASES,
                key=lambda candidate: len(_compact(candidate)),
                reverse=True,
            ):
                compact_alias = _compact(alias)
                if compact_alias not in compact_value:
                    continue
                if any(compact_alias in _compact(existing) for existing in matched_for_value):
                    continue
                matched_for_value.append(alias)
                matched_fields.setdefault(field, [])
                if alias not in matched_fields[field]:
                    matched_fields[field].append(alias)
                if alias in seen_aliases:
                    continue
                seen_aliases.add(alias)
                matched_aliases.append(alias)
    return matched_aliases, matched_fields


def _normalized_job_family(
    *,
    is_security_role: bool,
    target_role: str | None,
    job_family: str | None,
) -> str | None:
    if is_security_role:
        return SECURITY_NORMALIZED_JOB_FAMILY
    return job_family or target_role


def _normalized_target_role(
    *,
    is_security_role: bool,
    target_role: str | None,
    job_family: str | None,
) -> str | None:
    if is_security_role:
        return SECURITY_NORMALIZED_JOB_FAMILY
    return target_role or job_family


def _normalization_reason(
    *,
    is_security_role: bool,
    matched_aliases: list[str],
    normalized_job_family: str | None,
) -> str:
    if is_security_role:
        aliases = ", ".join(matched_aliases)
        return f"보안 직무 표현({aliases})을 채용/NCS 맥락의 {normalized_job_family} 직무군으로 정규화했습니다."
    return "보안 직무 별칭이 감지되지 않아 입력 직무명을 그대로 유지했습니다."


def _recommended_next_arguments(
    *,
    target_role: str | None,
    job_family: str | None,
    normalized_target_role: str | None,
    normalized_job_family: str | None,
    is_security_role: bool,
    matched_aliases: list[str],
) -> dict[str, Any]:
    original_target_role = target_role or job_family or (matched_aliases[0] if matched_aliases else None)
    arguments = {}
    if normalized_target_role is not None:
        arguments["target_role"] = normalized_target_role
    if normalized_job_family is not None:
        arguments["job_family"] = normalized_job_family
    if is_security_role and original_target_role:
        arguments["original_target_role"] = original_target_role
    return arguments


def _compact(value: str) -> str:
    return "".join(str(value).lower().split())
