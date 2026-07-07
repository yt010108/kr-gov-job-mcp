# analyze_institution_weakness

## 구현 상태

MVP MCP tool 구현됨. 현재는 입력으로 받은 개선 과제 evidence와 signal 후보만 사용한다.
ALIO/Cleaneye 자동 수집은 아직 별도 단계다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `institution_name` | 분석 대상 기관명 |
| `year` | 분석 기준 연도 |
| `evidence` | ALIO, Cleaneye, 수동 입력에서 온 개선 과제 근거 후보 목록 |
| `signals` | 사전에 추출된 개선 과제 signal 후보 목록 |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 분석 출처. 현재 값은 `institution_analysis` |
| `query` | 호출 입력 요약 |
| `institution_name` | 기관명 |
| `normalized_name` | 공백과 괄호만 정리한 기관명 |
| `year` | 분석 기준 연도 |
| `weakness_signals` | evidence 기반 개선 과제 signal 목록 |
| `weakness_signals[].category` | signal 분류. 예: `improvement_task`, `financial_or_operational`, `management_evaluation` |
| `weakness_signals[].summary` | 개선 과제 요약 |
| `weakness_signals[].careful_wording` | 단정적 비판을 피하기 위한 표현 기준 |
| `weakness_signals[].applicant_connection` | 지원자가 기여할 수 있는 포인트 |
| `weakness_signals[].evidence` | 원문 근거 목록 |
| `verification_notes` | 근거 부족 또는 확인 필요 사항 |
| `warnings` | 호출 경고 목록 |

## 데이터 소스

- ALIO 국회 지적사항
- ALIO 감사/평가 후보 항목
- Cleaneye 경영평가, 부채, 외부기관 감사결과
- 현재 tool은 위 자료를 직접 수집하지 않고, 입력으로 전달된 `evidence`와 `signals`만 사용한다.

## 처리 원칙

- 국회 지적사항, 감사결과, 경영평가성 자료는 원문 근거 링크와 함께만 사용한다.
- 개선 과제는 지원자가 자기소개서나 면접에서 활용 가능한 표현으로 바꾸되, 원문 의미를 과장하지 않는다.
- 현재 ALIO `47-2`, `47-3`은 수집 범위에서 제외되어 있으므로 근거로 쓰지 않는다.
