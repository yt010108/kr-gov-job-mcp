"""Built-in tools available before source-specific tools are implemented."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kr_gov_job_mcp.runtime import deployment_metadata
from kr_gov_job_mcp.tools.code_lookup import (
    create_lookup_job_alio_codes_tool,
    create_lookup_region_codes_tool,
)
from kr_gov_job_mcp.tools.institution_analysis import (
    create_analyze_institution_strategy_tool,
    create_analyze_institution_weakness_tool,
    create_prepare_institution_interview_tool,
)
from kr_gov_job_mcp.tools.public_jobs import (
    create_analyze_job_fit_report_tool,
    create_fetch_job_detail_tool,
    create_search_public_jobs_tool,
)
from kr_gov_job_mcp.tools.star_answer import create_generate_star_answer_framework_tool
from kr_gov_job_mcp.tools.registry import ToolDefinition, ToolRegistry, read_only_tool_annotations


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def health_check(_arguments: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "kr-gov-job-mcp",
            "registered_tools": len(registry.list_tools()),
            **deployment_metadata(),
        }

    registry.register(
        ToolDefinition(
            name="health_check",
            description="kr-gov-job-mcp 서비스에서 서버 준비 상태와 등록된 도구 개수 같은 기본 메타데이터를 반환합니다.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            annotations=read_only_tool_annotations("Health Check", open_world=False),
            handler=health_check,
        )
    )
    registry.register(create_lookup_job_alio_codes_tool())
    registry.register(create_lookup_region_codes_tool())
    registry.register(create_analyze_institution_strategy_tool())
    registry.register(create_analyze_institution_weakness_tool())
    registry.register(create_prepare_institution_interview_tool())
    registry.register(create_analyze_job_fit_report_tool())
    registry.register(create_generate_star_answer_framework_tool())
    registry.register(create_fetch_job_detail_tool())
    registry.register(create_search_public_jobs_tool())
    return registry
