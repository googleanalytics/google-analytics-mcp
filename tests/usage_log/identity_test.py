"""Covers runbook tests 8-9 (phase-2-middleware.md 2.11).
A missing email still yields an identity; a missing sub yields none at all,
because user_sub is NOT NULL and a placeholder would read as a real person."""

import analytics_mcp.usage_log.identity as identity_module
from analytics_mcp.usage_log.identity import read_identity


class FakeToken:
    def __init__(self, claims):
        self.claims = claims


def _with_token(monkeypatch, token):
    monkeypatch.setattr(identity_module, "get_access_token", lambda: token)


def test_reads_sub_and_email(monkeypatch):
    _with_token(monkeypatch, FakeToken({"sub": "1234", "email": "piotr@touchpoint.agency"}))
    identity = read_identity()
    assert identity == identity_module.Identity(sub="1234", email="piotr@touchpoint.agency")


def test_missing_email_still_yields_identity(monkeypatch):
    _with_token(monkeypatch, FakeToken({"sub": "1234", "email": None}))
    identity = read_identity()
    assert identity is not None
    assert identity.sub == "1234"
    assert identity.email is None


def test_missing_sub_yields_no_identity(monkeypatch):
    _with_token(monkeypatch, FakeToken({"email": "piotr@touchpoint.agency"}))
    assert read_identity() is None


def test_absent_token_yields_no_identity(monkeypatch):
    _with_token(monkeypatch, None)
    assert read_identity() is None
