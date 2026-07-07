"""Job-ALIO work region code lookup.

Codes were verified from the public Job-ALIO recruitment search page
``workRgnLst`` options on 2026-07-07 KST.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class RegionLookupError(ValueError):
    """Raised when a natural-language region cannot be resolved safely."""


@dataclass(frozen=True)
class JobAlioRegionCode:
    code: str
    name: str
    aliases: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "aliases": list(self.aliases),
        }


REGION_CODES: tuple[JobAlioRegionCode, ...] = (
    JobAlioRegionCode("R3018", "강원", ("강원도", "강원특별자치도")),
    JobAlioRegionCode("R3017", "경기", ("경기도",)),
    JobAlioRegionCode("R3022", "경남", ("경상남도",)),
    JobAlioRegionCode("R3021", "경북", ("경상북도",)),
    JobAlioRegionCode("R3015", "광주", ("광주광역시",)),
    JobAlioRegionCode("R3013", "대구", ("대구광역시",)),
    JobAlioRegionCode("R3012", "대전", ("대전광역시",)),
    JobAlioRegionCode("R3014", "부산", ("부산광역시",)),
    JobAlioRegionCode("R3010", "서울", ("서울시", "서울특별시")),
    JobAlioRegionCode("R3026", "세종", ("세종시", "세종특별자치시")),
    JobAlioRegionCode("R3016", "울산", ("울산광역시",)),
    JobAlioRegionCode("R3011", "인천", ("인천광역시",)),
    JobAlioRegionCode("R3023", "전남", ("전라남도",)),
    JobAlioRegionCode("R3024", "전북", ("전라북도", "전북특별자치도")),
    JobAlioRegionCode("R3025", "제주", ("제주도", "제주특별자치도")),
    JobAlioRegionCode("R3019", "충남", ("충청남도",)),
    JobAlioRegionCode("R3020", "충북", ("충청북도",)),
    JobAlioRegionCode("R3030", "해외", ("국외",)),
)


def list_region_codes() -> list[JobAlioRegionCode]:
    return list(REGION_CODES)


def find_region_codes(query: str | None = None) -> list[JobAlioRegionCode]:
    normalized_query = _normalize(query)
    if not normalized_query:
        return list_region_codes()

    exact_matches = [
        region
        for region in REGION_CODES
        if normalized_query == _normalize(region.code)
        or normalized_query == _normalize(region.name)
        or normalized_query in {_normalize(alias) for alias in region.aliases}
    ]
    if exact_matches:
        return exact_matches

    return [
        region
        for region in REGION_CODES
        if normalized_query in _normalize(region.name)
        or any(normalized_query in _normalize(alias) for alias in region.aliases)
    ]


def resolve_region_code(query: str) -> JobAlioRegionCode:
    matches = find_region_codes(query)
    if not matches:
        supported = ", ".join(region.name for region in REGION_CODES)
        raise RegionLookupError(f"unknown Job-ALIO region: {query}. supported: {supported}")
    if len(matches) > 1:
        candidates = ", ".join(f"{region.name}({region.code})" for region in matches)
        raise RegionLookupError(f"ambiguous Job-ALIO region: {query}. candidates: {candidates}")
    return matches[0]


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    return "".join(str(value).strip().lower().split())

