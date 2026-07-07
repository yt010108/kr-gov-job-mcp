# kr-gov-job-mcp

한국 공공기관 NCS 취업 준비 MCP입니다.

채용공고, 직무기술서, NCS 역량, ALIO/클린아이 기관 분석을 근거 기반으로 연결하는 것을 목표로 합니다.

## 현재 MVP 상태

확인 기준은 `python -m kr_gov_job_mcp.server --list-tools`로 등록되는 기본 도구입니다.

### 현재 구현됨

- 서버 상태 확인
- Job-ALIO 지역 코드 조회
- Job-ALIO 공공기관 채용공고 검색
- Job-ALIO 공고 상세 조회
- Job-ALIO 상세 정보 기반 최소 준비 리포트 생성
- 첨부파일, 전형 단계, NCS 매핑 후보 구조화

### 아직 미구현

- 실제 MCP stdio/SSE 서버 연결
- NCS/KSA 상세 역량 분석
- ALIO/클린아이 기관 분석
- 기관 signal을 준비 리포트에 자동 연결하는 흐름

### 다음 MVP 목표

공고 검색, 상세 조회, 준비 항목 리포트 생성까지 한 번에 확인 가능한 세로 흐름을 데모 문서와 실제 출력 예시로 고정합니다.

현재 실행 가능한 명령:

```powershell
python -m kr_gov_job_mcp.server --list-tools
python -m kr_gov_job_mcp.server --call-tool lookup_region_codes --input "{\"query\":\"서울특별시\"}"
python -m kr_gov_job_mcp.server --call-tool search_public_jobs --input "{\"keyword\":\"정보보호\",\"limit\":3,\"ongoing_only\":false}"
python -m kr_gov_job_mcp.server --call-tool fetch_job_detail --input "{\"job_id\":\"<검색 결과의 source_job_id>\"}"
python -m kr_gov_job_mcp.server --call-tool analyze_job_fit_report --input "{\"job_id\":\"<검색 결과의 source_job_id>\",\"target_role\":\"정보보호\",\"known_skills\":[\"웹 보안\",\"네트워크\",\"정보보안기사\"]}"
```

| 도구 | 상태 | 간략 설명 |
| --- | --- | --- |
| `health_check` | 구현됨 | 서버 scaffold 상태, 서비스명, 버전, 등록 도구 수를 반환한다. |
| `lookup_region_codes` | 구현됨 | 사용자가 입력한 지역명 또는 Job-ALIO 지역 코드를 Job-ALIO 검색용 `workRgnLst` 코드 후보로 변환/조회한다. 예: `서울특별시` → `R3010`. |
| `search_public_jobs` | 구현됨 | Job-ALIO 채용공고 목록을 검색한다. 키워드, 지역, 기관 코드, NCS 코드, 고용형태, 공고 기간 같은 필터를 받아 공고 요약과 NCS 매핑 후보를 반환한다. |
| `fetch_job_detail` | 구현됨 | `search_public_jobs`에서 얻은 Job-ALIO 공고 ID로 상세 공고를 조회한다. 지원자격, 우대사항, 전형절차, 첨부파일, 직무기술서 후보, 전형 단계 metadata를 구조화한다. |
| `analyze_job_fit_report` | 구현됨 MVP | Job-ALIO 상세 정보만 사용해 준비 항목, 지식 보완 후보, 근거 링크, 검증 노트를 생성한다. ALIO/클린아이 기관 분석은 아직 자동 연결하지 않는다. |
| `map_ncs_competencies` | 예정 | 공고 상세와 직무기술서 텍스트를 바탕으로 NCS/KSA 역량을 추출한다. 근거가 있는 경우에만 Knowledge, Skill, Attitude, 직업기초능력, 직무수행능력 후보를 만든다. |
| `analyze_institution_strategy` | 예정 | ALIO 주요사업, 기관 홈페이지, 필요 시 Cleaneye 사업 자료를 근거로 기관의 최근 사업 방향과 직무 연결 포인트를 요약한다. |
| `analyze_institution_weakness` | 예정 | ALIO 국회 지적사항, 경영평가, 감사/운영 자료 등을 근거로 기관의 개선 과제와 지원자가 기여할 수 있는 포인트를 정리한다. 단정적 비판이 아니라 근거 기반 개선 관점으로 표현한다. |

## 문제 정의

공공기관 취업 준비자는 보통 다음 자료를 따로 확인해야 합니다.

- 채용공고와 직무기술서
- NCS 직업기초능력 및 직무수행능력
- ALIO 주요사업, 국회 지적사항
- 클린아이 지방공기업 자료
- 기관 홈페이지

자료는 많지만, 실제로 어려운 부분은 이 자료들을 직무 판단과 기관 이해로 연결하는 과정입니다.
이 MCP는 단순 공고 검색이 아니라 공고, 직무기술서, NCS, 기관 분석을 한 흐름으로 정리하는 취업 정보 분석 워크플로우를 제공합니다.

## 핵심 기능

- 공공기관 채용공고, 인턴 검색
- 공고 상세와 직무기술서 구조화
- NCS/KSA 역량 매핑
- ALIO 기반 기관 최근 사업 방향 분석
- 국회 지적사항 기반 개선 과제 분석
- 공고, NCS, 기관 정보 기반 준비 항목 리포트 생성

## 도구 설계 문서

초기 설계 도구는 `docs/tool-design/index.md`에 정리되어 있습니다.

## 데이터 소스

- 잡알리오 채용정보
- ALIO 경영공시
- 클린아이 지방공기업 정보
- 나라장터 입찰/외주 정보

## 수집 워크플로우

수집기는 최종 분석 스키마를 확정하기 전에 원본 응답, 요청 조건, 결측 패턴을 남기는 역할을 합니다.
로컬 설치, raw sample 저장 위치, 필드 인벤토리 작성 규칙, 데모 재현 순서는
`docs/collector-workflow.md`에 정리되어 있습니다.

기본 검증 명령:

```powershell
python -m pytest -q
python -m ruff check .
```

## 프로젝트 구조

```txt
kr-gov-job-mcp/
  docs/
    proposal.md
    tool-design/
      index.md
      lookup-region-codes.md
      search-public-jobs.md
      fetch-job-detail.md
      map-ncs-competencies.md
      analyze-institution-strategy.md
      analyze-institution-weakness.md
      analyze-job-fit-report.md
    demo-scenario.md
    collector-layer.md
    collector-workflow.md
    raw-data-inventory.md
    source-data-erd.md
    ncs-competency-mapping.md
    institution-analysis-inputs.md
    job-fit-report.md
    server-scaffold.md
    job-alio-field-inventory.md
    job-alio-alio-b1020-linking.md
    alio-disclosure-field-inventory.md
    alio-pagination-policy.md
    alio-html-structure.md
    cleaneye-field-inventory.md
    cleaneye-html-structure.md
  examples/
    kisa-demo-input.json
    kisa-demo-output.md
    raw-data-inventory.json
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
