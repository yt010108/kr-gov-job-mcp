"""Runtime metadata helpers for deployment verification."""

from __future__ import annotations

import os

from kr_gov_job_mcp import __version__


def deployment_metadata() -> dict[str, str]:
    """Return version and build identifiers exposed through health checks."""

    return {
        "version": __version__,
        "source_ref": _env_value("APP_SOURCE_REF", "GIT_REF", default="unknown"),
        "revision": _env_value("APP_REVISION", "GIT_COMMIT", default="unknown"),
    }


def _env_value(*names: str, default: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default
