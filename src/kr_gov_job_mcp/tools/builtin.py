"""Built-in tools available before source-specific tools are implemented."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp import __version__
from kr_gov_job_mcp.tools.code_lookup import create_lookup_region_codes_tool
from kr_gov_job_mcp.tools.institution_analysis import (
    create_analyze_institution_strategy_tool,
    create_analyze_institution_weakness_tool,
)
from kr_gov_job_mcp.tools.public_jobs import (
    create_analyze_job_fit_report_tool,
    create_fetch_job_detail_tool,
    create_search_public_jobs_tool,
)
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
    registry.register(create_lookup_region_codes_tool())
    registry.register(create_analyze_institution_strategy_tool())
    registry.register(create_analyze_institution_weakness_tool())
    registry.register(create_analyze_job_fit_report_tool())
    registry.register(create_fetch_job_detail_tool())
    registry.register(create_search_public_jobs_tool())
    return registry
