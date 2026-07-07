# MCP 도구 설계

이 디렉터리는 MCP 도구별 입출력, 구현 상태, 데이터 소스를 분리해 관리한다.

| 도구명 | 구분 | 우선순위 | 문서 | 목적 |
| --- | --- | --- | --- | --- |
| `lookup_region_codes` | 코드 조회 | P0 | [lookup-region-codes.md](lookup-region-codes.md) | 자연어 지역명이나 Job-ALIO 지역 코드로 근무지 코드 후보를 조회한다. |
| `search_public_jobs` | 수집 | P0 | [search-public-jobs.md](search-public-jobs.md) | 공공기관 채용공고와 인턴 정보를 검색하고 지원 가능 후보를 추린다. |
| `fetch_job_detail` | 수집 | P0 | [fetch-job-detail.md](fetch-job-detail.md) | 공고 상세와 직무기술서를 구조화해 분석 기준 데이터로 만든다. |
| `map_ncs_competencies` | 분석 | P0 | [map-ncs-competencies.md](map-ncs-competencies.md) | 공고와 직무기술서에서 NCS/KSA 역량을 추출한다. |
| `analyze_institution_strategy` | 분석 | P0 | [analyze-institution-strategy.md](analyze-institution-strategy.md) | 기관의 최근 사업 방향과 직무 연결 포인트를 요약한다. |
| `analyze_institution_weakness` | 분석 | P0 | [analyze-institution-weakness.md](analyze-institution-weakness.md) | 기관의 부족한 점과 개선 과제를 분석 가능한 형태로 정리한다. |
| `analyze_job_fit_report` | 분석 | P0 | [analyze-job-fit-report.md](analyze-job-fit-report.md) | 공고 내용, NCS, 기관 정보를 연결해 준비 리포트를 만든다. |

## 구현 순서

1. `lookup_region_codes`
2. `search_public_jobs`
3. `fetch_job_detail`
4. `collect_institution_context`
5. `analyze_job_fit_report`

`map_ncs_competencies`, `analyze_institution_strategy`, `analyze_institution_weakness`는 현재
분석 helper와 schema는 있으나 MCP tool로는 아직 분리 구현하지 않았다.

