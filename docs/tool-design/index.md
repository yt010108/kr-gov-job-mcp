# MCP 도구 설계

이 디렉터리는 MCP 도구별 입출력, 구현 상태, 데이터 소스를 분리해 관리한다.

번호는 README, 이슈, 도구 설계 문서에서 같은 순서로 참조하기 위한 식별자다. 파일명은 기존 링크 호환을 위해 유지한다.

| 번호 | 도구명 | 구분 | 우선순위 | 문서 | 목적 |
| --- | --- | --- | --- | --- | --- |
| 01 | `lookup_region_codes` | 코드 조회 | P0 | [lookup-region-codes.md](lookup-region-codes.md) | 자연어 지역명이나 Job-ALIO 지역 코드로 근무지 코드 후보를 조회한다. |
| 02 | `lookup_job_alio_codes` | 코드 조회 | P0 | [lookup-job-alio-codes.md](lookup-job-alio-codes.md) | 자연어 기관명/NCS명으로 Job-ALIO 검색 후보를 조회한다. |
| 10 | `resolve_ncs_code` | 코드 조회 | P0 | [resolve-ncs-code.md](resolve-ncs-code.md) | 자연어 직무명을 확정 가능한 Job-ALIO NCS 코드와 리포트 맥락으로 해석한다. |
| 03 | `search_public_jobs` | 수집 | P0 | [search-public-jobs.md](search-public-jobs.md) | 공공기관 채용공고와 인턴 정보를 검색하고 지원 가능 후보를 추린다. |
| 04 | `fetch_job_detail` | 수집 | P0 | [fetch-job-detail.md](fetch-job-detail.md) | 공고 상세와 직무기술서를 구조화해 분석 기준 데이터로 만든다. |
| 05 | `map_ncs_competencies` | 분석 | P0 | [map-ncs-competencies.md](map-ncs-competencies.md) | 공고와 직무기술서에서 NCS/KSA 역량을 추출한다. |
| 06 | `analyze_institution_strategy` | 분석 | P0 | [analyze-institution-strategy.md](analyze-institution-strategy.md) | 기관의 최근 사업 방향과 직무 연결 포인트를 요약한다. |
| 07 | `analyze_institution_weakness` | 분석 | P0 | [analyze-institution-weakness.md](analyze-institution-weakness.md) | 기관의 부족한 점과 개선 과제를 분석 가능한 형태로 정리한다. |
| 08 | `prepare_institution_interview` | 분석 | P0 | [prepare-institution-interview.md](prepare-institution-interview.md) | 주요사업, 연구/정책 자료, 국회 지적사항을 면접 질문 카드로 변환한다. |
| 09 | `analyze_job_fit_report` | 분석 | P0 | [analyze-job-fit-report.md](analyze-job-fit-report.md) | 공고 내용, NCS, 기관 정보를 연결해 준비 리포트를 만든다. |

## 구현 순서

1. 01 `lookup_region_codes`
2. 02 `lookup_job_alio_codes`
3. 10 `resolve_ncs_code`
4. 03 `search_public_jobs`
5. 04 `fetch_job_detail`
6. 05 `map_ncs_competencies`
7. 09 `analyze_job_fit_report`
8. 06 `analyze_institution_strategy`
9. 07 `analyze_institution_weakness`
10. 08 `prepare_institution_interview`
11. `collect_institution_context`
