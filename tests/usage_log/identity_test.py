"""A missing email still yields an identity; a missing sub yields none at all,
because user_sub is NOT NULL and a placeholder would read as a real person."""

import httpx
import pytest

from analytics_mcp.usage_log.identity import (
    Identity,
    IdentityLookupError,
    IdentityResolver,
    read_identity,
)

CLAIMS = {"sub": "1234", "email": "piotr@touchpoint.agency"}


def test_reads_sub_and_email():
    assert read_identity(CLAIMS) == Identity(
        sub="1234", email="piotr@touchpoint.agency"
    )


def test_missing_email_still_yields_identity():
    identity = read_identity({"sub": "1234", "email": None})
    assert identity == Identity(sub="1234", email=None)


def test_missing_sub_yields_no_identity():
    assert read_identity({"email": "piotr@touchpoint.agency"}) is None


def _resolver(handler) -> IdentityResolver:
    return IdentityResolver(
        httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


async def test_resolves_identity_from_userinfo():
    seen_headers = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers["authorization"])
        return httpx.Response(200, json=CLAIMS)

    identity = await _resolver(handler).resolve("ya29.token")

    assert identity == Identity(sub="1234", email="piotr@touchpoint.agency")
    assert seen_headers == ["Bearer ya29.token"]


async def test_looks_each_token_up_once():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=CLAIMS)

    resolver = _resolver(handler)
    first = await resolver.resolve("ya29.token")
    second = await resolver.resolve("ya29.token")

    assert first == second
    assert len(requests) == 1


async def test_rejected_token_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_token"})

    with pytest.raises(IdentityLookupError, match="401"):
        await _resolver(handler).resolve("ya29.expired")
