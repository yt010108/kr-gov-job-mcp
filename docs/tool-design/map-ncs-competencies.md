# 05. map_ncs_competencies

## 구현 상태

MCP tool 구현 완료. Job-ALIO 공고 상세를 조회하고 사용자 제공 본문 또는 선택된 PDF
첨부에서 명시적인 NCS/KSA 항목을 추출한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `job_id` | Job-ALIO 공고 ID. 기존 상세 도구의 ID 별칭도 허용한다. |
| `duty_description_text` | 이미 추출한 직무기술서 본문. 첨부 다운로드보다 우선한다. |
| `attachment_url` | 여러 후보 중 명시적으로 선택할 첨부 URL |
| `include_attachment_text` | PDF 첨부 자동 추출 여부. 기본값은 `true` |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `ncs_codes` | Job-ALIO NCS 코드와 표시명 |
| `basic_competencies` | 직업기초능력 후보 |
| `duty_competencies` | 직무수행능력 후보 |
| `knowledge` | 필요지식 후보 |
| `skills` | 필요기술 후보 |
| `attitudes` | 직무수행태도 후보 |
| `attachment_candidates` | 후보, 선택 이유, 추출 상태 |
| `evidence` | 역량 추출 근거 목록 |
| `verification_notes` | 근거 부족 또는 확인 필요 사항 |
| `warnings` | 다운로드·형식·파싱 경고 |

## 데이터 소스

- Job-ALIO 상세 필드
- Job-ALIO NCS 코드/표시명
- 직무기술서 첨부파일 텍스트

## 처리 원칙

- Job-ALIO의 `ncsCdLst`와 `ncsCdNmLst`는 index 기준으로 매핑한다.
- 직무기술서 본문에서 명시 라벨이 있을 때만 K/S/A 후보를 만든다.
- 후보가 여러 개면 임의 선택하지 않고 `attachment_url` 지정을 요청한다.
- PDF 텍스트만 자동 추출한다. HWP/HWPX와 스캔 PDF는 확인 메모를 반환한다.
- 근거가 없으면 역량을 추정하지 않고 검증 노트로 남긴다.
