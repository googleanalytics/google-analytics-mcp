import logging
import time
from typing import Any, Final

import httpx
from mcp.server.auth.provider import AccessToken, TokenVerifier

GOOGLE_TOKEN_VERIFICATION_ENDPOINT: Final[str] = (
    "https://www.googleapis.com/oauth2/v1/tokeninfo"
)
HTTP_TIMEOUT_SECONDS: Final[float] = 5.0


class GoogleTokenVerifier(TokenVerifier):
    required_scopes: list[str]

    def __init__(self, required_scopes: list[str] | None = None) -> None:
        super().__init__()
        self.required_scopes = required_scopes or []

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            async with httpx.AsyncClient(
                timeout=HTTP_TIMEOUT_SECONDS
            ) as client:
                response = await client.get(
                    GOOGLE_TOKEN_VERIFICATION_ENDPOINT,
                    params={"access_token": token},
                )
                if response.status_code != 200:
                    logging.debug(f"Token verification failed: {response.text}")
                    return None
                logging.debug("Token verified successfully")
                token_info: dict[str, Any] = response.json()
                expires_in = int(token_info.get("expires_in", 0))
                if expires_in <= 0:
                    logging.debug("Token has expired")
                    return None

                expires_at = int(time.time()) + expires_in
                scope_str: str = token_info.get("scope", "")
                scopes = [
                    scope.strip()
                    for scope in scope_str.split(" ")
                    if scope.strip()
                ]
                rscopes = set(self.required_scopes)
                missing_scopes = rscopes.difference(scopes)
                if missing_scopes:
                    logging.debug(
                        f"Token is missing required scopes: {missing_scopes}"
                    )
                    return None
                return AccessToken(
                    token=token,
                    client_id=token_info.get("audience", ""),
                    expires_at=expires_at,
                    scopes=scopes,
                )
        except httpx.RequestError as e:
            logging.error(f"HTTP error during token verification: {e}")
            return None
