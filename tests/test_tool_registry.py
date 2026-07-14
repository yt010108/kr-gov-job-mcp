import pytest

from kr_gov_job_mcp.tools import ToolDefinition, ToolRegistry, create_default_registry


def test_default_registry_exposes_health_check() -> None:
    registry = create_default_registry()

    tools = registry.list_tools()

    assert [tool["name"] for tool in tools] == [
        "analyze_institution_strategy",
        "analyze_institution_weakness",
        "analyze_job_fit_report",
        "fetch_job_detail",
        "health_check",
        "lookup_job_alio_codes",
        "lookup_region_codes",
        "map_ncs_competencies",
        "prepare_application_strategy",
        "prepare_institution_interview",
        "resolve_ncs_code",
        "search_public_jobs",
    ]
    assert tools[4] == {
        "name": "health_check",
        "description": "kr-gov-job-mcp 서비스에서 서버 준비 상태와 등록된 도구 개수 같은 기본 메타데이터를 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "annotations": {
            "title": "Health Check",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    }
    assert tools[0]["input_schema"]["additionalProperties"] is False
    assert tools[1]["input_schema"]["additionalProperties"] is False
    assert tools[2]["input_schema"]["additionalProperties"] is False
    assert tools[3]["input_schema"]["additionalProperties"] is False
    assert tools[4]["input_schema"]["additionalProperties"] is False
    assert tools[5]["input_schema"]["additionalProperties"] is False
    assert tools[6]["input_schema"]["additionalProperties"] is False
    assert tools[7]["input_schema"]["additionalProperties"] is False
    assert tools[8]["input_schema"]["additionalProperties"] is False
    assert tools[9]["input_schema"]["additionalProperties"] is False
    assert tools[10]["input_schema"]["additionalProperties"] is False
    assert tools[11]["input_schema"]["additionalProperties"] is False


def test_default_registry_tool_metadata_satisfies_review_requirements() -> None:
    registry = create_default_registry()

    tools = registry.list_tools()

    for tool in tools:
        assert "kr-gov-job-mcp" in tool["description"]
        assert tool["annotations"]["title"]
        assert tool["annotations"]["readOnlyHint"] is True
        assert tool["annotations"]["destructiveHint"] is False
        assert tool["annotations"]["idempotentHint"] is True
        assert isinstance(tool["annotations"]["openWorldHint"], bool)


def test_health_check_returns_server_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SOURCE_REF", "refs/heads/main")
    monkeypatch.setenv("APP_REVISION", "257e45c")
    registry = create_default_registry()

    result = registry.call("health_check")

    assert result == {
        "status": "ok",
        "service": "kr-gov-job-mcp",
        "version": "0.1.0",
        "source_ref": "refs/heads/main",
        "revision": "257e45c",
        "registered_tools": 12,
    }


def test_registry_rejects_duplicate_tool_names() -> None:
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="example",
        description="Example tool.",
        input_schema={"type": "object"},
        handler=lambda _arguments: {"ok": True},
    )

    registry.register(tool)

    with pytest.raises(ValueError, match="tool already registered"):
        registry.register(tool)


def test_registry_calls_named_tool_with_arguments() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="echo",
            description="Echo input.",
            input_schema={"type": "object"},
            handler=lambda arguments: {"arguments": dict(arguments)},
        )
    )

    assert registry.call("echo", {"keyword": "보안"}) == {"arguments": {"keyword": "보안"}}
