# MCP 서버 스캐폴드

이 문서는 현재 서버 엔트리포인트와 도구 등록 구조를 설명한다.

## 로컬 실행

개발 환경 설치:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m kr_gov_job_mcp.server --call-tool search_public_jobs --input '{\"keyword\":\"정보\",\"limit\":1}'
```

macOS/Linux에서는 다음처럼 실행할 수 있다.

```bash
python -m kr_gov_job_mcp.server
python -m kr_gov_job_mcp.server --health
python -m kr_gov_job_mcp.server --list-tools
python -m kr_gov_job_mcp.server --stdio
python -m kr_gov_job_mcp.server --http --host 0.0.0.0 --port 8000
python -m kr_gov_job_mcp.server --call-tool health_check --input '{}'
```

editable 설치 후에는 콘솔 스크립트도 사용할 수 있다.

```bash
kr-gov-job-mcp --health
```

## 현재 CLI 동작

| 명령 | 목적 |
| --- | --- |
| `python -m kr_gov_job_mcp.server` | 서버 스캐폴드 상태와 등록 도구 목록을 JSON으로 출력 |
| `python -m kr_gov_job_mcp.server --health` | `health_check` 도구를 호출해 readiness JSON 출력 |
| `python -m kr_gov_job_mcp.server --list-tools` | 등록된 도구 정의 목록 출력 |
| `python -m kr_gov_job_mcp.server --stdio` | MCP stdio 서버 실행 |
| `python -m kr_gov_job_mcp.server --http --host 0.0.0.0 --port 8000` | MCP HTTP POST 엔드포인트 실행 |
| `python -m kr_gov_job_mcp.server --call-tool NAME --input '{}'` | 도구 호출 구조 smoke test |

## MCP stdio 연결 예시

Claude Desktop, Cursor, Codex MCP 클라이언트처럼 stdio transport를 지원하는 로컬 클라이언트에는
다음 설정으로 연결한다.

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

stdio 모드는 표준 입력에서 newline-delimited JSON-RPC 메시지를 읽고 표준 출력으로 MCP 응답만
쓴다. 로그가 필요하면 표준 에러를 사용한다.

## MCP HTTP / Docker 배포

Git source build나 Kubernetes 배포처럼 컨테이너가 독립 프로세스로 떠야 하는 환경에서는 HTTP
모드를 사용한다.

```bash
python -m kr_gov_job_mcp.server --http --host 0.0.0.0 --port 8000
```

현재 HTTP 모드는 `/mcp`에서 JSON-RPC POST 요청을 처리하고 `/health`에서 readiness JSON을
반환한다. SSE GET stream과 session resume은 아직 구현하지 않았다.

루트 `Dockerfile`은 이 HTTP 모드를 기본 실행한다. Git 소스 빌드 등록값은 다음처럼 둔다.

| 항목 | 값 |
| --- | --- |
| MCP 서버 이름 | `kr-gov-job-mcp` |
| Git URL | `https://github.com/yt010108/kr-gov-job-mcp.git` |
| 브랜치 / ref | `main` |
| Dockerfile 경로 | `Dockerfile` |
| PAT | 공개 저장소라면 비워둠 |

로컬 Docker smoke test:

```bash
docker build -t kr-gov-job-mcp .
docker run --rm -p 8000:8000 kr-gov-job-mcp
curl http://localhost:8000/health
```

## 도구 등록 구조

도구는 `ToolDefinition`으로 정의하고 `ToolRegistry`에 등록한다.

```python
from kr_gov_job_mcp.tools import ToolDefinition, ToolRegistry

registry = ToolRegistry()
registry.register(
    ToolDefinition(
        name="example_tool",
        description="Example callable tool.",
        input_schema={"type": "object", "properties": {}},
        handler=lambda arguments: {"ok": True},
    )
)
```

기본 레지스트리는 `create_default_registry()`로 생성한다.
현재 기본 등록 도구는 `health_check`, `lookup_region_codes`, `search_public_jobs`,
`fetch_job_detail`, `collect_institution_context`, `analyze_job_fit_report`,
`analyze_institution_strategy`, `analyze_institution_weakness`다.

## smoke test

현재 서버 스캐폴드의 최소 확인 기준:

```bash
python -m kr_gov_job_mcp.server --health
python -m kr_gov_job_mcp.server --list-tools
python -m kr_gov_job_mcp.server --http --host 127.0.0.1 --port 8000
python -m pytest -q
```

예상 health 응답:

```json
{"registered_tools":8,"service":"kr-gov-job-mcp","status":"ok","version":"0.1.0"}
```
