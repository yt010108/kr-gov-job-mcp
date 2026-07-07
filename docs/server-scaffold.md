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
| `python -m kr_gov_job_mcp.server --call-tool NAME --input '{}'` | 도구 호출 구조 smoke test |

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
현재 기본 등록 도구는 `fetch_job_detail`, `health_check`, `lookup_region_codes`,
`search_public_jobs`다. 이후 `collect_institution_context`, `analyze_job_fit_report` 같은
실제 도구를 이 레지스트리에 붙인다.

## smoke test

현재 서버 스캐폴드의 최소 확인 기준:

```bash
python -m kr_gov_job_mcp.server --health
python -m kr_gov_job_mcp.server --list-tools
python -m pytest -q
```

예상 health 응답:

```json
{"registered_tools":4,"service":"kr-gov-job-mcp","status":"ok","version":"0.1.0"}
```
