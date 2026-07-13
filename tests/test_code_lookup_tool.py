import pytest

from kr_gov_job_mcp.codes import list_job_alio_codes
from kr_gov_job_mcp.codes.job_alio_codes import (
    InstitutionCodeDataError,
    _load_institution_codes_from_csv,
)
from kr_gov_job_mcp.tools.code_lookup import (
    create_lookup_job_alio_codes_tool,
    create_lookup_region_codes_tool,
)


def test_lookup_job_alio_codes_returns_institution_candidate_by_alias() -> None:
    tool = create_lookup_job_alio_codes_tool()

    result = tool.handler({"code_type": "institution", "query": "KISA"})

    assert result == {
        "source": "job_alio",
        "code_type": "institution",
        "query": "KISA",
        "result_count": 1,
        "codes": [
            {
                "code": "C0399",
                "name": "한국인터넷진흥원",
                "aliases": ["KISA", "인터넷진흥원"],
                "score": 0.92,
                "source": "job_alio_recruit_filter_csv_2026_07_13",
            }
        ],
        "warnings": [],
    }


def test_lookup_job_alio_codes_returns_ncs_candidate_by_keyword() -> None:
    tool = create_lookup_job_alio_codes_tool()

    result = tool.handler({"code_type": "ncs", "query": "정보보호"})

    assert result["code_type"] == "ncs"
    assert result["query"] == "정보보호"
    assert result["result_count"] >= 1
    assert result["codes"][0] == {
        "code": "R600020",
        "name": "정보통신",
        "aliases": ["전산", "전산직", "IT", "정보보호", "보안", "네트워크", "개발", "데이터"],
        "score": 0.92,
        "source": "job_alio_seed_table",
    }
    assert result["warnings"] == []


def test_lookup_job_alio_codes_returns_institution_candidate_from_csv() -> None:
    tool = create_lookup_job_alio_codes_tool()

    result = tool.handler({"code_type": "institution", "query": "한국농수산식품유통공사"})

    assert result["code_type"] == "institution"
    assert result["query"] == "한국농수산식품유통공사"
    assert result["result_count"] == 1
    assert result["codes"][0] == {
        "code": "C0045",
        "name": "한국농수산식품유통공사",
        "aliases": [],
        "score": 0.98,
        "source": "job_alio_recruit_filter_csv_2026_07_13",
    }
    assert result["warnings"] == []


def test_lookup_job_alio_codes_returns_official_filter_code() -> None:
    tool = create_lookup_job_alio_codes_tool()

    result = tool.handler({"code_type": "institution", "query": "대구경북과학기술원"})

    assert result["code_type"] == "institution"
    assert result["query"] == "대구경북과학기술원"
    assert result["result_count"] == 1
    assert result["codes"][0] == {
        "code": "C0049",
        "name": "대구경북과학기술원",
        "aliases": [],
        "score": 0.98,
        "source": "job_alio_recruit_filter_csv_2026_07_13",
    }
    assert result["warnings"] == []


def test_lookup_job_alio_codes_keeps_manual_institution_aliases() -> None:
    tool = create_lookup_job_alio_codes_tool()

    result = tool.handler({"code_type": "institution", "query": "KISED"})

    assert result["result_count"] == 1
    assert result["codes"][0]["code"] == "C0451"
    assert result["codes"][0]["name"] == "창업진흥원"
    assert result["codes"][0]["aliases"] == ["KISED"]
    assert result["warnings"] == []


def test_lookup_job_alio_codes_contains_all_official_institution_filter_codes() -> None:
    institutions = list_job_alio_codes("institution")
    codes_by_name = {candidate.name: candidate.code for candidate in institutions}

    assert len(institutions) == 405
    assert len({candidate.code for candidate in institutions}) == 405
    assert len(codes_by_name) == 405
    assert all(candidate.code for candidate in institutions)
    assert {
        "대구경북과학기술원": "C0049",
        "한국전기연구원": "C0245",
        "한국전자통신연구원": "C0251",
        "아시아문화원(22.01.17 해산)": "C0869",
        "한국광물자원공사(21.09.10 해산)": "C0053",
        "한국광해관리공단(21.09.10 해산)": "C0086",
    }.items() <= codes_by_name.items()


