# kr-gov-job-mcp

한국 공공기관 NCS 취업 준비 MCP입니다.

채용공고, 직무기술서, NCS 역량, ALIO/클린아이 기관 분석을 근거 기반으로 연결하는 것을 목표로 합니다.

## 문제 정의

공공기관 취업 준비자는 보통 다음 자료를 따로 확인해야 합니다.

- 채용공고와 직무기술서
- NCS 직업기초능력 및 직무수행능력
- ALIO 주요사업, 국회 지적사항
- 클린아이 지방공기업 자료
- 기관 홈페이지, 보도자료, 채용 페이지

자료는 많지만, 실제로 어려운 부분은 이 자료들을 직무 판단과 기관 이해로 연결하는 과정입니다.
이 MCP는 단순 공고 검색이 아니라 공고, 직무기술서, NCS, 기관 분석을 한 흐름으로 정리하는 취업 정보 분석 워크플로우를 제공합니다.

## 핵심 기능

- 공공기관 채용공고, 인턴 검색
- 공고 상세와 직무기술서 구조화
- NCS/KSA 역량 매핑
- ALIO 기반 기관 최근 사업 방향 분석
- 국회 지적사항 기반 개선 과제 분석
- 공고, NCS, 기관 정보 기반 준비 항목 리포트 생성

## 예상 도구

초기 설계 도구는 `docs/tool-design.md`에 정리되어 있습니다.

우선 구현 후보:

- `search_public_jobs`
- `fetch_job_detail`
- `map_ncs_competencies`
- `analyze_institution_strategy`
- `analyze_institution_weakness`
- `analyze_job_fit_report`

## 데이터 소스

- 잡알리오 채용정보
- ALIO 경영공시
- 클린아이 지방공기업 정보
- 기관별 채용 페이지
- 기관 보도자료
- 나라장터 입찰/외주 정보

## 프로젝트 구조

```txt
kr-gov-job-mcp/
  docs/
    proposal.md
    tool-design.md
    demo-scenario.md
    collector-layer.md
    server-scaffold.md
    job-alio-field-inventory.md
    alio-disclosure-field-inventory.md
  examples/
    kisa-demo-input.json
    kisa-demo-output.md
  src/
    kr_gov_job_mcp/
      clients/
      collectors/
      schemas/
      server.py
      tools/
  tests/
  .env.example
  .gitignore
  pyproject.toml
```

## 개발 시작

Python 3.11 이상을 권장합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

서버 스캐폴드는 다음 명령으로 확인할 수 있습니다.

```powershell
python -m kr_gov_job_mcp.server
python -m kr_gov_job_mcp.server --health
python -m kr_gov_job_mcp.server --list-tools
```

패키지를 editable로 설치한 뒤에는 `kr-gov-job-mcp --health`도 사용할 수 있습니다.
자세한 실행과 도구 등록 구조는 `docs/server-scaffold.md`에 정리되어 있습니다.

## 개인정보 원칙

이 저장소에는 실제 개인정보, API 키, 로컬 분석 자료를 커밋하지 않습니다.

`.env.example`만 공유하고 실제 값은 `.env`로 관리합니다.

## 라이선스

TBD
