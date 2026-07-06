"""In-process tool registry used by the server scaffold."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


ToolHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class ToolDefinition:
    """Description and handler for one callable MCP-style tool."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    handler: ToolHandler | None = field(default=None, repr=False, compare=False)

    def public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    """Register, list, and call tools through a small stable interface."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if not tool.name:
            raise ValueError("tool name is required")
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.public_dict() for tool in sorted(self._tools.values(), key=lambda item: item.name)]

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def call(self, name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
        tool = self.get(name)
        if tool.handler is None:
            raise ValueError(f"tool is not callable: {name}")
        return dict(tool.handler(arguments or {}))
