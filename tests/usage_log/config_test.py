"""Startup config must fail loudly (phase-2-middleware.md 2.8).
A missing DSN has to stop the server, not produce one that silently
logs nothing — that blind spot is what this project exists to remove."""

import pytest

from analytics_mcp.usage_log.config import DSN_ENV_VAR, read_dsn


def test_returns_the_dsn(monkeypatch):
    monkeypatch.setenv(DSN_ENV_VAR, "postgresql://user@host/db?sslmode=require")
    assert read_dsn() == "postgresql://user@host/db?sslmode=require"


def test_raises_when_unset(monkeypatch):
    monkeypatch.delenv(DSN_ENV_VAR, raising=False)
    with pytest.raises(RuntimeError, match=DSN_ENV_VAR):
        read_dsn()


def test_raises_when_empty(monkeypatch):
    monkeypatch.setenv(DSN_ENV_VAR, "   ")
    with pytest.raises(RuntimeError, match=DSN_ENV_VAR):
        read_dsn()
