# kr-gov-job-mcp

한국 공공기관 NCS 및 채용 정보 분석을 위한 MCP(Model Context Protocol) 서버입니다.
단순 공고 검색을 넘어 **채용공고 · 직무기술서 · NCS 역량 · 기관 분석**의 파편화된 정보를 근거 기반으로 연결해 취업 준비 전략을 정리합니다.

## 취업 정보 분석 워크플로우

이 MCP는 다음 4단계로 활용할 수 있습니다.

1. **발굴 (Search)** — `search_public_jobs`로 조건에 맞는 채용공고를 찾습니다.
2. **분석 (Deep Dive)** — `fetch_job_detail`로 직무를 확인하고 `analyze_institution_strategy`로 기관의 사업 방향을 살펴봅니다.
3. **전략 (Fit Analysis)** — `analyze_job_fit_report`로 지원 직무와 보유 역량의 준비 항목·지식 갭을 정리합니다.
4. **표현 (Answer Framework)** — `generate_star_answer_framework`로 사용자 경험을 근거 기반 STAR 답변 뼈대로 정리합니다.

에이전트에는 예를 들어 다음과 같이 요청할 수 있습니다.

> "KISA 공고를 검색하고, 직무기술서와 기관 사업 전략을 바탕으로 준비 전략을 정리해줘."

### 자연어 요청 예시

- "지금 지원할 수 있는 한국인터넷진흥원 관련 공고를 찾아줘."
- "전산직으로 지원할 만한 공공기관 채용공고를 찾아줘."
- "KISED 전산직 면접 준비 도와줘."
- "전산직 지원 경험을 STAR 구조로 정리하고 부족한 근거를 질문해줘."

기관명·약칭이나 직무명이 Job-ALIO 코드와 다를 수 있으므로, 에이전트는 필요할 때 기관은
`lookup_job_alio_codes`, 직무는 `resolve_ncs_code`로 후보를 확인한 뒤 공고 검색·기관 분석 도구를 이어서 호출합니다.

| 도구 | 역할 |
| --- | --- |
| `search_public_jobs` | Job-ALIO 채용공고를 조건별로 검색 |
| `resolve_ncs_code` | 자연어 직무를 Job-ALIO NCS 코드와 리포트 맥락으로 해석 |
| `fetch_job_detail` | 공고 상세·첨부파일·전형 단계·NCS 매핑을 구조화 |
| `analyze_job_fit_report` | 지원 직무 적합도와 준비 전략을 정리 |
| `analyze_institution_strategy` | ALIO 및 연구·정책 자료 기반 기관 전략 신호를 분석 |
| `prepare_application_strategy` | 기관·직무 해석부터 공고별 준비 전략과 면접 카드까지 통합 |
| `generate_star_answer_framework` | 사용자 경험을 STAR 구조와 보완 질문으로 정리 |

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
- ALIO 주요사업, 연구/정책 자료, 국회 지적사항 기반 면접 카드 생성
- 공고, NCS, 기관 정보 기반 준비 항목 리포트 생성
- 공고 후보, 적합도, NCS, 기관 분석, 면접 카드를 한 응답으로 통합
- 사용자 경험 기반 STAR 자기소개서·면접 답변 프레임 생성

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

## CI 검증

GitHub Actions는 pull request와 `main` 브랜치 push에서 Python 3.11/3.12로 Ruff와 pytest를
실행하고, Python 3.12에서 sdist/wheel을 빌드합니다. Docker 컨테이너 실행은 필수 CI에 포함하지 않습니다.

로컬에서 같은 범위를 확인하려면 다음을 실행합니다.

```bash
python -m ruff check .
python -m pytest -q
python -m pip install build
python -m build
```

workflow가 `main`에 반영된 뒤 저장소 보호 규칙에서 `Test (Python 3.11)`, `Test (Python 3.12)`,
`Build package`를 필수 체크로 지정합니다. 보호 규칙은 GitHub 저장소 설정에서 별도로 적용해야 합니다.

## Docker / Git 소스 빌드 배포

루트 `Dockerfile`은 Git 소스 빌드 화면에서 바로 사용할 수 있다. 컨테이너는 기본적으로
`PORT` 환경변수 또는 `8000` 포트에서 HTTP MCP endpoint를 실행한다.
배포한 소스를 확인하려면 빌드 시 `APP_SOURCE_REF`와 `APP_REVISION`을 전달한다. 두 값은
`/health`와 `health_check`에 표시되며, 전달하지 않으면 `unknown`이다.

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
docker build -t kr-gov-job-mcp \
  --build-arg APP_SOURCE_REF=refs/heads/main \
  --build-arg APP_REVISION="$(git rev-parse HEAD)" .
docker run --rm -p 8000:8000 kr-gov-job-mcp
curl http://localhost:8000/health
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
      lookup-job-alio-codes.md
      resolve-ncs-code.md
      search-public-jobs.md
      fetch-job-detail.md
      map-ncs-competencies.md
      analyze-institution-strategy.md
      analyze-institution-weakness.md
      prepare-institution-interview.md
      analyze-job-fit-report.md
      generate-star-answer-framework.md
      prepare-application-strategy.md
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

## 현재 MVP 상태

확인 기준은 `python -m kr_gov_job_mcp.server --list-tools`로 등록되는 기본 도구입니다.

### 현재 구현됨

- 서버 상태 확인
- MCP stdio 서버 실행
- MCP Streamable HTTP POST 엔드포인트 실행
- Job-ALIO 지역 코드 조회
- Job-ALIO 기관명/NCS 코드 조회
- 자연어 직무의 Job-ALIO NCS 코드 해석
- Job-ALIO 공공기관 채용공고 검색
- Job-ALIO 공고 상세 조회
- Job-ALIO 공고와 직무기술서 PDF 기반 NCS/KSA 역량 정리
- Job-ALIO 상세 정보 기반 최소 준비 리포트 생성
- evidence 입력 기반 기관 사업 방향 signal 요약
- 기관명과 직무 기반 통합 지원 전략 생성
- 사용자 경험 근거 기반 STAR 답변 프레임 생성
