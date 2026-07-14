import pytest

from kr_gov_job_mcp.runtime import deployment_metadata


_DEPLOYMENT_ENV_NAMES = ("APP_SOURCE_REF", "APP_REVISION", "GIT_REF", "GIT_COMMIT")


def test_deployment_metadata_defaults_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _DEPLOYMENT_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)

    assert deployment_metadata() == {
        "version": "0.1.0",
        "source_ref": "unknown",
        "revision": "unknown",
    }


def test_deployment_metadata_prefers_app_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SOURCE_REF", " refs/heads/main ")
    monkeypatch.setenv("APP_REVISION", "257e45c-full")
    monkeypatch.setenv("GIT_REF", "fallback-ref")
    monkeypatch.setenv("GIT_COMMIT", "fallback-commit")

    result = deployment_metadata()

    assert result["source_ref"] == "refs/heads/main"
    assert result["revision"] == "257e45c-full"


def test_deployment_metadata_uses_git_fallbacks_for_blank_app_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_SOURCE_REF", "  ")
    monkeypatch.setenv("APP_REVISION", "")
    monkeypatch.setenv("GIT_REF", "refs/tags/v0.1.0")
    monkeypatch.setenv("GIT_COMMIT", "abcdef123456")

    result = deployment_metadata()

    assert result["source_ref"] == "refs/tags/v0.1.0"
    assert result["revision"] == "abcdef123456"
