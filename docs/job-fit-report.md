# Job Fit 준비 리포트 설계

조사일: 2026-07-07 KST

## 목적

`analyze_job_fit_report`는 공고, NCS, 기관 사업 방향, 개선 과제를 연결하는 최종 출력이다.
다만 수집기와 공통 스키마가 아직 PR 단위로 분리되어 있으므로, 현재 구현은 근거가 있는
준비 항목만 생성하고 부족한 입력은 `verification_notes`에 남기는 얇은 리포트 helper로 둔다.

## 입력

| 입력 | 의미 |
| --- | --- |
| `JobAlioDetail` | 잡알리오 상세, NCS 코드/표시명, 공고 본문 필드, 첨부파일 |
| `ApplicantReadinessInput` | 지원자의 목표 직무, 이미 알고 있는 기술 |
| `JobFitInstitutionSignal` | 기관 분석 입력에서 넘어오는 사업 방향/개선 과제 후보 |

## 출력

`JobFitPreparationReport`는 다음을 담는다.

| 필드 | 의미 |
| --- | --- |
| `preparation_items` | 우선 준비 항목 |
| `knowledge_gaps` | 보완할 직무 지식 후보 |
| `institution_materials_to_check` | 추가로 확인할 기관 자료 |
| `evidence_links` | 보고서에 연결된 원문 근거 |
| `verification_notes` | 근거 부족, 원문 확인 필요 사항 |

## 준비 항목 생성 기준

| 조건 | 출력 |
| --- | --- |
| 직무기술서 첨부 후보 있음 | `P0` 직무기술서 요구역량 확정 |
| NCS 코드/표시명 있음 | `P0` NCS 분류와 공고 요구사항 연결 |
| 지원자격/우대사항/전형절차 있음 | `P1` 대응 사례 준비 |
| 기관 signal 있음 | `P1` 기관 사업 방향과 직무 연결 |
| 기관 원문 URL 있음 | `P2` 기관 원문 공고 최종 대조 |

입력이 없으면 항목을 억지로 만들지 않고 `verification_notes`에 남긴다.

## 근거 원칙

모든 항목은 `JobFitEvidenceSource`를 가진다. 근거 종류는 다음으로 제한한다.

- `job_posting`
- `duty_description`
- `ncs`
- `institution_signal`
- `manual`

근거가 없는 기관 signal은 최종 주장으로 쓰지 않는다. 현재 helper는 해당 signal을
`verification_notes`에 표시하고, 원문 URL과 excerpt 확인을 요구한다.

## 지식 보완 후보

`knowledge_gaps`는 지원자의 `known_skills`와 NCS 표시명을 단순 비교해 만든다. 이는 확정 판단이
아니므로 각 항목에 검증 노트를 붙인다. 직무기술서의 K/S/A 텍스트 추출이 붙으면 이 비교는
더 세밀한 기준으로 바꾼다.

## 구현 메모

`generate_job_fit_report(...)`는 샘플 입력에서 바로 준비 리포트를 생성한다. 이후 #4의
NCS 매핑 입력과 #5의 기관 분석 입력이 머지되면, 이 helper의 입력을 `NcsMappingInput`과
`InstitutionAnalysisInput`으로 넓히면 된다.