@pytest.mark.parametrize(
    ("csv_text", "message"),
    [
        ("institution_code,institution_name\nBAD,기관\n", "invalid Job-ALIO institution code"),
        (
            "institution_code,institution_name\nC0001,기관가\nC0001,기관나\n",
            "duplicate Job-ALIO institution code",
        ),
        (
            "institution_code,institution_name\nC0001,기관·가\nC0002,기관가\n",
            "duplicate normalized Job-ALIO institution name",
        ),
    ],
)
def test_job_alio_institution_resource_rejects_invalid_rows(
    csv_text: str,
    message: str,
) -> None:
    with pytest.raises(InstitutionCodeDataError, match=message):
        _load_institution_codes_from_csv(csv_text, aliases_by_code={})


def test_lookup_job_alio_codes_contains_full_ncs_filter_names() -> None:
    codes = {candidate.name: candidate.code for candidate in list_job_alio_codes("ncs")}

    assert codes == {
        "사업관리": "R600001",
        "경영·회계·사무": "R600002",
        "금융·보험": "R600003",
        "교육·자연·사회과학": "R600004",
        "법률·경찰·소방·교도·국방": "R600005",
        "보건·의료": "R600006",
        "사회복지·종교": "R600007",
        "문화·예술·디자인·방송": "R600008",
        "운전·운송": "R600009",
        "영업판매": "R600010",
        "경비·청소": "R600011",
        "이용·숙박·여행·오락·스포츠": "R600012",
        "음식서비스": "R600013",
        "건설": "R600014",
        "기계": "R600015",
        "재료": "R600016",
        "화학": "R600017",
        "섬유·의복": "R600018",
        "전기·전자": "R600019",
        "정보통신": "R600020",
        "식품가공": "R600021",
        "인쇄·목재·가구·공예": "R600022",
        "환경·에너지·안전": "R600023",
        "농림어업": "R600024",
        "연구": "R600025",
    }


def test_lookup_job_alio_codes_returns_food_processing_ncs_code() -> None:
    tool = create_lookup_job_alio_codes_tool()

    result = tool.handler({"code_type": "ncs", "query": "식품가공"})

    assert result["result_count"] >= 1
    assert result["codes"][0]["code"] == "R600021"
    assert result["codes"][0]["name"] == "식품가공"


def test_lookup_job_alio_codes_returns_warning_without_matches() -> None:
    tool = create_lookup_job_alio_codes_tool()

    result = tool.handler({"code_type": "ncs", "query": "없는직무"})

    assert result["result_count"] == 0
    assert result["codes"] == []
    assert result["warnings"] == [
        "일치하는 Job-ALIO 코드 후보가 없습니다. 더 일반적인 기관명 또는 직무 키워드로 다시 조회하세요."
    ]


def test_lookup_job_alio_codes_rejects_invalid_arguments() -> None:
    tool = create_lookup_job_alio_codes_tool()

    with pytest.raises(ValueError, match="code_type is required"):
        tool.handler({"query": "정보보호"})

    with pytest.raises(ValueError, match="query is required"):
        tool.handler({"code_type": "ncs"})

    with pytest.raises(ValueError, match="unsupported lookup_job_alio_codes code_type"):
        tool.handler({"code_type": "region", "query": "서울"})

    with pytest.raises(ValueError, match="unsupported lookup_job_alio_codes arguments"):
        tool.handler({"code_type": "ncs", "query": "정보보호", "extra": True})


def test_lookup_region_codes_returns_matching_region() -> None:
    tool = create_lookup_region_codes_tool()

    result = tool.handler({"query": "서울시"})

    assert result == {
        "source": "job_alio",
        "code_type": "workRgnLst",
        "query": "서울시",
        "result_count": 1,
        "matches": [
            {
                "code": "R3010",
                "name": "서울",
                "aliases": ["서울시", "서울특별시"],
            }
        ],
    }


def test_lookup_region_codes_lists_all_regions_without_query() -> None:
    tool = create_lookup_region_codes_tool()

    result = tool.handler({})

    assert result["result_count"] == 18
    assert result["matches"][0]["name"] == "강원"
    assert result["matches"][-1]["name"] == "해외"
