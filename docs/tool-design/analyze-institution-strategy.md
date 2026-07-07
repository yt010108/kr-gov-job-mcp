# analyze_institution_strategy

## 구현 상태

MCP tool 구현됨. 입력으로 받은 기관 evidence와 signal 후보를 사용해 사업 방향 taxonomy,
우선순위, 신뢰도, 직무 연결 포인트를 생성한다. ALIO, Cleaneye, 기관 홈페이지 자동 수집은
별도 단계다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `institution_name` | 분석 대상 기관명 |
| `year` | 분석 기준 연도 |
| `job_family` | 직무군. 예: 정보보호, 전산, 사업관리 |
| `evidence` | ALIO, Cleaneye, 기관 홈페이지, 수동 입력에서 온 기관 근거 후보 목록 |
| `signals` | 사전에 추출된 기관 signal 후보 목록 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 분석 출처. 현재 값은 `institution_analysis` |
| `query` | 호출 입력 요약 |
| `institution_name` | 기관명 |
| `normalized_name` | 공백과 괄호만 정리한 기관명 |
| `year` | 분석 기준 연도 |
| `job_family` | 직무군 |
| `strategy_signals` | evidence 기반 기관 사업 방향 signal 목록 |
| `strategy_signals[].category` | signal 분류. 예: `business_direction`, `job_connection` |
| `strategy_signals[].summary` | 사업 방향 요약 |
| `strategy_signals[].strategy_type` | 사업 방향 taxonomy. 예: `디지털 전환`, `정보보호/안전/규제 대응` |
| `strategy_signals[].priority` | 응답 내 우선순위. 1이 가장 높음 |
| `strategy_signals[].confidence` | 근거 출처, 구체성, 직무 키워드 매칭을 반영한 `low`, `medium`, `high` |
| `strategy_signals[].source_reason` | 해당 근거를 왜 반영했는지 설명 |
| `strategy_signals[].job_connection` | 직무 연결 포인트 |
| `strategy_signals[].job_relevance` | 직무군별 연결 근거 |
| `strategy_signals[].interview_talking_point` | 면접에서 안전하게 말할 수 있는 포인트 |
| `strategy_signals[].resume_angle` | 자기소개서에 연결할 수 있는 방향 |
| `strategy_signals[].keywords` | taxonomy와 직무 연결에 사용된 키워드 |
| `strategy_signals[].needs_verification` | 출처/최신성/직무 연결 확인이 더 필요한지 여부 |
| `strategy_signals[].evidence` | 원문 근거 목록 |
| `verification_notes` | 근거 부족 또는 확인 필요 사항 |
| `warnings` | 호출 경고 목록 |

## 데이터 소스

- ALIO 주요사업
- 기관 홈페이지
- 필요 시 Cleaneye 사업보고서 또는 신규투자사업
- 현재 tool은 위 자료를 직접 수집하지 않고, 입력으로 전달된 `evidence`와 `signals`만 사용한다.

## 처리 원칙

- evidence가 없는 사업 방향은 최종 주장으로 쓰지 않는다.
- ALIO와 Cleaneye 기관 ID를 기관명만으로 강제 병합하지 않는다.
- 기관 홈페이지는 구조가 기관마다 다르므로 출처 URL과 excerpt를 함께 보존한다.
- 사업 방향은 다음 taxonomy 후보 중 evidence 키워드와 가장 잘 맞는 유형으로 분류한다.
  `핵심사업 유지/확대`, `디지털 전환`, `정보보호/안전/규제 대응`, `지역/산업 지원`,
  `대국민 서비스 개선`, `정책 집행/공공성 강화`, `연구개발/기술 고도화`,
  `ESG/상생/사회적 가치`.
- 우선순위와 신뢰도는 출처 유형, 기준 연도 또는 수집 시점, excerpt 구체성, 직무군 키워드
  매칭을 함께 본다.
- `정보보호`, `전산`, `사업관리` 직무군은 서로 다른 연결 문장을 생성한다.
