# 01b. lookup_institution_codes

## 구현 상태

Job-ALIO 채용정보 검색 페이지의 `pblntInstCd` option 값 중 MVP 테스트와 데모에 필요한
기관을 seed table로 1차 구현했다. 전체 기관 코드 자동 수집은 후속 확장 대상으로 둔다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `query` | 자연어 기관명, 약칭, 또는 Job-ALIO 기관 코드. 비우면 seed 기관 코드 목록 조회 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 데이터 출처. 현재 값은 `job_alio` |
| `code_type` | 코드 유형. 현재 값은 `pblntInstCd` |
| `query` | 사용자가 입력한 조회어 |
| `result_count` | 조회된 후보 수 |
| `matches` | 기관 코드 후보 목록 |
| `matches[].code` | Job-ALIO 기관 코드 |
| `matches[].name` | 기관 공식명 |
| `matches[].aliases` | 기관 별칭 목록 |
| `matches[].confidence` | 조회어와 후보의 일치 신뢰도. `high` 또는 `medium` |

## 데이터 소스

- Job-ALIO 채용정보 검색 페이지의 `pblntInstCd` option 값
- 현재 seed: 한국농수산식품유통공사, 전남대학교병원, 한국인터넷진흥원, 창업진흥원

## 처리 원칙

- `query`가 없으면 seed 기관 코드 목록을 반환한다.
- 이름, 공백 제거 이름, 별칭, 코드 조회를 지원한다.
- `search_public_jobs.institution_name`은 같은 resolver를 사용해 `institution_code`로 변환한다.
- 못 찾은 기관명은 경고와 함께 제목 keyword fallback으로 검색한다.
