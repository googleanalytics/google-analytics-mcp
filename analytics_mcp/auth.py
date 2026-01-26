import logging
import time
import typing
from collections.abc import Callable
from typing import Any, Final, Literal

import httpx
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.provider import TokenVerifier as _SDKTokenVerifier
from pydantic import BaseModel

HTTP_TIMEOUT_SECONDS: Final[float] = 5.0


class TokenVerifyResponse(BaseModel):
    issued_to: str
    audience: str
    scope: str
    expires_in: int | None = None
    access_type: str | None = None
    token: str | None = None


class TokenVerifyRequest(BaseModel):
    access_token: str


class TokenVerifier(_SDKTokenVerifier):
    url: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    auth: httpx.Auth | None = None
    required_scopes: set[str]
    content_type: Literal[
        "application/json", "application/x-www-form-urlencoded"
    ]

    def __init__(
        self,
        url: str,
        auth: httpx.Auth | None = None,
        method: Literal[
            "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
        ] = "GET",
        required_scopes: list[str] | None = None,
        content_type: Literal[
            "application/json", "application/x-www-form-urlencoded"
        ]
        | None = None,
    ) -> None:
        super().__init__()
        self.url = url
        self.method = method
        self.auth = auth
        self.required_scopes = set(required_scopes or [])
        self.content_type = content_type or "application/json"

    def _to_request_kwargs(self, request_data: BaseModel) -> dict[str, Any]:
        json_data = request_data.model_dump(exclude_none=True)
        if self.method in {"GET", "DELETE", "OPTIONS"}:
            return {"params": json_data}
        elif self.method in {"POST", "PUT", "PATCH"}:
            if self.content_type == "application/json":
                return {"json": json_data}
            elif self.content_type == "application/x-www-form-urlencoded":
                return {"data": json_data}
        else:
            raise ValueError(f"Unsupported HTTP method: {self.method}")

    async def verify_token(self, token: str) -> AccessToken | None:
        now = int(time.time())
        try:
            async with httpx.AsyncClient(
                auth=self.auth,
                timeout=HTTP_TIMEOUT_SECONDS,
            ) as client:
                response = await client.request(
                    self.method,
                    self.url,
                    **self._to_request_kwargs(
                        TokenVerifyRequest(access_token=token)
                    ),
                )
                response.raise_for_status()
                logging.debug("Token verified successfully")
                token_info = TokenVerifyResponse.model_validate(response.json())
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logging.error(f"HTTP error during token verification: {str(e)}")
            return None

        scopes = (token_info.scope or "").split()

        expires_at = None
        if token_info.expires_in is not None:
            expires_at = now + token_info.expires_in

        return AccessToken(
            token=token_info.token or token,
            client_id=token_info.audience,
            expires_at=expires_at,
            scopes=scopes,
        )


class BearerAuth(httpx.Auth):
    token_provider: Callable[[], str]

    def __init__(self, token_provider: Callable[[], str]) -> None:
        self.token_provider = token_provider

    def auth_flow(
        self, request: httpx.Request
    ) -> typing.Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self.token_provider()}"
        yield request
