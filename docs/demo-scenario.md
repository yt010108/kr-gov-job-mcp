# 데모 시나리오

## 사용자 입력

```txt
한국인터넷진흥원 전산/보안 직무 공고를 준비하고 싶어.
내 프로젝트 경험과 멘토링 피드백을 반영해서 자기소개서와 면접 준비표를 만들어줘.
```

## MCP 처리 흐름

1. `search_public_jobs`로 관련 공고를 찾습니다.
2. `fetch_job_detail`로 공고 상세와 직무기술서를 구조화합니다.
3. `map_ncs_competencies`로 NCS/KSA 역량을 추출합니다.
4. `analyze_institution_strategy`로 기관 최근 사업 방향을 분석합니다.
5. `analyze_institution_weakness`로 개선 과제를 정리합니다.
6. `collect_research_reports`로 면접 답변 근거가 될 보고서를 찾습니다.
7. `match_user_experience`로 사용자 경험과 문항을 매칭합니다.
8. `critique_self_intro`로 자기소개서 초안을 진단합니다.
9. `generate_interview_pack`으로 면접 준비 패키지를 만듭니다.
10. `generate_application_brief`로 최종 지원 준비표를 생성합니다.

## 예상 출력

- 공고 핵심 요약
- NCS 역량 매핑
- KISA 주요사업 요약
- ALIO 국회 지적사항 기반 개선 포인트
- 연구보고서 기반 마지막 할 말
- 사용자 경험과 문항별 매칭
- 부족한 경험과 보완 방법
- 예상 면접 질문 10개
- 답변 근거 링크

## 심사 시 강조 포인트

- 한국 공공기관 취업이라는 명확한 문제를 해결합니다.
- 단순 검색이 아니라 공고, 기관, 직무, 자기분석을 연결합니다.
- ALIO/클린아이/NCS 같은 한국 특화 공개 자료를 활용합니다.
- 자기소개서 대필보다 근거 기반 진단과 준비표 생성에 초점을 둡니다.
