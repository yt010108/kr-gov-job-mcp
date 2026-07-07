import pytest

from kr_gov_job_mcp.schemas.job import JobAlioSearchResult, JobAlioSummary
from kr_gov_job_mcp.tools.public_jobs import create_search_public_jobs_tool


def test_search_public_jobs_serializes_job_alio_results() -> None:
    captured_kwargs = {}

    def fake_search_jobs(**kwargs) -> JobAlioSearchResult:
        captured_kwargs.update(kwargs)
        return JobAlioSearchResult(
            page=kwargs["page"],
            limit=kwargs["limit"],
            total_count=2,
            jobs=[
                JobAlioSummary(
                    id="302423",
                    institution_name="창업진흥원",
                    institution_code="B552909",
                    title="2026년 제2차 신규직원 채용 공고",
                    start_date="2026-07-06",
                    end_date="2026-07-20",
                    is_ongoing=True,
                    ncs_codes=["R600020", "R600021"],
                    ncs_categories=["정보통신"],
                    employment_types=["무기계약직"],
                    recruitment_type="신입",
                    headcount=2,
                    work_regions=["대전", "세종"],
                    source_url="https://example.test/job",
                )
            ],
        )

    tool = create_search_public_jobs_tool(search_jobs=fake_search_jobs)

    result = tool.handler(
        {
            "keyword": "정보",
            "page": "2",
            "limit": "10",
            "ongoing_only": "true",
            "announcement_start_date": "2026-07-01",
            "announcement_end_date": "20260731",
        }
    )

    assert captured_kwargs == {
        "keyword": "정보",
        "page": 2,
        "limit": 10,
        "ongoing_only": True,
        "announcement_start_date": "20260701",
        "announcement_end_date": "20260731",
    }
    assert result["source"] == "job_alio"
    assert result["total_count"] == 2
    assert result["result_count"] == 1
    assert result["jobs"][0] == {
        "id": "302423",
        "source": "job_alio",
        "source_job_id": "302423",
        "institution_name": "창업진흥원",
        "institution_code": "B552909",
        "title": "2026년 제2차 신규직원 채용 공고",
        "start_date": "2026-07-06",
        "end_date": "2026-07-20",
        "is_ongoing": True,
        "employment_types": ["무기계약직"],
        "recruitment_type": "신입",
        "headcount": 2,
        "work_regions": ["대전", "세종"],
        "source_url": "https://example.test/job",
        "ncs_mappings": [
            {
                "code": "R600020",
                "display_name": "정보통신",
                "source_field": "ncsCdLst/ncsCdNmLst",
                "needs_verification": False,
            },
            {
                "code": "R600021",
                "display_name": None,
                "source_field": "ncsCdLst/ncsCdNmLst",
                "needs_verification": True,
            },
        ],
    }


def test_search_public_jobs_rejects_unknown_arguments() -> None:
    tool = create_search_public_jobs_tool(
        search_jobs=lambda **_kwargs: JobAlioSearchResult(page=1, limit=20, total_count=0)
    )

    with pytest.raises(ValueError, match="unsupported search_public_jobs arguments"):
        tool.handler({"new_grad_only": True})


def test_search_public_jobs_caps_limit() -> None:
    captured_kwargs = {}

    def fake_search_jobs(**kwargs) -> JobAlioSearchResult:
        captured_kwargs.update(kwargs)
        return JobAlioSearchResult(page=1, limit=kwargs["limit"], total_count=0)

    tool = create_search_public_jobs_tool(search_jobs=fake_search_jobs)

    result = tool.handler({"limit": 1000})

    assert captured_kwargs["limit"] == 100
    assert result["warnings"] == ["limit is capped at 100 for one Job-ALIO request."]


def test_search_public_jobs_resolves_region_name() -> None:
    captured_kwargs = {}

    def fake_search_jobs(**kwargs) -> JobAlioSearchResult:
        captured_kwargs.update(kwargs)
        return JobAlioSearchResult(page=1, limit=20, total_count=0)

    tool = create_search_public_jobs_tool(search_jobs=fake_search_jobs)

    result = tool.handler({"region": "서울특별시"})

    assert captured_kwargs["region_code"] == "R3010"
    assert result["resolved_filters"] == {
        "region": {
            "code": "R3010",
            "name": "서울",
            "aliases": ["서울시", "서울특별시"],
        }
    }


def test_search_public_jobs_rejects_region_code_conflict() -> None:
    tool = create_search_public_jobs_tool(
        search_jobs=lambda **_kwargs: JobAlioSearchResult(page=1, limit=20, total_count=0)
    )

    with pytest.raises(ValueError, match="region and region_code conflict"):
        tool.handler({"region": "서울", "region_code": "R3011"})
