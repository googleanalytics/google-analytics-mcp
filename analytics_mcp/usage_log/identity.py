from __future__ import annotations

from dataclasses import dataclass

from fastmcp.server.dependencies import get_access_token


@dataclass(frozen=True)
class Identity:
    sub: str
    email: str | None


def read_identity() -> Identity | None:
    token = get_access_token()
    claims = token.claims if token else {}
    sub = claims.get("sub")
    if not sub:
        return None
    email = claims.get("email")
    return Identity(sub=str(sub), email=str(email) if email else None)
