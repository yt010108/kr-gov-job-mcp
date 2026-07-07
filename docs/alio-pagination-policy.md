# ALIO 페이지네이션 정책

작성일: 2026-07-07 KST

## 목적

ALIO 항목별 보고서 목록이 대량인 기관을 안전하게 수집하기 위한 페이지네이션 정책을 정한다.
기본 collector는 raw observation과 parser/ERD 설계에 필요한 샘플을 모으는 도구이며, 전체 목록
수집은 명시적 full collection 모드에서만 수행한다.

## 배경

3개 기관 검증에서 한국전력공사 `49-1` 입찰공고 `B1030`의 `total_count`가 92,741건으로 확인됐다.
반면 parser 설계와 ERD v0 작성에는 첫 페이지와 대표 상세 HTML만으로도 충분했다. 따라서 기본값은
작고 재현 가능한 observation을 우선하고, 대량 수집은 필터와 재개 가능한 checkpoint를 요구한다.

## 수집 모드

| 모드 | 목적 | 기본 동작 | 사용 조건 |
| --- | --- | --- | --- |
| `raw_observation` | 필드/HTML 구조 관찰, parser 설계 | 항목별 1페이지, 첫 상세 1건 | 기본값 |
| `sample_validation` | 기관 몇 곳의 결측/total_count 비교 | 항목별 1페이지, 대표 상세 1건 | 검증 이슈 또는 수동 실행 |
| `full_collection` | 분석용 전체 목록 확보 | 명시한 page/filter 범위만 순회 | 사용자가 명시적으로 요청 |
| `resume_collection` | 중단된 full collection 재개 | checkpoint 이후 page부터 순회 | checkpoint가 있을 때 |

기본 collector는 `raw_observation`으로 간주한다. `full_collection`은 다음 옵션이 명시돼야 한다.

- `collection_mode=full`
- `max_pages`
- `started_at` 또는 실행 id
- 대량 항목이면 검색어 또는 기간 필터
- 중단/재개를 위한 checkpoint 저장 위치

## 항목별 기본 page 정책

| 항목 | 내부 번호 | 유형 | observation 기본 | full 기본 cap | full hard cap | 비고 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 6-2 직원 채용정보 | `B1020` | 수시 | 1 page | 10 pages | 50 pages | Job-ALIO와 중복 후보라 전체 수집 우선순위 낮음 |
| 40 주요사업 | `31501` | 정기 | 전체 응답 1회 | 전체 응답 1회 | 전체 응답 1회 | 정기 보고서 목록은 page 순회 대상 아님 |
| 47-1 국회지적사항 | `B1210` | 수시 | 1 page | 10 pages | 50 pages | 개선 과제 분석 후보 |
| 49-1 입찰공고 | `B1030` | 수시 대량 | 1 page | 5 pages | 20 pages | 필터 없이는 hard cap 이상 금지 |
| 49-2 수의계약 | `7030` | 정기 | 전체 응답 1회 | 전체 응답 1회 | 전체 응답 1회 | 첨부 XLSX가 실제 계약 row 원천 |
| 50-1 자체 연구 보고서 | `B1040` | 수시 | 1 page | 10 pages | 50 pages | 0건 가능 |
| 50-2 외부용역 연구 보고서 | `B1260` | 수시 | 1 page | 10 pages | 50 pages | 연구보고서 분석 후보 |

hard cap을 넘기는 수집은 별도 명시 옵션이 있어도 기본 collector에서 수행하지 않는다. 대량 archival이
필요하면 별도 batch job으로 분리한다.

## B1030 대량 항목 정책

`B1030` 입찰공고는 total_count가 수만 건으로 커질 수 있어 특별 취급한다.

필터 없는 동작:

- observation: 1페이지까지만 저장
- full_collection: 기본 5페이지, hard cap 20페이지
- hard cap 도달 시 `stopped_reason=high_volume_cap` 기록

필터가 필요한 경우:

- `total_count > 1000`이면 전체 수집 전에 검색어 또는 기간 필터가 필요하다.
- 기간 필터는 우선 31일 이하 window를 권장한다.
- 제목 검색어가 있으면 검색어와 page 범위를 metadata에 남긴다.
- 필터 후에도 `total_count > 10000`이면 window를 더 줄인다.

권장 필터:

| 필터 | 목적 |
| --- | --- |
| `keyword` | 기관 주요 사업/직무 관련 입찰만 수집 |
| `date_from`, `date_to` | 최근 기간 또는 특정 연도 단위로 분할 |
| `bid_type` | 입찰 유형 구분이 확인되면 사용 |

## 요청 속도와 retry

기본 속도:

- source별 1 request/second
- HTML 상세와 목록 page를 같은 source budget으로 계산
- full_collection에서는 batch 사이 5초 pause 권장

retry:

