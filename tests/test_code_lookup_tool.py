import pytest

from kr_gov_job_mcp.codes import list_job_alio_codes
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
                "source": "alio_institution_codes_csv_2026_07_08",
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
        "source": "alio_institution_codes_csv_2026_07_08",
    }
    assert result["warnings"] == []


def test_lookup_job_alio_codes_returns_filter_name_fallback_without_code() -> None:
    tool = create_lookup_job_alio_codes_tool()

    result = tool.handler({"code_type": "institution", "query": "대구경북과학기술원"})

    assert result["code_type"] == "institution"
    assert result["query"] == "대구경북과학기술원"
    assert result["result_count"] == 1
    assert result["codes"][0] == {
        "code": None,
        "name": "대구경북과학기술원",
        "aliases": [],
        "score": 0.98,
        "source": "alio_open_data_recruit_filter_2026_07_08",
        "fallback_search": {
            "tool": "search_public_jobs",
            "arguments": {"keyword": "대구경북과학기술원"},
            "reason": "기관코드가 확인되지 않아 기관명을 공고 키워드로 검색합니다.",
        },
    }
    assert result["warnings"] == [
        "일부 기관명 후보는 기관코드가 확인되지 않아 search_public_jobs의 institution_code로 바로 사용할 수 없습니다. fallback_search.arguments.keyword로 기관명을 검색하세요."
    ]


def test_lookup_job_alio_codes_keeps_manual_institution_aliases() -> None:
    tool = create_lookup_job_alio_codes_tool()

    result = tool.handler({"code_type": "institution", "query": "KISED"})

    assert result["result_count"] == 1
    assert result["codes"][0]["code"] == "C0451"
    assert result["codes"][0]["name"] == "창업진흥원"
    assert result["codes"][0]["aliases"] == ["KISED"]
    assert result["warnings"] == []


def test_lookup_job_alio_codes_contains_institution_filter_names() -> None:
    institutions = list_job_alio_codes("institution")

    assert len(institutions) == 405
    assert sum(1 for candidate in institutions if candidate.code is None) == 50
    assert "한국농수산식품유통공사" in {candidate.name for candidate in institutions}
    assert "대구경북과학기술원" in {candidate.name for candidate in institutions}


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
