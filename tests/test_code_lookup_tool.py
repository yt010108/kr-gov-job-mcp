from kr_gov_job_mcp.tools.code_lookup import create_lookup_region_codes_tool


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

