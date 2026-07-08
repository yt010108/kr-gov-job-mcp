import pytest

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
                "source": "job_alio_seed_table",
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
