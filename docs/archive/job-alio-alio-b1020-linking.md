# Job-ALIO와 ALIO B1020 채용공시 연결 규칙

현재 MVP 범위 밖의 미래 설계 문서입니다. Job-ALIO 검색, 상세 조회, 준비 리포트 흐름이 안정된 뒤 ALIO 채용공시 연결 단계에서 다시 사용합니다.

작성일: 2026-07-07 KST

## 목적

Job-ALIO 채용공고와 ALIO 6-2 직원 채용정보 `B1020`의 중복/보완 관계를 정리한다. 같은 채용공고가
두 출처에 동시에 올라올 수 있으므로, 하나의 canonical `JobPosting`을 만들되 양쪽 원문은
`EvidenceSource`로 남기는 방식을 v0 규칙으로 둔다.

## 기본 원칙

- Job-ALIO는 채용공고의 주 소스다.
- ALIO `B1020`은 기관별 경영공시 관점의 보완 소스다.
- 양쪽 공고를 바로 병합하지 않고 candidate link를 먼저 만든다.
- 자동 확신이 낮으면 `needs_review`로 남기고 사용자가 보는 분석 결과에는 단정 표현을 쓰지 않는다.
- source evidence는 중복으로 보존한다. 중복 제거 대상은 분석용 canonical row뿐이다.

## 소스별 역할

| 구분 | Job-ALIO | ALIO `B1020` |
| --- | --- | --- |
| primary key | `recrutPblntSn` | `idx`, `submissionNo`, `disclosureNo` |
| 기관 식별 | `pblntInstCd`, `pbadmsStdInstCd`, `instNm` | `apbaId`, `apbaNa` |
| 제목 | `recrutPbancTtl` | `title` |
| 공고 기간 | `pbancBgngYmd`, `pbancEndYmd` | HTML `공고기간`, 목록 `openDate`/`idate` |
| NCS | `ncsCdLst`, `ncsCdNmLst` | 없음 |
| 채용 상세 | 자격, 우대, 전형절차, steps | 채용분야, 고용형태, 근무지, 인원, 전형단계별 표 |
| 첨부 | 상세 `files` | 공고문, 입사지원서, 직무기술서, 기타 첨부 |
| 원문 링크 | `srcUrl` | ALIO board URL, 기관 접수 URL |

Job-ALIO에 더 강한 필드:

- NCS 코드와 표시명
- 지원자격, 우대조건, 결격사유 같은 장문 채용 조건
- 채용 단계별 steps metadata
- Job-ALIO 공고 serial number

ALIO `B1020`에 더 강한 필드:

- ALIO 기관 코드 `apbaId`와 경영공시 provenance
- 공고문/입사지원서/직무기술서 첨부 label
- 기관 접수 사이트 URL
- 전형단계별 채용정보 표

## Canonical 모델

v0에서는 `JobPosting`을 canonical row로 둔다.

| 모델 | 역할 |
| --- | --- |
| `JobPosting` | 분석용 대표 채용공고. Job-ALIO 공고가 있으면 이를 우선 사용 |
| `JobPostingSourceLink` | Job-ALIO와 ALIO B1020 evidence를 canonical row에 연결 |
| `EvidenceSource` | 각 출처 원문 URL, raw sample id, excerpt 보존 |

`JobPostingSourceLink` 후보 필드:

| 필드 | 의미 |
| --- | --- |
| `job_posting_id` | canonical `JobPosting` |
| `source_type` | `job_alio` 또는 `alio_b1020` |
| `source_id` | `recrutPblntSn`, `idx`, `submissionNo` 등 |
| `evidence_id` | 원문 근거 |
| `match_status` | 아래 상태값 |
| `match_score` | 0.0-1.0 후보 점수 |
| `match_reasons` | 기관/제목/기간/첨부/URL 근거 |
| `conflict_fields` | 충돌 필드 목록 |

## 매칭 전처리

### 기관명 정규화

기관명은 법적 접미사를 제거하지 않는다. 다음 정도만 적용한다.

- 앞뒤 공백 제거
- 연속 공백 1칸으로 축소
- 괄호 주변 공백 정리
- 전각/반각 괄호 차이 정리
- `주식회사`, `(주)` 같은 법인 표기는 별칭 후보로만 추가

기관 매칭 우선순위:

