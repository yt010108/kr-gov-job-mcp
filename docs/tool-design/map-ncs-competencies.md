# 04. map_ncs_competencies

## 구현 상태

MCP tool은 아직 미구현. 현재는 `NcsMappingInput` schema와 `prepare_ncs_mapping_input(...)`
helper 기준으로 입력 구조만 잡혀 있다.

## 입력

planned schema:

| field | 한국어 설명 |
| --- | --- |
| `job_detail` | `fetch_job_detail`이 반환한 공고 상세 구조화 결과 |
| `duty_description_text` | 직무기술서에서 추출한 텍스트 |

## 출력

planned schema:

| field | 한국어 설명 |
| --- | --- |
| `basic_competencies` | 직업기초능력 후보 |
| `duty_competencies` | 직무수행능력 후보 |
| `knowledge` | 필요지식 후보 |
| `skills` | 필요기술 후보 |
| `attitudes` | 직무수행태도 후보 |
| `evidence` | 역량 추출 근거 목록 |
| `verification_notes` | 근거 부족 또는 확인 필요 사항 |

## 데이터 소스

- Job-ALIO 상세 필드
- Job-ALIO NCS 코드/표시명
- 직무기술서 첨부파일 텍스트

## 처리 원칙

- Job-ALIO의 `ncsCdLst`와 `ncsCdNmLst`는 index 기준으로 매핑한다.
- 직무기술서 본문에서 명시 라벨이 있을 때만 K/S/A 후보를 만든다.
- 근거가 없으면 역량을 추정하지 않고 검증 노트로 남긴다.
