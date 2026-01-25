import logging
from typing import Any, Final, Literal

import httpx
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.provider import TokenVerifier as _SDKTokenVerifier
from pydantic import BaseModel

HTTP_TIMEOUT_SECONDS: Final[float] = 5.0


class TokenVerifyResponse(BaseModel):
    client_id: str
    token: str
    scopes: list[str]
    expires_at: int | None = None


class TokenVerifyRequest(BaseModel):
    access_token: str


class TokenVerifier(_SDKTokenVerifier):
    url: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    auth: httpx.Auth | None = None
    required_scopes: set[str]
    content_type:Literal["application/json", "application/x-www-form-urlencoded"]

    def __init__(
        self,
        url: str,
        auth: httpx.Auth | None = None,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"] = "GET",
        required_scopes: list[str] | None = None,
        content_type: Literal["application/json", "application/x-www-form-urlencoded"] | None = None,
    ) -> None:
        super().__init__()
        self.url = url
        self.method = method
        self.auth = auth
        self.required_scopes = set(required_scopes or [])
        self.content_type = content_type or "application/json"

    def _to_request_kwargs(
        self, request_data: BaseModel
    ) -> dict[str, Any]:
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
                token_info = TokenVerifyResponse.model_validate(
                    response.json()
                )
        except httpx.RequestError as e:
            logging.error(f"HTTP error during token verification: {e}")
            return None

        missing_scopes = self.required_scopes.difference(token_info.scopes)
        if missing_scopes:
            logging.debug(
                f"Token is missing required scopes: {missing_scopes}"
            )
            return None
        return AccessToken(
            token=token_info.token,
            client_id=token_info.client_id,
            expires_at=token_info.expires_at,
            scopes=token_info.scopes,
        )
