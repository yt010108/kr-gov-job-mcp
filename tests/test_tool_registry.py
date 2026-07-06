import pytest

from kr_gov_job_mcp.tools import ToolDefinition, ToolRegistry, create_default_registry


def test_default_registry_exposes_health_check() -> None:
    registry = create_default_registry()

    tools = registry.list_tools()

    assert tools == [
        {
            "name": "health_check",
            "description": "Return basic server readiness and registry metadata.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        }
    ]


def test_health_check_returns_server_metadata() -> None:
    registry = create_default_registry()

    result = registry.call("health_check")

    assert result == {
        "status": "ok",
        "service": "kr-gov-job-mcp",
        "version": "0.1.0",
        "registered_tools": 1,
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
