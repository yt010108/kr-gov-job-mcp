"""Command-line entry point for the kr-gov-job-mcp server scaffold."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any, TextIO

from kr_gov_job_mcp.mcp_http import run_http_server
from kr_gov_job_mcp.mcp_stdio import run_stdio_server
from kr_gov_job_mcp.tools import ToolRegistry, create_default_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run or inspect the kr-gov-job-mcp server scaffold.")
    parser.add_argument(
        "--health",
        action="store_true",
        help="Run the built-in health_check tool and print JSON.",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="Print the registered tool definitions as JSON.",
    )
    parser.add_argument(
        "--call-tool",
        metavar="NAME",
        help="Call a registered tool by name and print JSON.",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run the MCP stdio server using newline-delimited JSON-RPC messages.",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run the MCP Streamable HTTP server.",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Host for --http mode. Defaults to HOST or 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_default_port(),
        help="Port for --http mode. Defaults to PORT or 8000.",
    )
    parser.add_argument(
        "--input",
        default="{}",
        help="JSON object passed as tool arguments when using --call-tool.",
    )
    return parser


def run_command(
    args: argparse.Namespace,
    *,
    registry: ToolRegistry,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    if args.stdio:
        return run_stdio_server(registry, stdin=stdin, stdout=stdout, stderr=stderr)

    if args.http:
        return run_http_server(registry, host=args.host, port=args.port)

    if args.list_tools:
        _write_json({"tools": registry.list_tools()}, stdout)
        return 0

    if args.health:
        _write_json(registry.call("health_check"), stdout)
        return 0

    if args.call_tool:
        try:
            arguments = _loads_json_object(args.input)
            result = registry.call(args.call_tool, arguments)
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            print(str(exc), file=stderr)
            return 2
        _write_json(result, stdout)
        return 0

    _write_json(
        {
            "status": "ready",
            "service": "kr-gov-job-mcp",
            "tools": registry.list_tools(),
        },
        stdout,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    registry = create_default_registry()
    return run_command(args, registry=registry, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


def _loads_json_object(value: str) -> Mapping[str, Any]:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("--input must be a JSON object")
    return payload


def _default_port() -> int:
    value = os.environ.get("PORT", "8000")
    try:
        return int(value)
    except ValueError:
        return 8000


def _write_json(payload: Mapping[str, Any], stdout: TextIO) -> None:
    stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
