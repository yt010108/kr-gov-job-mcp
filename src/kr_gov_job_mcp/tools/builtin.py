"""Built-in tools available before source-specific tools are implemented."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp import __version__
from kr_gov_job_mcp.tools.registry import ToolDefinition, ToolRegistry


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def health_check(_arguments: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "kr-gov-job-mcp",
            "version": __version__,
            "registered_tools": len(registry.list_tools()),
        }

    registry.register(
        ToolDefinition(
            name="health_check",
            description="Return basic server readiness and registry metadata.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            handler=health_check,
        )
    )
    return registry
