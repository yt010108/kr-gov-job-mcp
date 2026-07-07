"""Small Job-ALIO institution code lookup table for MVP institution-name search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class InstitutionLookupError(ValueError):
    """Raised when an institution query cannot be resolved safely."""


@dataclass(frozen=True)
class JobAlioInstitutionCode:
    code: str
    name: str
    aliases: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "aliases": list(self.aliases),
        }


INSTITUTION_CODES: tuple[JobAlioInstitutionCode, ...] = (
    JobAlioInstitutionCode("C0045", "한국농수산식품유통공사", ("aT", "농수산식품유통공사")),
    JobAlioInstitutionCode("C0113", "전남대학교병원", ("전남대병원", "전남대학교 병원", "화순전남대학교병원")),
    JobAlioInstitutionCode("C0399", "한국인터넷진흥원", ("KISA", "인터넷진흥원")),
    JobAlioInstitutionCode("C0451", "창업진흥원", ()),
)


def list_institution_codes() -> list[JobAlioInstitutionCode]:
    return list(INSTITUTION_CODES)


def find_institution_codes(query: str | None = None) -> list[JobAlioInstitutionCode]:
    normalized_query = _normalize(query)
    if not normalized_query:
        return list_institution_codes()

    exact_matches = [
        institution
        for institution in INSTITUTION_CODES
        if normalized_query == _normalize(institution.code)
        or normalized_query == _normalize(institution.name)
        or normalized_query in {_normalize(alias) for alias in institution.aliases}
    ]
    if exact_matches:
        return exact_matches

    return [
        institution
        for institution in INSTITUTION_CODES
        if normalized_query in _normalize(institution.name)
        or any(normalized_query in _normalize(alias) for alias in institution.aliases)
    ]


def resolve_institution_code(query: str) -> JobAlioInstitutionCode:
    matches = find_institution_codes(query)
    if not matches:
        supported = ", ".join(institution.name for institution in INSTITUTION_CODES)
        raise InstitutionLookupError(f"unknown Job-ALIO institution: {query}. supported: {supported}")
    if len(matches) > 1:
        candidates = ", ".join(f"{institution.name}({institution.code})" for institution in matches)
        raise InstitutionLookupError(
            f"ambiguous Job-ALIO institution: {query}. candidates: {candidates}"
        )
    return matches[0]


def institution_match_confidence(institution: JobAlioInstitutionCode, query: str | None) -> str:
    normalized_query = _normalize(query)
    if not normalized_query:
        return "medium"
    exact_values = {
        _normalize(institution.code),
        _normalize(institution.name),
        *(_normalize(alias) for alias in institution.aliases),
    }
    return "high" if normalized_query in exact_values else "medium"


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    for token in (" ", "\t", "\n", "(", ")", "[", "]", "재단법인", "주식회사", "(주)"):
        text = text.replace(token, "")
    return text
