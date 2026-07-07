# 03. fetch_job_detail

## 구현 상태

Job-ALIO `recrutPblntSn` 기반 1차 구현 완료. `search_public_jobs`가 반환한 `id` 또는
`source_job_id`를 입력으로 사용한다.

## 입력

| field | 한국어 설명 |
| --- | --- |
| `job_id` | Job-ALIO 공고 ID |
| `source_job_id` | `search_public_jobs`가 반환한 Job-ALIO 원본 공고 ID alias |
| `recruitment_notice_sn` | Job-ALIO 채용공고 일련번호 alias |

## 출력

| field | 한국어 설명 |
| --- | --- |
| `source` | 데이터 출처. 현재 값은 `job_alio` |
| `query` | 호출 입력 요약 |
| `job` | 공고 상세 객체 |
| `job.id` | 내부 공고 ID |
| `job.source` | 공고 출처. 현재 값은 `job_alio` |
| `job.source_job_id` | Job-ALIO 원본 공고 ID |
| `job.institution_name` | 기관명 |
| `job.institution_code` | 기관 코드 |
| `job.title` | 공고명 |
| `job.start_date` | 공고 시작일 |
| `job.end_date` | 공고 마감일 |
| `job.is_ongoing` | 진행 여부 |
| `job.employment_types` | 고용 유형 목록 |
| `job.recruitment_type` | 채용 구분 |
| `job.headcount` | 채용 인원 |
| `job.work_regions` | 근무 지역 목록 |
| `job.source_url` | 원문 링크 |
| `job.ncs_mappings` | NCS 코드/표시명 매핑 후보 목록 |
| `job.qualification` | 지원자격 |
| `job.preferred_conditions` | 우대조건 |
| `job.preference` | 가점/우대사항 |
| `job.disqualification_reason` | 결격사유 |
| `job.screening_procedure` | 전형 절차 |
| `job.replacement_recruitment` | 대체인력 채용 여부 |
| `job.attachments` | 첨부파일 metadata 목록 |
| `job.attachments[].duty_description_candidate` | 직무기술서 첨부 후보 여부 |
| `job.steps` | 전형 단계 metadata 목록 |
| `warnings` | 호출 경고 목록 |

## 데이터 소스

- 잡알리오 상세 Ajax 응답

## 처리 원칙

- `job_id`, `source_job_id`, `recruitment_notice_sn`은 같은 Job-ALIO 공고 ID alias로 본다.
- 여러 ID alias가 들어오면 모두 같은 값이어야 한다.
- 첨부파일의 `file_type == "C"`이거나 파일명에 `직무기술서`, `직무설명`, `NCS`가 있으면
  직무기술서 후보로 표시한다.
- 첨부파일 본문 추출은 하지 않는다. PDF/HWP/HWPX/ZIP 텍스트 추출기는 별도 단계다.
