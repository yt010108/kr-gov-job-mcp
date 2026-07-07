import pytest

from kr_gov_job_mcp.codes import RegionLookupError, find_region_codes, resolve_region_code


def test_resolve_region_code_accepts_name_alias_and_code() -> None:
    assert resolve_region_code("서울").code == "R3010"
    assert resolve_region_code("서울특별시").code == "R3010"
    assert resolve_region_code("R3010").name == "서울"


def test_find_region_codes_returns_partial_matches() -> None:
    matches = find_region_codes("전")

    assert [match.name for match in matches] == ["대전", "전남", "전북"]


def test_resolve_region_code_rejects_unknown_or_ambiguous_query() -> None:
    with pytest.raises(RegionLookupError, match="unknown Job-ALIO region"):
        resolve_region_code("강남")

    with pytest.raises(RegionLookupError, match="ambiguous Job-ALIO region"):
        resolve_region_code("전")

