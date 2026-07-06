# MCP 도구 설계 초안

| 도구명 | 구분 | 우선순위 | MVP | 목적 |
| --- | --- | --- | --- | --- |
| search_public_jobs | 수집 | P0 | Yes | 공공기관 채용공고, 인턴, 공모전 정보를 검색하고 지원 가능 후보를 추립니다. |
| fetch_job_detail | 수집 | P0 | Yes | 공고 상세와 직무기술서를 구조화해 지원 준비의 기준 데이터로 만듭니다. |
| map_ncs_competencies | 분석 | P0 | Yes | 공고와 직무기술서에서 NCS/KSA 역량을 추출합니다. |
| analyze_institution_strategy | 분석 | P0 | Yes | 기관의 최근 사업 방향과 직무 연결 포인트를 요약합니다. |
| analyze_institution_weakness | 분석 | P0 | Yes | 기관의 부족한 점과 개선 과제를 면접 답변 소재로 바꿉니다. |
| collect_research_reports | 수집 | P1 | Yes | 연구보고서와 사업보고서를 수집해 직무 관심도 근거를 만듭니다. |
| match_user_experience | 개인화 | P0 | Yes | 사용자 경험을 요구역량, NCS, 자기소개서 문항과 매칭합니다. |
| critique_self_intro | 평가 | P0 | Yes | 자기소개서 초안을 공고, NCS, 기관 분석 기준으로 진단합니다. |
| generate_interview_pack | 생성 | P0 | Yes | 기관과 직무에 맞춘 면접 준비 패키지를 생성합니다. |
| generate_application_brief | 생성 | P1 | Yes | 공공기관 지원 준비표를 한 장짜리 실행 문서로 만듭니다. |
| store_mentoring_feedback | 개인화 | P1 | No | 멘토링 피드백을 사용자별 답변 개선 규칙으로 저장합니다. |
| export_to_notion_or_pdf | 내보내기 | P2 | No | 지원 준비표를 Notion 페이지나 PDF 문서로 내보냅니다. |

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
- 공모전/인턴 공고 사이트

### fetch_job_detail

입력:

- `job_url`
- `institution_name`

출력:

- 지원자격
- 우대사항
- 직무 내용
- 전형 절차
- 자기소개서 문항
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
- 자기소개서 증거
- 면접 확인 포인트

### analyze_institution_strategy

입력:

- `institution_name`
- `year`
- `job_family`

출력:

- 주요사업
- 성장 사업
- 디지털/보안/데이터 포인트
- 지원동기 근거
- 면접 사업 이해

데이터 소스:

- ALIO 주요사업
- 기관 홈페이지
- 보도자료
- 연구보고서

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

### collect_research_reports

입력:

- `institution_name`
- `job_family`
- `keyword`

출력:

- 보고서명
- 핵심 내용
- 직무 연결 포인트
- 마지막 할 말 후보
- 링크

### match_user_experience

입력:

- `user_profile`
- `experience_notes`
- `ncs_profile`
- `self_intro_questions`

출력:

- 문항별 추천 경험
- 강점
- 약점
- 보완 경험
- 수치화 필요 항목
- GitHub/블로그 증거

### critique_self_intro

입력:

- `question`
- `answer`
- `institution_strategy`
- `ncs_profile`
- `mentoring_rules`

출력:

- 문항 적합도
- NCS 반영도
- 기관 분석 반영도
- 구체성
- 차별성
- 수정 제안
- 꼬리질문

### generate_interview_pack

입력:

- `job_detail`
- `institution_strategy`
- `weakness`
- `user_experience_match`

출력:

- 1분 자기소개
- 지원동기
- 직무역량 답변 구조
- 기관 사업 질문
- 부족한 점 질문
- 마지막 할 말
- 꼬리질문
- 근거 링크

### generate_application_brief

입력:

- `all_analysis_outputs`

출력:

- 기관명
- 공고명
- 직무
- 마감일
- 요구역량
- NCS 매핑
- 기관 방향
- 부족한 점
- 문항별 소재
- 면접 질문
- 참고 링크
