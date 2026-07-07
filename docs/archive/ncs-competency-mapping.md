# NCS/KSA 매핑 입력 설계

조사일: 2026-07-07 KST

## 목적

NCS/KSA 매핑은 공고와 직무기술서 원문 근거가 있어야 한다. 현재 단계에서는 최종 역량
판단을 생성하지 않고, 잡알리오와 첨부파일 수집 결과에서 확인 가능한 입력값을 분리한다.
근거가 없는 추정은 `verification_notes`로 남겨 이후 PDF/HWP/HWPX 텍스트 추출이나 수동
검토에서 확인한다.

## 확인한 잡알리오 입력 필드

샘플 검색어 `정보` 기준, 잡알리오 상세에서 다음 필드를 확인했다.

| 입력 후보 | 잡알리오 필드/스키마 | 관찰 |
| --- | --- | --- |
| NCS 코드 | `ncsCdLst`, `JobAlioDetail.ncs_codes` | 예: `R600006`, `R600002`, `R600025` |
| NCS 표시명 | `ncsCdNmLst`, `JobAlioDetail.ncs_categories` | 예: `보건.의료`, `경영.회계.사무`, `연구` |
| 지원자격 | `aplyQlfcCn`, `qualification` | 원문 근거로 보존 가능 |
| 우대조건 | `prefCondCn`, `preferred_conditions` | 원문 근거로 보존 가능 |
| 가점/우대사항 | `prefCn`, `preference` | 공고별 존재 여부 다름 |
| 결격사유 | `disqlfcRsn`, `disqualification_reason` | 직접 KSA보다는 검증 근거 |
| 전형절차 | `scrnprcdrMthdExpln`, `screening_procedure` | 평가 단계 연결 후보 |
| 첨부파일 | `files`, `attachments` | `file_type=C` 또는 파일명 `직무기술서`가 직무기술서 후보 |

샘플에서는 직무기술서가 PDF/HWP/ZIP으로 내려오는 경우가 섞여 있었다. 따라서 KSA 추출은
첨부 텍스트 추출기가 붙기 전까지 확정하지 않는다.

## 매핑 입력 구조

`NcsMappingInput`은 다음 데이터를 담는다.

| 필드 | 의미 |
| --- | --- |
| `job_id` | 잡알리오 공고 ID |
| `institution_name` | 기관명 |
| `title` | 공고 제목 |
| `source_url` | 기관 원문 URL |
| `ncs_codes` | 코드와 표시명 매핑, 원본 필드 근거 |
| `duty_description_attachments` | 직무기술서 첨부 후보 |
| `source_fields` | 지원자격, 우대조건, 전형절차 등 원문 필드 |
| `ksa_candidates` | 명시 라벨에서만 추출한 K/S/A 후보 |
| `verification_notes` | 원문 근거 부족, 코드/표시명 불일치, 텍스트 추출 필요 사항 |

이 구조는 #2의 `NcsKsaMapping` 최종 결과를 만들기 전 단계다. `NcsMappingInput`은 collector
출력과 분석 스키마 사이의 검증 대기열 역할을 한다.

## NCS 코드 매핑 기준

1. `ncs_codes`와 `ncs_categories`는 같은 index끼리 묶는다.
2. 길이가 다르면 누락된 표시명을 `None`으로 두고 `verification_notes`에 기록한다.
3. 코드 자체와 표시명은 잡알리오 원문 필드 근거가 있으므로 임의 보정하지 않는다.

## 직무기술서 후보 기준

첨부파일은 다음 조건 중 하나면 직무기술서 후보로 본다.

- `file_type == "C"`
- 파일명에 `직무기술서`, `직무설명`, `NCS`가 포함된다.

후보 첨부는 URL과 파일명을 보존한다. PDF/HWP/HWPX/ZIP 텍스트 추출은 별도 단계로 둔다.

## K/S/A 후보 추출 기준

직무기술서 텍스트가 있을 때만 다음 명시 라벨을 찾는다.

| 분류 | 라벨 후보 |
| --- | --- |
| Knowledge | `필요지식`, `지식`, `knowledge` |
| Skill | `필요기술`, `기술`, `skill` |
| Attitude | `직무수행태도`, `태도`, `attitude` |
| 직업기초능력 | `직업기초능력`, `기초능력`, `basic competency` |
| 직무수행능력 | `직무수행능력`, `직무능력`, `duty competency` |

명시 라벨이 없으면 후보를 만들지 않고 `verification_notes`에 남긴다. 공고 제목이나 기관명만
보고 역량을 추정하지 않는다.

## Evidence 연결

모든 후보는 `NcsEvidenceReference`를 가진다.

| source_type | 용도 |
| --- | --- |
| `ncs_code` | 잡알리오 NCS 코드/표시명 |
| `job_alio_field` | 지원자격, 우대조건, 전형절차 등 상세 필드 |
| `duty_description_attachment` | 직무기술서 첨부 후보 |
| `duty_description_text` | 텍스트 추출된 직무기술서 라벨/문장 |

최종 `NcsKsaMapping`으로 변환할 때 근거가 없는 항목은 만들지 않거나, 반드시 검증 노트와
함께 낮은 신뢰도로 둔다.

## 구현 메모

`prepare_ncs_mapping_input(detail, duty_description_text=None)`는 `JobAlioDetail`을 받아
`NcsMappingInput`을 만든다. 현재는 명시 라벨 기반의 보수적 추출만 수행한다. 직무기술서
본문 파서가 추가되면 이 함수에 추출 텍스트를 넘겨 K/S/A 후보를 채운다.
