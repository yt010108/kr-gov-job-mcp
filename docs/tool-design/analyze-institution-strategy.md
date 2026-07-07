# analyze_institution_strategy

## 구현 상태

MVP MCP tool 구현됨. 현재는 입력으로 받은 기관 evidence와 signal 후보만 사용한다. ALIO,
Cleaneye, 기관 홈페이지 자동 수집은 아직 별도 단계다.

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
| `strategy_signals[].job_connection` | 직무 연결 포인트 |
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
