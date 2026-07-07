# analyze_institution_strategy

## 구현 상태

MCP tool은 아직 미구현. 현재는 `InstitutionAnalysisInput` schema와 기관 evidence/signal
후보 구조만 잡혀 있다.

## 입력

- `institution_name`
- `year`
- `job_family`

## 출력

- 주요사업
- 성장 사업
- 디지털/보안/데이터 포인트
- 기관 이해 근거
- 사업 이해

## 데이터 소스

- ALIO 주요사업
- 기관 홈페이지
- 필요 시 Cleaneye 사업보고서 또는 신규투자사업

## 처리 원칙

- evidence가 없는 사업 방향은 최종 주장으로 쓰지 않는다.
- ALIO와 Cleaneye 기관 ID를 기관명만으로 강제 병합하지 않는다.
- 기관 홈페이지는 구조가 기관마다 다르므로 출처 URL과 excerpt를 함께 보존한다.

