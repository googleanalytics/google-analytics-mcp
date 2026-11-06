from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import httpx

GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
MAX_CACHED_IDENTITIES = 10_000


@dataclass(frozen=True)
class Identity:
    sub: str
    email: str | None


class IdentityLookupError(RuntimeError):
    pass


def read_identity(claims: dict[str, Any]) -> Identity | None:
    sub = claims.get("sub")
    if not sub:
        return None
    email = claims.get("email")
    return Identity(sub=str(sub), email=str(email) if email else None)


class IdentityResolver:
    """Looks up the Google account behind an access token.

    The upstream OAuth provider passes Google's access token through as the
    MCP token and records only a hash of it as subject, so the user's sub and
    email are fetched from the OpenID userinfo endpoint, once per token.
    """

    def __init__(
        self, http: httpx.AsyncClient, userinfo_url: str = GOOGLE_USERINFO_URL
    ) -> None:
        self._http = http
        self._userinfo_url = userinfo_url
        self._cache: OrderedDict[str, Identity] = OrderedDict()

    async def resolve(self, access_token: str) -> Identity | None:
        cached = self._cache.get(access_token)
        if cached is not None:
            return cached
        response = await self._http.get(
            self._userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code != 200:
            raise IdentityLookupError(
                f"userinfo lookup failed with HTTP {response.status_code}"
            )
        identity = read_identity(response.json())
        if identity is not None:
            self._remember(access_token, identity)
        return identity

    def _remember(self, access_token: str, identity: Identity) -> None:
        self._cache[access_token] = identity
        while len(self._cache) > MAX_CACHED_IDENTITIES:
            self._cache.popitem(last=False)
