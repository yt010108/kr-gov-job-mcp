# MCP 도구 설계 초안

| 도구명 | 구분 | 우선순위 | 목적 |
| --- | --- | --- | --- |
| lookup_region_codes | 코드 조회 | P0 | 자연어 지역명이나 Job-ALIO 지역 코드로 근무지 코드 후보를 조회합니다. |
| search_public_jobs | 수집 | P0 | 공공기관 채용공고와 인턴 정보를 검색하고 지원 가능 후보를 추립니다. |
| fetch_job_detail | 수집 | P0 | 공고 상세와 직무기술서를 구조화해 분석 기준 데이터로 만듭니다. |
| map_ncs_competencies | 분석 | P0 | 공고와 직무기술서에서 NCS/KSA 역량을 추출합니다. |
| analyze_institution_strategy | 분석 | P0 | 기관의 최근 사업 방향과 직무 연결 포인트를 요약합니다. |
| analyze_institution_weakness | 분석 | P0 | 기관의 부족한 점과 개선 과제를 분석 가능한 형태로 정리합니다. |
| analyze_job_fit_report | 분석 | P0 | 공고 내용, NCS, 기관 정보를 연결해 이 지원자가 무엇을 준비해야 하는지 리포트로 정리합니다. |

## 도구별 입출력

### lookup_region_codes

입력:

- `query`

출력:

- Job-ALIO 코드 유형: `workRgnLst`
- 지역 코드
- 지역명
- 별칭

데이터 소스:

- Job-ALIO 채용정보 검색 페이지의 `workRgnLst` option 값

### search_public_jobs

구현 상태: Job-ALIO 검색 기반 1차 구현 완료. Cleaneye 채용/인턴 공고 사이트 통합과
`new_grad_only` 같은 코드 테이블 기반 필터는 아직 보류한다.

입력:

- `keyword`
- `page`
- `limit`
- `ongoing_only`
- `institution_code`
- `ncs_code`
- `region`
- `region_code`
- `academic_condition_code`
- `employment_type_code`
- `recruitment_type`
- `replacement_only`
- `announcement_start_date`
- `announcement_end_date`
- `institution_type`
- `institution_classification`

출력:

- 공고명
- 기관명
- 기관 코드
- 공고 시작일
- 마감일
- 진행 여부
- 지역
- NCS 코드/표시명 매핑 후보
- 고용 유형
- 채용 구분
- 채용 인원
- 원문 링크

데이터 소스:

- 잡알리오

### fetch_job_detail

입력:

- `job_url`
- `institution_name`

출력:

- 지원자격
- 우대사항
- 직무 내용
- 전형 절차
- NCS 키워드

데이터 소스:

- 공고 원문
- PDF/HTML 직무기술서

### map_ncs_competencies

입력:

- `job_detail`
- `duty_description_text`

출력:

- 직업기초능력
- 직무수행능력
- Knowledge
- Skill
- Attitude
- 역량 근거
- 검증 포인트

### analyze_institution_strategy

입력:

- `institution_name`
- `year`
- `job_family`

출력:

- 주요사업
- 성장 사업
- 디지털/보안/데이터 포인트
- 기관 이해 근거
- 사업 이해

데이터 소스:

- ALIO 주요사업
- 기관 홈페이지

### analyze_institution_weakness

입력:

- `institution_name`
- `year`

출력:

- 개선 과제
- 운영/사업 약점
- 조심할 표현
- 지원자가 기여할 수 있는 개선 아이디어

데이터 소스:

- ALIO 국회 지적사항
- 경영평가

### analyze_job_fit_report

입력:

- `job_detail`
- `ncs_profile`
- `institution_strategy`
- `institution_weakness`
- `applicant_profile`

출력:

- 공고 요구사항과 NCS 역량 연결 결과
- 기관 사업 방향과 직무 연결 결과
- 지원자가 우선 준비해야 할 항목
- 보완해야 할 직무 지식
- 확인해야 할 기관 자료
- 준비 우선순위
- 근거 링크
