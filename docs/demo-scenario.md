# 데모 시나리오

현재 데모는 구현된 MVP 흐름을 먼저 보여준다. 장기 목표인 NCS/KSA 상세 분석과 기관 분석은 planned 항목으로 분리한다.

## 사용자 입력

```txt
한국인터넷진흥원 전산/보안 직무 공고와 기관 정보를 분석하고 싶어.
공고, NCS, ALIO 자료를 연결해서 이 지원자가 무엇을 준비해야 하는지 정리해줘.
```

## 현재 MVP 처리 흐름

현재 실제로 실행 가능한 흐름:

1. `search_public_jobs`로 관련 공고를 찾습니다.
2. `fetch_job_detail`로 공고 상세, 첨부파일, 전형 단계, NCS 후보를 구조화합니다.
3. `analyze_job_fit_report`로 Job-ALIO 상세 정보 기반의 최소 준비 항목 리포트를 생성합니다.

실제 KISA 기준 출력 예시는 `examples/kisa-real-demo-output.md`에 기록되어 있습니다.

## 실제 실행 명령

KISA 공고 검색:

```bash
python -m kr_gov_job_mcp.server --call-tool search_public_jobs --input '{"keyword":"한국인터넷진흥원","limit":5,"ongoing_only":false}'
```

공고 상세 조회:

```bash
python -m kr_gov_job_mcp.server --call-tool fetch_job_detail --input '{"job_id":"302324"}'
```

준비 리포트 생성:

```bash
python -m kr_gov_job_mcp.server --call-tool analyze_job_fit_report --input '{"job_id":"302324","target_role":"정보보호","known_skills":["웹 보안","네트워크","정보보안기사"]}'
```

## 현재 출력에서 확인할 수 있는 것

- 공고 핵심 요약
- NCS 코드와 표시명 후보
- 첨부파일과 직무기술서 후보
- 지원자격, 우대사항, 전형절차 기반 준비 항목
- Job-ALIO 근거 링크
- 기관 분석 미연결 상태에 대한 `verification_notes`

## Planned 분석 흐름

다음 도구는 설계 문서에는 있지만 현재 기본 registry에는 등록되어 있지 않습니다.

1. `map_ncs_competencies`: 직무기술서 본문에서 NCS/KSA 역량을 추출합니다.
2. `analyze_institution_strategy`: ALIO 주요사업과 기관 홈페이지를 근거로 기관 최근 사업 방향을 분석합니다.
3. `analyze_institution_weakness`: 국회 지적사항, 경영평가, 감사 자료를 근거로 개선 과제를 정리합니다.

planned 흐름까지 연결되면 최종 출력은 다음 항목을 포함합니다.

- NCS/KSA 상세 역량 매핑
- KISA 주요사업 요약
- ALIO 국회 지적사항 기반 개선 포인트
- 기관 signal을 반영한 준비 항목 리포트
- 분석 근거 링크

## 예시 문서 구분

- `examples/kisa-real-demo-output.md`: 실제 Job-ALIO 명령 실행 결과를 기준으로 작성한 현재 MVP 출력.
- `examples/kisa-demo-template.md`: NCS/KSA와 기관 분석까지 연결된 장기 목표 출력 형태를 보여주는 템플릿.

## 심사 시 강조 포인트

- 한국 공공기관 취업이라는 명확한 문제를 해결합니다.
- 단순 검색이 아니라 공고, 기관, 직무, NCS를 연결합니다.
- ALIO/클린아이/NCS 같은 한국 특화 공개 자료를 활용합니다.
- 현재 MVP는 단순 공고 조회를 넘어, 공고 상세와 직무기술서 후보를 근거로 준비 항목을 생성합니다.
