# analyze_institution_weakness

## 구현 상태

MCP tool은 아직 미구현. ALIO/Cleaneye raw 수집과 `InstitutionSignalCandidate` 구조를
먼저 활용한다.

## 입력

- `institution_name`
- `year`

## 출력

- 개선 과제
- 운영/사업 약점
- 조심할 표현
- 지원자가 기여할 수 있는 개선 아이디어

## 데이터 소스

- ALIO 국회 지적사항
- ALIO 감사/평가 후보 항목
- Cleaneye 경영평가, 부채, 외부기관 감사결과

## 처리 원칙

- 국회 지적사항, 감사결과, 경영평가성 자료는 원문 근거 링크와 함께만 사용한다.
- 개선 과제는 지원자가 자기소개서나 면접에서 활용 가능한 표현으로 바꾸되, 원문 의미를 과장하지 않는다.
- 현재 ALIO `47-2`, `47-3`은 수집 범위에서 제외되어 있으므로 근거로 쓰지 않는다.

