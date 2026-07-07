# 01. lookup_region_codes

## 구현 상태

Job-ALIO 채용정보 검색 페이지의 `workRgnLst` option 값을 기준으로 1차 구현 완료.
`search_public_jobs`의 자연어 지역명 변환과 같은 resolver를 공유한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `query` | 자연어 지역명 또는 Job-ALIO 지역 코드. 비우면 전체 지역 코드 목록 조회 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 데이터 출처. 현재 값은 `job_alio` |
| `code_type` | 코드 유형. 현재 값은 `workRgnLst` |
| `query` | 사용자가 입력한 조회어 |
| `result_count` | 조회된 후보 수 |
| `matches` | 지역 코드 후보 목록 |
| `matches[].code` | Job-ALIO 지역 코드 |
| `matches[].name` | 지역명 |
| `matches[].aliases` | 지역 별칭 목록 |

## 데이터 소스

- Job-ALIO 채용정보 검색 페이지의 `workRgnLst` option 값

## 처리 원칙

- `query`가 없으면 전체 지역 코드 목록을 반환한다.
- `서울`, `서울시`, `서울특별시`, `R3010`처럼 이름, 별칭, 코드 조회를 지원한다.
- 부분 검색 결과가 여러 개면 후보 목록을 반환한다.
