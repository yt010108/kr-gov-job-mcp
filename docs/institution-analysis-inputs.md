# 기관 분석 입력 데이터 설계

조사일: 2026-07-07 KST

## 목적

기관 사업 방향과 개선 과제 분석은 여러 출처를 섞어야 한다. 이 단계에서는 최종 기관 분석
결과를 만들지 않고, ALIO, Cleaneye, 기관 홈페이지에서 얻은 원문
근거를 `InstitutionAnalysisInput`으로 모은다. 근거가 부족한 후보는 분석 결과로 확정하지
않고 `verification_notes`에 남긴다.

## 출처별 입력 후보

| 출처 | 기관 식별자 | 사업 방향 후보 | 개선 과제 후보 | 주의점 |
| --- | --- | --- | --- | --- |
| ALIO 경영공시 | `apbaId`, 기관명 | 주요사업, 일반현황, 사업 내용 | 국회 지적사항, 감사/평가 관련 항목 | 중앙 공공기관 대상 |
| Cleaneye 지방공기업 | `entId` | 일반현황, 사업보고서, 신규투자사업 | 경영평가등급, 부채규모, 외부기관 감사결과 | 지방공기업 |
| Cleaneye 출자출연 | `insttCode` | 일반현황, 경영성과, 재무현황 | 재무·부채관리 계획, 외부기관 감사결과 | 지방출자·출연기관 |
| 기관 홈페이지 | URL, 기관명 | 기관 소개, 사업 소개, ESG/경영 자료 | 감사/윤리/고객만족 자료 | 구조가 기관마다 다름 |

## 기관명/기관코드 정규화

기관명은 공사/공단/병원 같은 법적 성격을 담는 접미사를 임의로 제거하지 않는다. 기본
정규화는 공백 정리와 괄호 주변 공백 정리에 한정한다.

식별 우선순위:

1. 출처별 고유 코드: ALIO `apbaId`, Cleaneye `entId`, Cleaneye `insttCode`
2. 기관 공식 홈페이지 URL
3. 원문에 표시된 기관명
4. 별칭: 영문 약칭, 채용공고 표기, 구 기관명

ALIO와 Cleaneye는 대상 기관군이 다르므로 같은 필드에 억지로 합치지 않는다. 입력 구조에서는
`alio_id`, `cleaneye_id`, `cleaneye_kind`를 따로 보존한다.

## InstitutionAnalysisInput 구조

| 필드 | 의미 |
| --- | --- |
| `institution_name` | 사용자가 요청하거나 수집에서 선택한 기관명 |
| `normalized_name` | 공백만 정리한 기관명 |
| `aliases` | KISA 같은 약칭, 표기 차이 |
| `alio_id` | ALIO 기관 코드 |
| `cleaneye_id` | Cleaneye `entId` 또는 `insttCode` |
| `cleaneye_kind` | `local_public_enterprise` 또는 `local_invested_contributed` |
| `identity_candidates` | 출처별 기관 식별 후보 |
| `evidence` | 원문 URL, excerpt, source fields |
| `signals` | 사업 방향/개선 과제/직무 연결 후보 |
| `verification_notes` | 코드 미확인, 근거 부족, 후보 검증 필요 사항 |

## Signal 후보 분류

| category | 용도 |
| --- | --- |
| `business_direction` | 주요사업, 성장 사업, 기관 홈페이지 기반 방향 |
| `improvement_task` | 국회 지적사항, 감사결과, 설명자료 기반 개선 과제 |
| `job_connection` | 채용공고/직무기술서와 기관 사업의 연결점 |
| `financial_or_operational` | 부채, 재무, 운영 현황 후보 |
| `management_evaluation` | 경영평가, 고객만족, ESG 등 평가성 자료 |

Signal은 반드시 `InstitutionEvidence`와 연결하는 것을 원칙으로 한다. evidence가 없는 signal은
`verification_notes`에 남긴다.

## 근거 연결 방식

`InstitutionEvidence`는 다음 정보를 담는다.

| 필드 | 예시 |
| --- | --- |
| `title` | `ALIO 주요사업`, `기관 홈페이지 사업 소개` |
| `source_type` | `alio_disclosure`, `cleaneye`, `institution_homepage` |
| `url` | 원문 URL |
| `source_id` | `apbaId`, `entId`, 기관 페이지 식별자 등 |
| `excerpt` | 분석 후보를 만든 원문 일부 |
| `fields` | 원본 itemNo, itemId, page_type 등 |

최종 분석 도구는 이 evidence를 바탕으로 기관 사업 방향과 개선 과제를 요약한다. evidence가
없는 내용은 분석 결과에 넣지 않거나, 낮은 신뢰도와 검증 노트를 함께 둔다.

## 구현 메모

`prepare_institution_analysis_input(...)`은 기관명, 출처별 코드, evidence, signal 후보를 받아
`InstitutionAnalysisInput`을 만든다. 지금은 보수적으로 누락 검증만 수행한다. ALIO/Cleaneye/
기관 홈페이지 collector 결과를 evidence와 signal 후보로 변환하는 adapter를 추가한다.
