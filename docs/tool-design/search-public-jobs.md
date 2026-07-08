# 03. search_public_jobs

## 구현 상태

Job-ALIO 검색 기반 1차 구현 완료. Cleaneye 채용/인턴 공고 사이트 통합과 `new_grad_only`
같은 코드 테이블 기반 필터는 아직 보류한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `keyword` | 검색 키워드 |
| `page` | 페이지 번호 |
| `limit` | 반환할 최대 공고 수. 한 번의 Job-ALIO 요청 기준 최대 100 |
| `ongoing_only` | 진행 중인 공고만 조회할지 여부 |
| `institution_code` | Job-ALIO 기관 코드. 자연어 기관명은 `lookup_job_alio_codes`로 먼저 조회하고, `code`가 있는 후보만 입력 |
| `ncs_code` | Job-ALIO NCS 코드 필터. 자연어 직무명/NCS명은 `lookup_job_alio_codes`로 먼저 조회 |
| `region` | 자연어 지역명 |
| `region_code` | Job-ALIO 지역 코드 |
| `academic_condition_code` | 학력 조건 코드 |
| `employment_type_code` | 고용형태 코드 |
| `recruitment_type` | 채용 구분 코드 |
| `replacement_only` | 대체인력 채용만 조회할지 여부 |
| `announcement_start_date` | 공고 시작일 필터. `YYYY-MM-DD` 또는 `YYYYMMDD` |
| `announcement_end_date` | 공고 종료일 필터. `YYYY-MM-DD` 또는 `YYYYMMDD` |
| `institution_type` | 기관 유형 코드 |
| `institution_classification` | 기관 분류 코드 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 데이터 출처. 현재 값은 `job_alio` |
| `query` | 정규화된 검색 입력 |
| `resolved_filters` | 자연어 입력을 코드로 바꾼 필터 정보 |
| `page` | 응답 페이지 번호 |
| `limit` | 응답당 요청 공고 수 |
| `total_count` | Job-ALIO 검색 결과 전체 수 |
| `result_count` | 현재 응답에 포함된 공고 수 |
| `jobs` | 공고 요약 목록 |
| `jobs[].id` | 내부적으로 사용하는 공고 ID |
| `jobs[].source` | 공고 출처. 현재 값은 `job_alio` |
| `jobs[].source_job_id` | Job-ALIO 원본 공고 ID |
| `jobs[].institution_name` | 기관명 |
| `jobs[].institution_code` | 기관 코드 |
| `jobs[].title` | 공고명 |
| `jobs[].start_date` | 공고 시작일 |
| `jobs[].end_date` | 공고 마감일 |
| `jobs[].is_ongoing` | 진행 여부 |
| `jobs[].employment_types` | 고용 유형 목록 |
| `jobs[].recruitment_type` | 채용 구분 |
| `jobs[].headcount` | 채용 인원 |
| `jobs[].work_regions` | 근무 지역 목록 |
| `jobs[].source_url` | 원문 링크 |
| `jobs[].ncs_mappings` | NCS 코드/표시명 매핑 후보 목록 |
| `jobs[].ncs_mappings[].code` | NCS 코드 |
| `jobs[].ncs_mappings[].display_name` | NCS 표시명 |
| `jobs[].ncs_mappings[].source_field` | 원천 필드명. 현재 값은 `ncsCdLst/ncsCdNmLst` |
| `jobs[].ncs_mappings[].needs_verification` | 코드와 표시명 쌍 확인 필요 여부 |
| `warnings` | 검색 경고 목록 |

## 데이터 소스

- 잡알리오 채용정보 Ajax 목록 응답

## 처리 원칙

- `region_code`가 있으면 그대로 Job-ALIO 검색에 사용한다.
- `region`이 있으면 `lookup_region_codes`와 같은 resolver로 Job-ALIO 지역 코드로 바꾼다.
- `region`과 `region_code`가 서로 충돌하면 검색하지 않고 오류를 낸다.
- `institution_code`, `ncs_code`는 Job-ALIO 코드 입력 필드이며, 자연어 기관명이나 직무명은
  `lookup_job_alio_codes`로 후보를 확인한 뒤 전달한다.
- 기관명 lookup 결과에서 `code`가 `null`인 후보는 표시명 확인용이며,
  `institution_code`로 바로 전달하지 않고 `fallback_search.arguments.keyword`의 기관명으로 검색한다.
- 서버 내부에서 기관명/NCS명 자동 resolver를 실행하지 않는다.
- `limit`은 한 번의 Job-ALIO 요청 기준 최대 100으로 제한한다.
