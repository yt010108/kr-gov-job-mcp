"""Small Job-ALIO code lookup tables for high-impact search filters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


JobAlioCodeType = Literal["institution", "ncs"]


@dataclass(frozen=True)
class JobAlioCodeCandidate:
    code: str
    name: str
    aliases: tuple[str, ...] = ()
    source: str = "job_alio_seed_table"

    def public_dict(self, *, score: float) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "aliases": list(self.aliases),
            "score": score,
            "source": self.source,
        }


INSTITUTION_CODES: tuple[JobAlioCodeCandidate, ...] = (
    JobAlioCodeCandidate(
        "C0399",
        "한국인터넷진흥원",
        ("KISA", "인터넷진흥원"),
    ),
    JobAlioCodeCandidate(
        "B552909",
        "창업진흥원",
        ("KISED",),
    ),
)

NCS_CODES: tuple[JobAlioCodeCandidate, ...] = (
    JobAlioCodeCandidate(
        "R600020",
        "정보통신",
        ("전산", "전산직", "IT", "정보보호", "보안", "네트워크", "개발", "데이터"),
    ),
    JobAlioCodeCandidate(
        "R600021",
        "사업관리",
        ("사업 기획", "사업운영", "프로젝트 관리", "PM"),
    ),
    JobAlioCodeCandidate(
        "R600002",
        "경영.회계.사무",
        ("사무", "행정", "경영", "회계"),
    ),
    JobAlioCodeCandidate(
        "R600006",
        "보건.의료",
        ("보건", "의료", "병원"),
    ),
    JobAlioCodeCandidate(
        "R600025",
        "연구",
        ("연구직", "R&D", "연구개발"),
    ),
)


def list_job_alio_codes(code_type: JobAlioCodeType) -> list[JobAlioCodeCandidate]:
    if code_type == "institution":
        return list(INSTITUTION_CODES)
    if code_type == "ncs":
        return list(NCS_CODES)
    raise ValueError(f"unsupported Job-ALIO code_type: {code_type}")


def find_job_alio_codes(
    *,
    code_type: JobAlioCodeType,
    query: str,
    limit: int = 20,
) -> list[tuple[JobAlioCodeCandidate, float]]:
    normalized_query = _normalize(query)
    if not normalized_query:
        return []

    scored: list[tuple[JobAlioCodeCandidate, float]] = []
    for candidate in list_job_alio_codes(code_type):
        score = _match_score(candidate, normalized_query)
        if score > 0:
            scored.append((candidate, score))
    return sorted(scored, key=lambda item: (-item[1], item[0].name, item[0].code))[:limit]


def _match_score(candidate: JobAlioCodeCandidate, normalized_query: str) -> float:
    normalized_code = _normalize(candidate.code)
    normalized_name = _normalize(candidate.name)
    normalized_aliases = [_normalize(alias) for alias in candidate.aliases]

    if normalized_query == normalized_code:
        return 1.0
    if normalized_query == normalized_name:
        return 0.98
    if normalized_query in normalized_aliases:
        return 0.92
    if normalized_query in normalized_name or any(normalized_query in alias for alias in normalized_aliases):
        return 0.75
    if normalized_name in normalized_query or any(alias and alias in normalized_query for alias in normalized_aliases):
        return 0.68
    return 0.0


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    return "".join(str(value).strip().lower().split())
