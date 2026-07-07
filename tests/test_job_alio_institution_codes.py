import pytest

from kr_gov_job_mcp.codes import (
    InstitutionLookupError,
    find_institution_codes,
    resolve_institution_code,
)


def test_resolve_institution_code_accepts_name_alias_and_code() -> None:
    assert resolve_institution_code("전남대병원").code == "C0113"
    assert resolve_institution_code("전남대학교 병원").code == "C0113"
    assert resolve_institution_code("C0045").name == "한국농수산식품유통공사"
    assert resolve_institution_code("aT").code == "C0045"


def test_find_institution_codes_returns_partial_matches() -> None:
    matches = find_institution_codes("진흥원")

    assert {match.name for match in matches} == {"한국인터넷진흥원", "창업진흥원"}


def test_resolve_institution_code_rejects_unknown_or_ambiguous_query() -> None:
    with pytest.raises(InstitutionLookupError, match="unknown Job-ALIO institution"):
        resolve_institution_code("없는기관")

    with pytest.raises(InstitutionLookupError, match="ambiguous Job-ALIO institution"):
        resolve_institution_code("진흥원")
