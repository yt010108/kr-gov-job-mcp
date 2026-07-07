# 03. fetch_job_detail

## 구현 상태

Job-ALIO `recrutPblntSn` 기반 1차 구현 완료. `search_public_jobs`가 반환한 `id` 또는
`source_job_id`를 입력으로 사용한다.

## 입력

- `job_id`
- `source_job_id`
- `recruitment_notice_sn`

## 출력

- 공고 기본 정보
- 지원자격
- 우대사항
- 가점/우대사항
- 결격사유
- 전형 절차
- 첨부파일 metadata
- 직무기술서 첨부 후보 여부
- 전형 단계 metadata
- NCS 코드/표시명 매핑 후보

## 데이터 소스

- 잡알리오 상세 Ajax 응답

## 처리 원칙

- `job_id`, `source_job_id`, `recruitment_notice_sn`은 같은 Job-ALIO 공고 ID alias로 본다.
- 여러 ID alias가 들어오면 모두 같은 값이어야 한다.
- 첨부파일의 `file_type == "C"`이거나 파일명에 `직무기술서`, `직무설명`, `NCS`가 있으면
  직무기술서 후보로 표시한다.
- 첨부파일 본문 추출은 하지 않는다. PDF/HWP/HWPX/ZIP 텍스트 추출기는 별도 단계다.
