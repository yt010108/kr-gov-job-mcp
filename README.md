# kr-gov-job-mcp

한국 공공기관 NCS 취업 준비 MCP입니다.

채용공고, 직무기술서, NCS 역량, ALIO/클린아이 기관 분석을 근거 기반으로 연결하는 것을 목표로 합니다.

## 현재 MVP 상태

확인 기준은 `python -m kr_gov_job_mcp.server --list-tools`로 등록되는 기본 도구입니다.

### 현재 구현됨

- 서버 상태 확인
- MCP stdio 서버 실행
- MCP Streamable HTTP POST 엔드포인트 실행
- Job-ALIO 지역 코드 조회
- Job-ALIO 공공기관 채용공고 검색
- Job-ALIO 공고 상세 조회
- Job-ALIO 상세 정보 기반 최소 준비 리포트 생성
- evidence 입력 기반 기관 사업 방향 signal 요약
- evidence 입력 기반 기관 개선 과제 signal 요약
- 첨부파일, 전형 단계, NCS 매핑 후보 구조화

### 아직 미구현

- MCP SSE GET stream, resumable session 같은 고급 HTTP transport 기능
- NCS/KSA 상세 역량 분석
- ALIO/클린아이 자료 자동 수집 기반 기관 분석
- 기관 signal을 준비 리포트에 자동 연결하는 흐름

### 다음 MVP 목표

공고 검색, 상세 조회, 준비 항목 리포트 생성까지 한 번에 확인 가능한 세로 흐름을 데모 문서와 실제 출력 예시로 고정합니다.

현재 실행 가능한 명령:

```powershell
python -m kr_gov_job_mcp.server --list-tools
python -m kr_gov_job_mcp.server --stdio
python -m kr_gov_job_mcp.server --http --host 0.0.0.0 --port 8000
python -m kr_gov_job_mcp.server --call-tool lookup_region_codes --input "{\"query\":\"서울특별시\"}"
python -m kr_gov_job_mcp.server --call-tool search_public_jobs --input "{\"keyword\":\"정보보호\",\"limit\":3,\"ongoing_only\":false}"
python -m kr_gov_job_mcp.server --call-tool fetch_job_detail --input "{\"job_id\":\"<검색 결과의 source_job_id>\"}"
python -m kr_gov_job_mcp.server --call-tool analyze_job_fit_report --input "{\"job_id\":\"<검색 결과의 source_job_id>\",\"target_role\":\"정보보호\",\"known_skills\":[\"웹 보안\",\"네트워크\",\"정보보안기사\"]}"
python -m kr_gov_job_mcp.server --call-tool collect_institution_context --input "{\"institution_name\":\"한국농수산식품유통공사\",\"sources\":[\"alio\",\"homepage\"]}"
python -m kr_gov_job_mcp.server --call-tool analyze_institution_strategy --input "{\"institution_name\":\"한국인터넷진흥원\",\"year\":2026,\"job_family\":\"정보보호\"}"
python -m kr_gov_job_mcp.server --call-tool analyze_institution_weakness --input "{\"institution_name\":\"한국인터넷진흥원\",\"year\":2026}"
```

현재 MVP 데모 흐름은 `docs/demo-scenario.md`, 실제 KISA 기준 출력은 `examples/kisa-real-demo-output.md`에서 볼 수 있습니다.

| 도구 | 상태 | 간략 설명 |
| --- | --- | --- |
| `health_check` | 구현됨 | 서버 scaffold 상태, 서비스명, 버전, 등록 도구 수를 반환한다. |
| `lookup_region_codes` | 구현됨 | `query`로 받은 지역명 또는 Job-ALIO 지역 코드를 조회해 `matches[].code`, `matches[].name`, `matches[].aliases`를 반환한다. 예: `서울특별시` → `R3010`. |
| `search_public_jobs` | 구현됨 | Job-ALIO 채용공고 목록을 검색한다. 입력/출력 JSON field는 영어 `snake_case`이며, `keyword`, `region`, `institution_code`, `ncs_code`, `employment_type_code`, `announcement_start_date` 같은 필터를 받아 `jobs[].source_job_id`, `jobs[].title`, `jobs[].institution_name`, `jobs[].ncs_mappings` 등을 반환한다. |
| `fetch_job_detail` | 구현됨 | `job_id`, `source_job_id`, `recruitment_notice_sn` 중 하나로 상세 공고를 조회해 `job.qualification`, `job.attachments`, `job.steps`, `job.ncs_mappings` 등을 반환한다. |
| `analyze_job_fit_report` | 구현됨 MVP | `job_id`, `target_role`, `known_skills`를 받아 `preparation_items`, `knowledge_gaps`, `evidence_links`, `verification_notes`를 생성한다. 기관 분석은 아직 자동 연결하지 않는다. |
| `collect_institution_context` | 구현됨 MVP | `institution_name`, `sources`를 받아 ALIO 기관 정보 기반 `identity_candidates`, `evidence`, `signals`를 생성한다. |
| `analyze_institution_strategy` | 구현됨 MVP | `institution_name`, `year`, `job_family`, `evidence`, `signals`를 받아 `strategy_signals`와 `verification_notes`를 반환한다. |
| `analyze_institution_weakness` | 구현됨 MVP | `institution_name`, `year`, `evidence`, `signals`를 받아 `weakness_signals`, `careful_wording`, `verification_notes`를 반환한다. |
| `map_ncs_competencies` | 예정 | planned schema 기준 `job_detail`, `duty_description_text`를 바탕으로 `knowledge`, `skills`, `attitudes`, `evidence`, `verification_notes`를 추출한다. |

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
현재 MVP에서 Job-ALIO 필드 관찰은 `docs/inventory/job-alio-field-inventory.md`를 기준으로 봅니다.

