"""Small Job-ALIO code lookup tables for high-impact search filters."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from io import StringIO
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


JOB_ALIO_INSTITUTION_CODES_CSV = "resources/job_alio_institution_codes.csv"
ALIO_INSTITUTION_ALIASES_CSV = "resources/alio_institution_codes.csv"
INSTITUTION_CODE_SOURCE = "job_alio_recruit_filter_csv_2026_07_13"
EXPECTED_INSTITUTION_CODE_COUNT = 405
INSTITUTION_CODE_PATTERN = re.compile(r"C\d{4}")
MANUAL_INSTITUTION_ALIASES: dict[str, tuple[str, ...]] = {
    "C0399": ("인터넷진흥원",),
    "C0451": ("KISED",),
}

NCS_CODES: tuple[JobAlioCodeCandidate, ...] = (
    JobAlioCodeCandidate(
        "R600001",
        "사업관리",
        ("사업 기획", "사업운영", "프로젝트 관리", "PM"),
    ),
    JobAlioCodeCandidate(
        "R600002",
        "경영·회계·사무",
        ("경영.회계.사무", "경영회계사무", "사무", "행정", "경영", "회계"),
    ),
    JobAlioCodeCandidate("R600003", "금융·보험", ("금융", "보험")),
    JobAlioCodeCandidate(
        "R600004",
        "교육·자연·사회과학",
        ("교육", "자연과학", "사회과학", "교육자연사회과학"),
    ),
    JobAlioCodeCandidate(
        "R600005",
        "법률·경찰·소방·교도·국방",
        ("법률", "경찰", "소방", "교도", "국방"),
    ),
    JobAlioCodeCandidate(
        "R600006",
        "보건·의료",
        ("보건.의료", "보건의료", "보건", "의료", "병원"),
    ),
    JobAlioCodeCandidate("R600007", "사회복지·종교", ("사회복지", "복지", "종교")),
    JobAlioCodeCandidate(
        "R600008",
        "문화·예술·디자인·방송",
        ("문화", "예술", "디자인", "방송", "콘텐츠"),
    ),
    JobAlioCodeCandidate("R600009", "운전·운송", ("운전", "운송")),
    JobAlioCodeCandidate("R600010", "영업판매", ("영업", "판매")),
    JobAlioCodeCandidate("R600011", "경비·청소", ("경비", "청소")),
    JobAlioCodeCandidate(
        "R600012",
        "이용·숙박·여행·오락·스포츠",
        ("이용", "숙박", "여행", "오락", "스포츠"),
    ),
    JobAlioCodeCandidate("R600013", "음식서비스", ("음식", "서비스", "조리")),
    JobAlioCodeCandidate("R600014", "건설", ("건축", "토목")),
    JobAlioCodeCandidate("R600015", "기계", ("기계설비",)),
    JobAlioCodeCandidate("R600016", "재료", ("소재",)),
    JobAlioCodeCandidate("R600017", "화학", ("화공",)),
    JobAlioCodeCandidate("R600018", "섬유·의복", ("섬유", "의복")),
    JobAlioCodeCandidate("R600019", "전기·전자", ("전기", "전자")),
    JobAlioCodeCandidate(
        "R600020",
        "정보통신",
        ("전산", "전산직", "IT", "정보보호", "보안", "네트워크", "개발", "데이터"),
    ),
    JobAlioCodeCandidate("R600021", "식품가공", ("식품", "가공")),
    JobAlioCodeCandidate("R600022", "인쇄·목재·가구·공예", ("인쇄", "목재", "가구", "공예")),
    JobAlioCodeCandidate("R600023", "환경·에너지·안전", ("환경", "에너지", "안전")),
    JobAlioCodeCandidate("R600024", "농림어업", ("농림", "어업", "농림어업")),
    JobAlioCodeCandidate(
        "R600025",
        "연구",
        ("연구직", "R&D", "연구개발"),
    ),
)


def list_job_alio_codes(code_type: JobAlioCodeType) -> list[JobAlioCodeCandidate]:
    if code_type == "institution":
        return list(_institution_codes())
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


@lru_cache(maxsize=1)
def _institution_codes() -> tuple[JobAlioCodeCandidate, ...]:
    aliases_by_code = _load_alio_aliases_from_csv(
        _resource_csv_text(ALIO_INSTITUTION_ALIASES_CSV)
    )
    return _load_institution_codes_from_csv(
        _resource_csv_text(JOB_ALIO_INSTITUTION_CODES_CSV),
        aliases_by_code=aliases_by_code,
    )


def _load_institution_codes_from_csv(
    csv_text: str,
    *,
    aliases_by_code: dict[str, dict[str, str | None]],
) -> tuple[JobAlioCodeCandidate, ...]:
    candidates: list[JobAlioCodeCandidate] = []
    seen_codes: set[str] = set()
    seen_names: set[str] = set()
    for row in csv.DictReader(StringIO(csv_text)):
        code = _clean_text(row.get("institution_code"))
        name = _clean_text(row.get("institution_name"))
        if not code or not name:
            raise InstitutionCodeDataError("institution code and name are required")
        _validate_institution_row(code=code, name=name, seen_codes=seen_codes, seen_names=seen_names)
        alias_row = aliases_by_code.get(code, {})
        aliases = _institution_aliases(
            name=name,
            normalized_name=alias_row.get("normalized_name"),
            aliases=alias_row.get("aliases"),
            manual_aliases=MANUAL_INSTITUTION_ALIASES.get(code, ()),
        )
        candidates.append(
            JobAlioCodeCandidate(
                code,
                name,
                aliases,
                source=INSTITUTION_CODE_SOURCE,
            )
        )
    if len(candidates) != EXPECTED_INSTITUTION_CODE_COUNT:
        raise InstitutionCodeDataError(
            f"expected {EXPECTED_INSTITUTION_CODE_COUNT} Job-ALIO institution codes, got {len(candidates)}"
        )
    return tuple(candidates)


def _load_alio_aliases_from_csv(csv_text: str) -> dict[str, dict[str, str | None]]:
    aliases_by_code: dict[str, dict[str, str | None]] = {}
    seen_codes: set[str] = set()
    seen_names: set[str] = set()
    for row in csv.DictReader(StringIO(csv_text)):
        code = _clean_text(row.get("institution_code"))
        name = _clean_text(row.get("institution_name"))
        if not code or not name:
            raise InstitutionCodeDataError("ALIO alias code and name are required")
        _validate_institution_row(code=code, name=name, seen_codes=seen_codes, seen_names=seen_names)
        aliases_by_code[code] = {
            "normalized_name": row.get("normalized_name"),
            "aliases": row.get("aliases"),
        }
    return aliases_by_code


def _resource_csv_text(resource_name: str) -> str:
    return resources.files("kr_gov_job_mcp").joinpath(resource_name).read_text(encoding="utf-8-sig")


def _validate_institution_row(
    *,
    code: str,
    name: str,
    seen_codes: set[str],
    seen_names: set[str],
) -> None:
    if not INSTITUTION_CODE_PATTERN.fullmatch(code):
        raise InstitutionCodeDataError(f"invalid Job-ALIO institution code: {code}")
    if code in seen_codes:
        raise InstitutionCodeDataError(f"duplicate Job-ALIO institution code: {code}")

    normalized_name = _normalize(name)
    if normalized_name in seen_names:
        raise InstitutionCodeDataError(f"duplicate normalized Job-ALIO institution name: {name}")

    seen_codes.add(code)
    seen_names.add(normalized_name)


class InstitutionCodeDataError(ValueError):
    """Raised when a packaged Job-ALIO institution resource is invalid."""


def _institution_aliases(
    *,
    name: str,
    normalized_name: str | None,
    aliases: str | None,
    manual_aliases: tuple[str, ...],
) -> tuple[str, ...]:
    raw_aliases = [
        normalized_name,
        *(aliases or "").split("|"),
        *manual_aliases,
    ]
    unique_aliases: list[str] = []
    seen = {_normalize(name)}
    for alias in raw_aliases:
        text = _clean_text(alias)
        normalized = _normalize(text)
        if not text or not normalized or normalized in seen:
            continue
        unique_aliases.append(text)
        seen.add(normalized)
    return tuple(unique_aliases)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    ignored = {" ", "\t", "\n", "\r", "·", "ㆍ", ".", "-", "_", "/"}
    return "".join(char for char in str(value).strip().lower() if char not in ignored)
