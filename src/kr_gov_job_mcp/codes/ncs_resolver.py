"""Resolve natural-language job inputs to Job-ALIO NCS candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kr_gov_job_mcp.codes.job_alio_codes import (
    JobAlioCodeCandidate,
    find_job_alio_codes,
    list_job_alio_codes,
)


@dataclass(frozen=True)
class NcsResolutionCandidate:
    """One ranked NCS candidate with the terms that matched the input."""

    candidate: JobAlioCodeCandidate
    score: float
    matched_aliases: tuple[str, ...]

    @property
    def code(self) -> str:
        return self.candidate.code

    @property
    def name(self) -> str:
        return self.candidate.name

    def public_dict(self) -> dict[str, Any]:
        return {
            **self.candidate.public_dict(score=self.score),
            "matched_aliases": list(self.matched_aliases),
        }


@dataclass(frozen=True)
class NcsResolution:
    """The result of resolving one natural-language NCS query."""

    query: str
    candidates: tuple[NcsResolutionCandidate, ...]
    selected: NcsResolutionCandidate | None
    warnings: tuple[str, ...]

    @property
    def confidence(self) -> float:
        return self.selected.score if self.selected is not None else 0.0


def resolve_ncs_code(*, query: str, limit: int = 5) -> NcsResolution:
    """Return ranked Job-ALIO NCS candidates and select only unambiguous matches."""
    text = _to_text(query)
    if text is None:
        raise ValueError("NCS query is required")
    if limit < 1:
        raise ValueError("NCS result limit must be at least 1")

    all_matches = find_job_alio_codes(
        code_type="ncs",
        query=text,
        limit=len(list_job_alio_codes("ncs")),
    )
    ranked = tuple(
        NcsResolutionCandidate(
            candidate=candidate,
            score=score,
            matched_aliases=_matched_aliases(candidate, text),
        )
        for candidate, score in all_matches
    )
    selected = _select_candidate(ranked)
    warnings = _warnings_for(ranked, selected)
    return NcsResolution(
        query=text,
        candidates=ranked[:limit],
        selected=selected,
        warnings=warnings,
    )


def _select_candidate(
    candidates: tuple[NcsResolutionCandidate, ...],
) -> NcsResolutionCandidate | None:
    if not candidates:
        return None

    top = candidates[0]
    if sum(candidate.score == top.score for candidate in candidates) != 1:
        return None
    if top.score >= 0.92:
        return top
    if top.score >= 0.68 and len(candidates) == 1:
        return top
    return None


def _warnings_for(
    candidates: tuple[NcsResolutionCandidate, ...],
    selected: NcsResolutionCandidate | None,
) -> tuple[str, ...]:
    if not candidates:
        return (
            "일치하는 Job-ALIO NCS 후보가 없습니다. search_public_jobs.ncs_code는 비워 둡니다.",
        )
    if selected is None:
        return (
            "여러 NCS 후보가 비슷하게 일치해 하나의 코드로 확정하지 않았습니다. candidates를 확인한 뒤 ncs_code를 선택하세요.",
        )
    return ()


def _matched_aliases(candidate: JobAlioCodeCandidate, query: str) -> tuple[str, ...]:
    normalized_query = _normalize(query)
    terms = (candidate.code, candidate.name, *candidate.aliases)
    exact = tuple(term for term in terms if _normalize(term) == normalized_query)
    if exact:
        return exact

    partial = tuple(
        term
        for term in terms
        if (normalized_term := _normalize(term))
        and (normalized_term in normalized_query or normalized_query in normalized_term)
    )
    return tuple(sorted(set(partial), key=lambda item: (-len(item), item)))


def _to_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize(value: str) -> str:
    ignored = {" ", "\t", "\n", "\r", "·", "ㆍ", ".", "-", "_", "/"}
    return "".join(char for char in value.strip().lower() if char not in ignored)
