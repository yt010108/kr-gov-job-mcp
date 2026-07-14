# resolve_ncs_code

## 구현 상태

MCP tool 구현됨. 자연어 직무명, NCS명, 약칭, 별칭을 Job-ALIO NCS 대분류 후보와 검색 코드로 해석한다.
후보 테이블은 `lookup_job_alio_codes(code_type="ncs")`와 같은 `NCS_CODES`를 사용한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `query` | 자연어 직무명, NCS명, 약칭 또는 별칭 |
| `target_role` | 면접 또는 준비 리포트에서 사용한 원문 목표 직무명 |
| `job_family` | 기관 분석 또는 준비 리포트에서 사용한 원문 직무군 |
| `known_skills` | 명시적 직무명이 없을 때 보조적으로 해석할 보유 기술 또는 경험 목록 |
| `preparation_notes` | 직무 단서가 포함될 수 있는 지원자 메모 |
| `limit` | 반환할 최대 후보 수. 기본 5, 최대 25 |

`query`, `target_role`, `job_family`, `known_skills`, `preparation_notes` 중 하나는 필요하다.
명시적 직무 입력이 있으면 보조 입력보다 우선한다.

## 출력

| field | 한국어 설명 |
| --- | --- |
| `original_query` | 호출자가 전달한 원문 query |
| `original_target_role` | 호출자가 전달한 원문 목표 직무 |
| `original_job_family` | 호출자가 전달한 원문 직무군 |
| `resolved_query` | 실제 후보 조회에 사용한 텍스트 |
| `candidates` | 점수와 일치 alias를 포함한 NCS 후보 목록 |
| `selected_ncs_code` | 확정된 Job-ALIO NCS 코드. 확정하지 않으면 `null` |
| `selected_ncs_name` | 확정된 Job-ALIO NCS 표시명. 확정하지 않으면 `null` |
| `search_public_jobs_arguments` | 확정된 경우 다음 검색에 바로 전달할 `ncs_code` |
| `report_context` | 면접·기관 분석 호출에 전달할 원문 직무, NCS명, NCS 코드 맥락 |
| `recommended_next_calls` | 모호하거나 0건일 때 후보 확인을 위한 다음 호출 |
| `warnings` | 확정하지 않은 이유 또는 0건 안내 |

## 처리 원칙

- 확정된 `selected_ncs_code`만 `search_public_jobs.ncs_code`에 전달한다.
- `target_role`, `job_family`는 면접·기관 분석의 표현 관점이며 채용 검색 필터가 아니다.
- 원문 직무명과 직무군은 각각 `report_context.original_target_role`,
  `report_context.original_job_family`에 보존한다.
- 여러 후보가 같은 수준으로 일치하면 하나를 임의로 고르지 않고 `selected_ncs_code`를 비워 둔다.
- 후보가 없으면 검색 필터도 비워 두고 `warnings`, `recommended_next_calls`로 다음 확인을 안내한다.

## 호출 흐름

```text
resolve_ncs_code(query="전산직")
  -> selected_ncs_code="R600020"

search_public_jobs(ncs_code="R600020")
```

면접 또는 기관 분석에는 `report_context`의 `target_role`, `job_family`, `original_target_role`,
`ncs_code`를 함께 전달할 수 있다. 이 도구들은 NCS 코드로 공고를 검색하지 않는다.