1. 이미 확인된 `InstitutionIdentity`에서 `pblntInstCd` 또는 `pbadmsStdInstCd`와 `apbaId`가 같은
   내부 `Institution`에 연결된 경우
2. 정규화 기관명이 정확히 같은 경우
3. 기관명 alias가 같은 경우
4. 홈페이지 domain 또는 채용 접수 domain이 같은 경우

### 제목 정규화

제목은 비교용 normalized title을 따로 만든다.

- 공백/개행 제거
- 괄호 문자는 보존하되 공백만 정리
- `공고`, `채용공고`, `재공고` 같은 일반 suffix/prefix는 token 비교에서 낮은 가중치
- `2026년`, `기간제`, `인턴`, `전문연구직` 같은 채용 구분 token은 보존
- 숫자와 차수 token은 보존

### 날짜 정규화

Job-ALIO:

- `pbancBgngYmd` -> `start_date`
- `pbancEndYmd` -> `end_date`

ALIO `B1020`:

- HTML `공고기간` -> `start_date`, `end_date`
- 목록 `openDate`/`idate` -> 보조 date evidence

날짜 비교는 다음을 기록한다.

- `exact`: 시작일과 종료일 모두 동일
- `overlap`: 기간이 겹침
- `near`: 시작일 또는 종료일 차이가 1일 이내
- `missing`: 한쪽 기간 없음
- `conflict`: 기간이 겹치지 않음

## 후보 매칭 규칙

### exact_match

다음 조건을 모두 만족하면 같은 공고로 자동 연결한다.

- 기관 identity가 확정되어 같음
- normalized title이 같거나 핵심 token set이 거의 같음
- 공고 기간이 `exact` 또는 `overlap`
- 원문 URL domain, 접수 URL, 첨부 파일명 중 하나 이상이 일치하거나 매우 유사함

처리:

- Job-ALIO row를 canonical `JobPosting`으로 유지한다.
- ALIO `B1020`은 `JobPostingSourceLink(match_status=exact_match)`로 연결한다.
- ALIO에만 있는 첨부 label과 전형단계 표는 evidence로 추가한다.

### strong_candidate

다음 조건이면 자동 후보로 연결하되 review 가능 상태로 둔다.

- 기관명이 같거나 같은 `Institution` 후보로 묶임
- title 핵심 token이 대부분 일치
- 공고 기간이 `exact`, `overlap`, 또는 `near`

처리:

- `match_status=strong_candidate`
- 사용자에게는 “동일 공고 후보”로만 표현한다.
- 분석용 병합은 가능하지만 conflict field를 함께 표시한다.

### needs_review

다음 중 하나라도 해당하면 사람이 확인해야 한다.

- 기관명은 같지만 코드 mapping이 없음
- 제목은 유사하지만 차수/직렬/고용형태 token이 다름
- 날짜가 `missing` 또는 `conflict`
- 같은 Job-ALIO 공고에 ALIO 후보가 2개 이상 붙음
- 같은 ALIO `B1020` row에 Job-ALIO 후보가 2개 이상 붙음

처리:

- `match_status=needs_review`
- canonical row를 새로 합치지 않는다.
- 근거 URL과 비교 필드를 함께 남긴다.

### no_match

기관 후보가 다르거나 제목/기간 근거가 모두 약하면 연결하지 않는다.

처리:

- `match_status=no_match`는 audit log에만 남기고 canonical 모델에는 연결하지 않는다.

### source_only_job_alio

Job-ALIO에는 있으나 ALIO `B1020` 후보가 없을 때 쓴다.

가능한 이유:

- ALIO 공시가 늦게 올라옴
- 기관이 ALIO `B1020`에 해당 공고를 올리지 않음
- 제목 표기가 크게 달라 후보 검색에 실패함

### source_only_alio

ALIO `B1020`에는 있으나 Job-ALIO 후보가 없을 때 쓴다.

가능한 이유:

- Job-ALIO 검색 조건이 ongoing-only라 마감 공고를 놓침
- ALIO에는 과거/수정 공고가 남아 있음
- Job-ALIO가 아닌 기관 채용 페이지 공고만 존재함

### conflict

같은 공고로 보이는 근거가 충분하지만 핵심 값이 충돌할 때 쓴다.

충돌 예:

- 마감일이 다름
- 채용인원이 다름
- 첨부 직무기술서 파일명이 서로 다름
- 접수 URL이 서로 다름

처리:

