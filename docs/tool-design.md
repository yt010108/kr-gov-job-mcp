# MCP 도구 설계 초안

| 도구명 | 구분 | 우선순위 | 목적 |
| --- | --- | --- | --- |
| search_public_jobs | 수집 | P0 | 공공기관 채용공고와 인턴 정보를 검색하고 지원 가능 후보를 추립니다. |
| fetch_job_detail | 수집 | P0 | 공고 상세와 직무기술서를 구조화해 분석 기준 데이터로 만듭니다. |
| map_ncs_competencies | 분석 | P0 | 공고와 직무기술서에서 NCS/KSA 역량을 추출합니다. |
| analyze_institution_strategy | 분석 | P0 | 기관의 최근 사업 방향과 직무 연결 포인트를 요약합니다. |
| analyze_institution_weakness | 분석 | P0 | 기관의 부족한 점과 개선 과제를 분석 가능한 형태로 정리합니다. |
| analyze_job_fit_report | 분석 | P0 | 공고 내용, NCS, 기관 정보를 연결해 이 지원자가 무엇을 준비해야 하는지 리포트로 정리합니다. |

## 도구별 입출력

### search_public_jobs

입력:

- `keyword`
- `region`
- `job_family`
- `employment_type`
- `deadline_range`
- `new_grad_only`

출력:

- 공고명
- 기관명
- 직무
- 마감일
- 지역
- 요구역량
- 원문 링크
- 추천 사유

데이터 소스:

- 잡알리오
- 클린아이
- 기관별 채용 페이지
- 인턴 공고 사이트

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
- 기관 채용 페이지

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
- 보도자료

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
- 기관 보도자료

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
