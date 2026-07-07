from kr_gov_job_mcp.tools.code_lookup import (
    create_lookup_institution_codes_tool,
    create_lookup_region_codes_tool,
)


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


def test_lookup_institution_codes_returns_matching_alias() -> None:
    tool = create_lookup_institution_codes_tool()

    result = tool.handler({"query": "전남대병원"})

    assert result == {
        "source": "job_alio",
        "code_type": "pblntInstCd",
        "query": "전남대병원",
        "result_count": 1,
        "matches": [
            {
                "code": "C0113",
                "name": "전남대학교병원",
                "aliases": ["전남대병원", "전남대학교 병원", "화순전남대학교병원"],
                "confidence": "high",
            }
        ],
    }


def test_lookup_institution_codes_lists_seed_institutions_without_query() -> None:
    tool = create_lookup_institution_codes_tool()

    result = tool.handler({})

    assert result["result_count"] == 4
    assert result["matches"][0]["name"] == "한국농수산식품유통공사"
