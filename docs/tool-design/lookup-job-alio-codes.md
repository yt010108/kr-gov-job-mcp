# lookup_job_alio_codes

## 구현 상태

MCP tool 구현됨. Job-ALIO 검색 필터에 사용할 기관 코드와 NCS 코드 후보를 조회한다.
현재는 자주 쓰는 기관/NCS 후보를 작은 seed table로 제공하며, 자동 갱신은 후속 범위다.

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
| `codes[].code` | Job-ALIO 검색 필터에 넣을 코드 |
| `codes[].name` | 코드 표시명 |
| `codes[].aliases` | 자연어 alias 후보 |
| `codes[].score` | 간단한 매칭 점수 |
| `codes[].source` | 후보 출처 |
| `warnings` | 0건 또는 제한 사항 |

## 처리 원칙

- 이 도구는 코드 후보 조회만 담당한다.
- `search_public_jobs` 내부에서 자동 resolver를 실행하지 않는다.
- 후보가 여러 개면 LLM이나 사용자가 확인한 뒤 `search_public_jobs`에 코드를 전달한다.
- seed table에 없는 후보는 빈 결과와 warning으로 안전하게 반환한다.
