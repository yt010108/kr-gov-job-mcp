# lookup_job_alio_codes

## 구현 상태

MCP tool 구현됨. Job-ALIO 검색 필터에 사용할 NCS 코드 후보와 기관명 후보를 조회한다.
NCS는 JOB-ALIO 화면에 노출된 25개 표준직무 코드를 제공한다.
기관명은 패키지에 포함된 `alio_institution_codes.csv`의 기관코드를 우선 사용하고,
CSV에 없는 ALIO 채용정보 필터 표시명은 `code`가 `null`인 fallback 후보로 제공한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `code_type` | 조회할 코드 유형. 현재 `institution`, `ncs` 지원 |
| `query` | 기관명, 기관 약칭, NCS명, 직무 키워드 또는 코드 |
| `limit` | 반환할 최대 후보 수. 기본 20, 최대 50 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 현재 값은 `job_alio` |
| `code_type` | 조회한 코드 유형 |
| `query` | 정규화 전 입력 query |
| `result_count` | 반환된 후보 수 |
| `codes[].code` | Job-ALIO 검색 필터에 넣을 코드. 기관명 표시명 후보는 `null`일 수 있음 |
| `codes[].name` | 코드 표시명 |
| `codes[].aliases` | 자연어 alias 후보 |
| `codes[].score` | 간단한 매칭 점수 |
| `codes[].source` | 후보 출처 |
| `codes[].fallback_search` | 기관코드가 없는 기관명 후보에서 사용할 `search_public_jobs` keyword 검색 인자 |
| `warnings` | 0건 또는 제한 사항 |

## 처리 원칙

- 이 도구는 코드 후보 조회만 담당한다.
- `search_public_jobs` 내부에서 자동 resolver를 실행하지 않는다.
- 후보가 여러 개면 LLM이나 사용자가 확인한 뒤 `search_public_jobs`에 코드를 전달한다.
- 기관명 후보 중 `code`가 `null`인 항목은 `search_public_jobs.institution_code`로 바로 전달하지 않는다.
- 기관명 후보 중 `code`가 `null`인 항목은 `fallback_search.arguments.keyword`의 기관명으로
  `search_public_jobs` 검색을 이어간다.
- 코드 테이블과 필터 표시명 목록에 없는 후보는 빈 결과와 warning으로 안전하게 반환한다.
