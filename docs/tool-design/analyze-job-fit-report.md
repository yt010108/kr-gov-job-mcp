# 07. analyze_job_fit_report

## 구현 상태

MCP tool은 아직 미구현. 현재는 `JobFitPreparationReport` schema와
`generate_job_fit_report(...)` helper 기준의 얇은 리포트 생성 단계다.

## 입력

- `job_detail`
- `ncs_profile`
- `institution_strategy`
- `institution_weakness`
- `applicant_profile`

## 출력

- 공고 요구사항과 NCS 역량 연결 결과
- 기관 사업 방향과 직무 연결 결과
- 지원자가 우선 준비해야 할 항목
- 보완해야 할 직무 지식
- 확인해야 할 기관 자료
- 준비 우선순위
- 근거 링크

## 데이터 소스

- `fetch_job_detail` 출력
- `map_ncs_competencies` 출력
- `collect_institution_context` 또는 기관 분석 입력
- 지원자 준비 상태 입력

## 처리 원칙

- 공고, NCS, 기관 signal은 evidence가 연결된 항목만 강한 주장으로 사용한다.
- 부족한 자료는 `verification_notes` 또는 `institution_materials_to_check`로 남긴다.
- 리포트는 지원자가 다음에 확인하거나 준비해야 할 항목을 우선순위로 정리한다.
