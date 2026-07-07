import pytest

from kr_gov_job_mcp.schemas.job import (
    JobAlioAttachment,
    JobAlioDetail,
    JobAlioSearchResult,
    JobAlioStep,
    JobAlioSummary,
)
from kr_gov_job_mcp.tools.public_jobs import (
    create_analyze_job_fit_report_tool,
    create_fetch_job_detail_tool,
    create_search_public_jobs_tool,
)


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


def test_search_public_jobs_zero_results_include_diagnostics_and_suggestions() -> None:
    def fake_search_jobs(**kwargs) -> JobAlioSearchResult:
        return JobAlioSearchResult(page=kwargs["page"], limit=kwargs["limit"], total_count=0)

    tool = create_search_public_jobs_tool(search_jobs=fake_search_jobs)

    result = tool.handler(
        {
            "keyword": "전남대학교 병원",
            "region": "서울",
            "ongoing_only": True,
            "limit": 5,
        }
    )

    diagnostics = result["diagnostics"]
    suggestions = result["suggested_next_queries"]

    assert result["result_count"] == 0
    assert diagnostics["no_result"] is True
    assert diagnostics["applied_filters"]["keyword"] == "전남대학교 병원"
    assert diagnostics["resolved_filters"]["region"]["code"] == "R3010"
    assert diagnostics["keyword_scope"] == "keyword는 잡알리오 채용공고 제목 검색어로 전달됩니다."
    assert any("현재 접수 중인 공고만" in cause for cause in diagnostics["possible_causes"])
    assert any("기관명" in cause for cause in diagnostics["possible_causes"])
    assert any(suggestion["arguments"].get("ongoing_only") is False for suggestion in suggestions)
    assert any(suggestion["tool"] == "lookup_institution_codes" for suggestion in suggestions)
    assert any(
        set(suggestion["arguments"]) <= {"keyword", "page", "limit", "ongoing_only"}
        for suggestion in suggestions
    )


def test_search_public_jobs_zero_results_suggest_region_filter_for_region_keyword() -> None:
    def fake_search_jobs(**kwargs) -> JobAlioSearchResult:
        return JobAlioSearchResult(page=kwargs["page"], limit=kwargs["limit"], total_count=0)

    tool = create_search_public_jobs_tool(search_jobs=fake_search_jobs)

    result = tool.handler({"keyword": "서울", "ongoing_only": False})

    suggestions = result["suggested_next_queries"]

    assert any(
        suggestion["tool"] == "search_public_jobs"
        and suggestion["arguments"].get("region") == "서울"
        and "keyword" not in suggestion["arguments"]
        for suggestion in suggestions
    )


def test_search_public_jobs_rejects_region_code_conflict() -> None:
    tool = create_search_public_jobs_tool(
        search_jobs=lambda **_kwargs: JobAlioSearchResult(page=1, limit=20, total_count=0)
    )

    with pytest.raises(ValueError, match="region and region_code conflict"):
        tool.handler({"region": "서울", "region_code": "R3011"})


def test_fetch_job_detail_serializes_detail_fields() -> None:
    captured_job_ids = []

    def fake_fetch_job_detail(job_id: str) -> JobAlioDetail:
        captured_job_ids.append(job_id)
        return JobAlioDetail(
            id=job_id,
            institution_name="창업진흥원",
            institution_code="B552909",
            title="2026년 제2차 신규직원 채용 공고",
            start_date="2026-07-06",
            end_date="2026-07-20",
            is_ongoing=True,
            ncs_codes=["R600020"],
            ncs_categories=["정보통신"],
            employment_types=["무기계약직"],
            recruitment_type="신입",
            headcount=2,
            work_regions=["대전"],
            source_url="https://example.test/job",
            qualification="지원자격 원문",
            preferred_conditions="우대조건 원문",
            preference="가점 원문",
            disqualification_reason="결격사유 원문",
            screening_procedure="서류, 면접",
            replacement_recruitment=False,
            attachments=[
                JobAlioAttachment(
                    sort_no=1,
                    file_no=3060250,
                    name="직무기술서.pdf",
                    file_type="A",
                    url="https://example.test/duty.pdf",
                )
            ],
            steps=[
                JobAlioStep(
                    sort_no=0,
                    title="서류전형",
                    step_sn=123,
                    min_step_sn=100,
                    max_step_sn=200,
                    headcount=2,
                    applicant_count=10,
                    competition_rate=5.0,
                    occurrence_date="2026-07-21",
                )
            ],
        )

    tool = create_fetch_job_detail_tool(fetch_job_detail=fake_fetch_job_detail)

    result = tool.handler({"job_id": "302423"})

    assert captured_job_ids == ["302423"]
    assert result["source"] == "job_alio"
    assert result["query"] == {"job_id": "302423"}
    assert result["job"]["qualification"] == "지원자격 원문"
    assert result["job"]["preferred_conditions"] == "우대조건 원문"
    assert result["job"]["screening_procedure"] == "서류, 면접"
    assert result["job"]["attachments"] == [
        {
            "sort_no": 1,
            "file_no": 3060250,
            "name": "직무기술서.pdf",
            "file_type": "A",
            "url": "https://example.test/duty.pdf",
            "duty_description_candidate": True,
        }
    ]
    assert result["job"]["steps"] == [
        {
            "sort_no": 0,
            "title": "서류전형",
            "step_sn": 123,
            "min_step_sn": 100,
            "max_step_sn": 200,
            "headcount": 2,
            "applicant_count": 10,
            "competition_rate": 5.0,
            "occurrence_date": "2026-07-21",
        }
    ]