| 상황 | 처리 |
| --- | --- |
| connect/read timeout | 최대 3회, 1초/2초/4초 backoff |
| HTTP 429 | 즉시 중단, `stopped_reason=rate_limited` |
| HTTP 5xx | 최대 2회 retry 후 중단 |
| JSON parse 실패 | 해당 page 실패로 기록하고 중단 |
| 같은 page 반복 실패 | checkpoint 저장 후 중단 |

retry 후 성공한 page도 metadata에 `retry_count`를 남긴다.

## 중단/재개 기준

중단 조건:

- `max_pages` 도달
- item hard cap 도달
- rate limit 감지
- 같은 page 반복 실패
- 사용자가 중단 요청
- `total_count`가 실행 중 급격히 바뀌어 page window가 불안정해짐

checkpoint 필드:

| 필드 | 의미 |
| --- | --- |
| `run_id` | 수집 실행 id |
| `institution_id` | `apbaId` |
| `item_no` | 사용자 항목번호 |
| `report_form_root_no` | ALIO 내부 번호 |
| `query` | 검색어/기간/기타 필터 |
| `last_successful_page` | 마지막 성공 page |
| `next_page` | 재개할 page |
| `total_count_observed` | 마지막 관찰 total_count |
| `page_size_observed` | page당 row 수 |
| `stopped_reason` | 중단 사유 |

재개 시에는 같은 query hash를 요구한다. query가 바뀌면 새 run으로 취급한다.

## page metadata 저장

모든 목록 raw sample metadata에는 page 관찰 정보를 남긴다.

| 필드 | 의미 |
| --- | --- |
| `collection_mode` | `raw_observation`, `sample_validation`, `full_collection`, `resume_collection` |
| `page_no` | 요청 page 번호 |
| `page_size` | 응답 row 수 또는 요청 countPerPage |
| `row_count` | 실제 row 수 |
| `total_count` | 응답 total_count |
| `total_pages_estimated` | `ceil(total_count / page_size)` 후보 |
| `page_limit` | 이번 실행에서 허용한 page 수 |
| `is_high_volume` | `total_count > high_volume_threshold` |
| `high_volume_threshold` | 기본 1000 |
| `stopped_reason` | cap, no_next_page, rate_limited 등 |
| `query_hash` | 재현용 query hash |

raw sample id 권장 형식:

| 모드 | sample_id |
| --- | --- |
| observation | `{apbaId}-item-{item_no}-{report_form_root_no}-reports-page-1` |
| full page | `{apbaId}-item-{item_no}-{report_form_root_no}-reports-page-{page_no}` |
| checkpoint | `{apbaId}-item-{item_no}-{report_form_root_no}-checkpoint` |

기존 1페이지 sample id는 호환을 위해 유지할 수 있지만, metadata에는 `page_no=1`을 반드시 넣는다.

## full collection 안전장치

full collection 실행 전 확인할 것:

1. 항목이 정기 보고서인지 수시 게시판인지 확인한다.
2. `total_count`를 1페이지에서 먼저 읽는다.
3. `total_count > 1000`이면 high-volume으로 표시한다.
4. `B1030`이고 high-volume이면 검색어/기간 필터 없이 hard cap을 넘기지 않는다.
5. 예상 요청 수와 예상 소요 시간을 로그에 남긴다.
6. checkpoint가 없으면 page 1부터, 있으면 `next_page`부터 시작한다.

예상 요청 수:

```txt
list_requests = min(total_pages_estimated, page_limit)
detail_requests = min(row_count_for_selected_pages, detail_limit)
estimated_requests = list_requests + detail_requests
```

기본 full collection은 목록 page만 수집한다. 상세 HTML은 별도 `include_report_html=true`와
`detail_limit`이 있을 때만 가져온다.

## parser/ERD 작업과의 관계

전체 수집 전에도 다음 작업은 가능하다.

- 항목별 field inventory
- HTML 구조 조사
- attachment metadata 정규화
- ERD v0
- Job-ALIO와 `B1020` 매칭 규칙 설계

전체 수집이 필요한 작업:

- 기관별 장기 입찰/계약 시계열 분석
- 전체 연구보고서 corpus 구축
- 과거 채용공고 회귀 분석
- 대량 matching 품질 평가

## 구현 메모

향후 collector 옵션 후보:

| 옵션 | 기본값 | 의미 |
| --- | --- | --- |
| `collection_mode` | `raw_observation` | 수집 모드 |
| `page_limit` | item policy 기본값 | 이번 실행 page 제한 |
| `hard_page_limit` | item policy hard cap | 안전 상한 |
| `high_volume_threshold` | `1000` | 대량 항목 기준 |
| `require_filter_for_high_volume` | `true` | 대량 full 수집 필터 요구 |
| `resume_from_checkpoint` | `false` | checkpoint 재개 |
| `include_report_html` | `true` in observation | 상세 HTML 저장 여부 |
| `detail_limit` | `1` in observation | 상세 HTML fetch 개수 |

collector는 page 순회를 시작하기 전에 item policy를 계산하고, 중단 시에도 마지막 metadata/checkpoint를
남겨야 한다.
