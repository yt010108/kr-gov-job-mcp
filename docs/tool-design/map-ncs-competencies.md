# map_ncs_competencies

## 구현 상태

MCP tool은 아직 미구현. 현재는 `NcsMappingInput` schema와 `prepare_ncs_mapping_input(...)`
helper 기준으로 입력 구조만 잡혀 있다.

## 입력

- `job_detail`
- `duty_description_text`

## 출력

- 직업기초능력
- 직무수행능력
- Knowledge
- Skill
- Attitude
- 역량 근거
- 검증 포인트

## 데이터 소스

- Job-ALIO 상세 필드
- Job-ALIO NCS 코드/표시명
- 직무기술서 첨부파일 텍스트

## 처리 원칙

- Job-ALIO의 `ncsCdLst`와 `ncsCdNmLst`는 index 기준으로 매핑한다.
- 직무기술서 본문에서 명시 라벨이 있을 때만 K/S/A 후보를 만든다.
- 근거가 없으면 역량을 추정하지 않고 검증 노트로 남긴다.