기본 검증 명령:

```powershell
python -m pytest -q
python -m ruff check .
```

## Docker / Git 소스 빌드 배포

루트 `Dockerfile`은 Git 소스 빌드 화면에서 바로 사용할 수 있다. 컨테이너는 기본적으로
`PORT` 환경변수 또는 `8000` 포트에서 HTTP MCP endpoint를 실행한다.

등록 화면 입력값:

| 항목 | 값 |
| --- | --- |
| MCP 서버 이름 | `kr-gov-job-mcp` |
| 설명 | `Korean public-sector Job-ALIO and NCS preparation MCP server` |
| Git URL | `https://github.com/yt010108/kr-gov-job-mcp.git` |
| 브랜치 / ref | `main` |
| Dockerfile 경로 | `Dockerfile` |
| PAT | 공개 저장소라면 비워둠 |

컨테이너가 제공하는 endpoint:

| 경로 | 용도 |
| --- | --- |
| `/health` | 배포 health check |
| `/mcp` | MCP JSON-RPC POST endpoint |

로컬 Docker 확인:

```bash
docker build -t kr-gov-job-mcp .
docker run --rm -p 8000:8000 kr-gov-job-mcp
```

MCP HTTP 호출 예시:

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"lookup_region_codes","arguments":{"query":"서울특별시"}}}'
```

## 프로젝트 구조

```txt
kr-gov-job-mcp/
  Dockerfile
  .dockerignore
  docs/
    proposal.md
    tool-design/
      index.md
      lookup-region-codes.md
      search-public-jobs.md
      fetch-job-detail.md
      collect-institution-context.md
      map-ncs-competencies.md
      analyze-institution-strategy.md
      analyze-institution-weakness.md
      analyze-job-fit-report.md
    inventory/
      job-alio-field-inventory.md
      alio-disclosure-field-inventory.md
      cleaneye-field-inventory.md
      raw-data-inventory.md
      raw-data-inventory.json
    demo-scenario.md
    collector-workflow.md
    server-scaffold.md
    archive/
      source-data-erd.md
      institution-analysis-inputs.md
      job-alio-alio-b1020-linking.md
      alio-pagination-policy.md
      alio-sample-validation.md
      alio-html-structure.md
      ncs-competency-mapping.md
      job-fit-report.md
      cleaneye-html-structure.md
  examples/
    kisa-demo-input.json
    kisa-demo-template.md
    kisa-real-demo-output.md
  src/
    kr_gov_job_mcp/
      clients/
      collectors/
      schemas/
      mcp_http.py
      mcp_stdio.py
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
python -m kr_gov_job_mcp.server --stdio
python -m kr_gov_job_mcp.server --http --host 0.0.0.0 --port 8000
```

패키지를 editable로 설치한 뒤에는 `kr-gov-job-mcp --health`도 사용할 수 있습니다.
자세한 실행과 도구 등록 구조는 `docs/server-scaffold.md`에 정리되어 있습니다.

로컬 MCP 클라이언트에는 다음처럼 stdio 서버로 연결할 수 있습니다.

```json
{
  "mcpServers": {
    "kr-gov-job-mcp": {
      "command": "python",
      "args": ["-m", "kr_gov_job_mcp.server", "--stdio"]
    }
  }
}
```

## 개인정보 원칙

이 저장소에는 실제 개인정보, API 키, 로컬 분석 자료를 커밋하지 않습니다.

`.env.example`만 공유하고 실제 값은 `.env`로 관리합니다.

## 라이선스

추후 결정합니다.