def test_fetch_job_detail_accepts_same_id_aliases() -> None:
    tool = create_fetch_job_detail_tool(
        fetch_job_detail=lambda job_id: JobAlioDetail(id=job_id, title="상세 공고")
    )

    result = tool.handler(
        {
            "job_id": "302423",
            "source_job_id": "302423",
            "recruitment_notice_sn": "302423",
        }
    )

    assert result["job"]["id"] == "302423"


def test_fetch_job_detail_rejects_missing_or_conflicting_ids() -> None:
    tool = create_fetch_job_detail_tool(
        fetch_job_detail=lambda job_id: JobAlioDetail(id=job_id, title="상세 공고")
    )

    with pytest.raises(ValueError, match="fetch_job_detail requires job_id"):
        tool.handler({})

    with pytest.raises(ValueError, match="conflicting fetch_job_detail ids"):
        tool.handler({"job_id": "302423", "source_job_id": "302424"})


def test_analyze_job_fit_report_fetches_detail_and_returns_preparation_report() -> None:
    captured_job_ids = []

    def fake_fetch_job_detail(job_id: str) -> JobAlioDetail:
        captured_job_ids.append(job_id)
        return JobAlioDetail(
            id=job_id,
            institution_name="한국인터넷진흥원",
            title="정보보호 분야 채용 공고",
            source_url="https://example.test/job",
            ncs_codes=["R600020"],
            ncs_categories=["정보통신"],
            qualification="정보보호 관련 지식 필요",
            preferred_conditions="정보보안기사 우대",
            screening_procedure="서류전형, 면접전형",
            attachments=[
                JobAlioAttachment(
                    name="NCS 직무기술서.pdf",
                    file_type="A",
                    url="https://example.test/duty.pdf",
                )
            ],
        )

    tool = create_analyze_job_fit_report_tool(fetch_job_detail=fake_fetch_job_detail)

    result = tool.handler(
        {
            "job_id": "302423",
            "target_role": "정보보호",
            "known_skills": ["웹 보안", "정보보안기사"],
        }
    )

    assert captured_job_ids == ["302423"]
    assert result["source"] == "job_alio"
    assert result["query"] == {
        "job_id": "302423",
        "target_role": "정보보호",
        "known_skills": ["웹 보안", "정보보안기사"],
    }
    assert result["job_id"] == "302423"
    assert result["job_title"] == "정보보호 분야 채용 공고"
    assert result["applicant_target_role"] == "정보보호"
    assert any(item["priority"] == "P0" for item in result["preparation_items"])
    assert any(item["source_type"] == "duty_description" for item in result["evidence_links"])
    assert any(note["field"] == "institution_signals" for note in result["verification_notes"])


def test_analyze_job_fit_report_rejects_unknown_arguments_and_bad_skills() -> None:
    tool = create_analyze_job_fit_report_tool(
        fetch_job_detail=lambda job_id: JobAlioDetail(id=job_id, title="상세 공고")
    )

    with pytest.raises(ValueError, match="unsupported analyze_job_fit_report arguments"):
        tool.handler({"job_id": "302423", "extra": True})

    with pytest.raises(ValueError, match="expected list value"):
        tool.handler({"job_id": "302423", "known_skills": "정보보호"})
