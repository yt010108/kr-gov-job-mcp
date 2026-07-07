# analyze_public_job_query

## 구현 상태

MCP tool 구현됨. 사용자의 자연어 채용 질문을 받아 공고 검색, 상세 조회, 준비 리포트 생성을
한 응답으로 묶는다. 현재는 기존 `search_public_jobs`, `fetch_job_detail`,
`analyze_job_fit_report` 흐름을 조합한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `query` | 사용자의 자연어 질문 원문 |
| `institution_name` | 질문에서 분리된 기관명. 명시하면 query 추정보다 우선 |
| `keyword` | 직무, 공고, NCS 관련 검색 키워드 |
| `region` | 자연어 근무지역명 |
| `ongoing_only` | 진행 중 공고만 우선 조회할지 여부 |
| `analysis_depth` | `search_only`, `detail`, `fit_report` |
| `target_role` | 준비 리포트에서 사용할 목표 직무 |
| `known_skills` | 지원자가 이미 보유한 기술, 자격증, 경험 |
| `limit` | 선택할 공고 수. 기본 3, 최대 5 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 현재 값은 `public_job_query_orchestration` |
| `interpreted_query` | 자연어 질문에서 해석한 기관명, 키워드, 진행 여부, 분석 깊이 |
| `search_attempts` | 검색 시도별 이유, 인자, 결과 수 |
| `selected_jobs` | 선택된 공고 요약 |
| `job_details` | `detail` 이상에서 자동 조회한 상세 공고 |
| `fit_reports` | `fit_report`에서 생성한 준비 리포트 |
| `institution_analysis_status` | 기관 분석을 위해 추가 evidence가 필요한지 여부 |
| `no_result_diagnostics` | 결과가 없을 때 가능한 원인과 재검색 제안 |
| `next_actions` | 다음에 호출하거나 확인할 액션 |
| `warnings` | 검색 실패나 제한 사항 |

## 처리 원칙

- 하위 기능을 중복 구현하지 않고 기존 도구 흐름을 조합한다.
- 기관명이나 직무 키워드가 명시되면 query 추정보다 우선한다.
- 결과가 없으면 진행 중 제한 해제, 기관명 alias, institution code, NCS/상세 필드 검색 같은
  다음 액션을 반환한다.
- 기관 사업 방향이나 개선 과제 분석은 원문 evidence가 필요하므로 이 도구 안에서 근거 없이
  단정하지 않는다.