- canonical row에는 Job-ALIO 값을 우선 보존한다.
- ALIO 값은 `EvidenceSource.fields`와 `conflict_fields`에 보존한다.
- 사용자-facing 리포트에는 “출처별 값 차이”로 표시한다.

## 점수화 v0

점수는 자동 병합을 위한 절대 기준이 아니라 후보 정렬용이다.

| 근거 | 가중치 |
| --- | --- |
| 기관 identity 확정 | 0.30 |
| 기관명/alias 일치 | 0.15 |
| 제목 핵심 token 일치 | 0.30 |
| 공고 기간 exact/overlap/near | 0.15 |
| URL 또는 첨부 파일명 유사 | 0.10 |

상태값 기준:

| 조건 | match_status |
| --- | --- |
| 0.90 이상이고 conflict 없음 | `exact_match` |
| 0.75 이상 | `strong_candidate` |
| 0.45 이상 | `needs_review` |
| 0.45 미만 | `no_match` |

기관 identity가 다르다고 확정된 경우 점수와 무관하게 `no_match`다.

## 중복 저장 방지

중복 방지 흐름:

1. Job-ALIO parser가 `JobPosting`을 만든다.
2. ALIO `B1020` parser는 바로 새 `JobPosting`을 만들지 않고 `AlioRecruitmentDisclosure` 후보를 만든다.
3. linker가 Job-ALIO와 ALIO 후보를 비교해 `JobPostingSourceLink`를 만든다.
4. `exact_match` 또는 `strong_candidate`만 canonical `JobPosting`에 연결한다.
5. `needs_review`, `source_only_alio`는 별도 후보 상태로 남긴다.

ALIO-only row를 언제 `JobPosting`으로 승격할지:

- Job-ALIO 검색 범위를 마감 공고까지 넓혀도 후보가 없고
- 기관 identity가 확인되며
- ALIO 제목/기간/원문 URL이 충분할 때
- `source_origin=alio_b1020`인 `JobPosting`으로 승격할 수 있다.

## Evidence 보존 방식

| EvidenceSource 필드 | Job-ALIO | ALIO B1020 |
| --- | --- | --- |
| `source_type` | `job_alio` | `alio_b1020` |
| `source_id` | `recrutPblntSn` | `idx` 우선, 없으면 `submissionNo` |
| `title` | 공고 제목 | ALIO 제목 |
| `url` | Job-ALIO 상세 또는 `srcUrl` | ALIO board URL |
| `excerpt` | 제목/기간/기관명 | 제목/공고기간/첨부 label |
| `fields` | NCS, 지원자격, steps key | `disclosureNo`, `submissionNo`, `idx`, 첨부 label |

`B1210`과 달리 `B1020`은 정상 `disclosureNo`가 있을 수 있지만, 수시 게시판 상세 key는 `idx`가 더
직접적이다. 따라서 `source_id`는 `idx` 우선, provenance에는 세 값을 모두 남긴다.

## 애매함 표현

사용자-facing 상태 문구:

| match_status | 표시 문구 |
| --- | --- |
| `exact_match` | 같은 공고로 확인됨 |
| `strong_candidate` | 같은 공고일 가능성이 높음 |
| `needs_review` | 같은 공고인지 확인 필요 |
| `source_only_job_alio` | Job-ALIO에서만 확인됨 |
| `source_only_alio` | ALIO 6-2에서만 확인됨 |
| `conflict` | 출처별 값 차이 있음 |
| `no_match` | 연결하지 않음 |

자동 리포트에서는 `exact_match` 외 상태를 확정 표현으로 쓰지 않는다.

## Parser 구현 순서

1. Job-ALIO parser
   - `recrutPblntSn`, 기관명/기관코드, 제목, 기간, NCS, 첨부를 정규화한다.
2. ALIO `B1020` parser
   - `idx`, `submissionNo`, `disclosureNo`, 제목, 공고기간, 채용분야, 첨부 label, 접수 URL을 정규화한다.
3. Linker
   - 기관 후보, 제목 token, 날짜, URL/첨부 유사도를 계산한다.
4. Evidence writer
   - canonical row와 양쪽 source evidence를 연결한다.

## 보류 사항

- 실제 기관 코드 mapping table 구축
- 제목 유사도 threshold를 raw sample 30건 이상으로 재조정
- ALIO `B1020` 전형단계 표의 세부 parser
- Job-ALIO 마감 공고 검색 범위 확대
