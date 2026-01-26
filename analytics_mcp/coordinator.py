# Copyright 2025 Google LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module declaring the singleton MCP instance.

The singleton allows other modules to register their tools with the same MCP
server using `@mcp.tool` annotations, thereby 'coordinating' the bootstrapping
of the server.
"""

from typing import Literal

import httpx
from mcp.server.fastmcp import FastMCP

from analytics_mcp.auth import BearerAuth, TokenVerifier
from analytics_mcp.jwt import JWTProvider
from analytics_mcp.settings import (
    BasicAuthSettings,
    BearerAuthSettings,
    FastMcpSettings,
    JwtProviderSettings,
)


def _create_jwt_provider() -> JWTProvider:
    from joserfc import jwk

    settings = JwtProviderSettings()  # type: ignore[call-arg]
    if not settings.private_keys or settings.algorithm is None:
        raise ValueError(
            "JWTProvider cannot be created without private keys and algorithm."
        )

    private_keys = jwk.KeySet.import_key_set(
        {"keys": settings.private_keys}
    )

    return JWTProvider(
        private_keys=private_keys,
        algorithm=settings.algorithm,
        claims=settings.claims,
        token_lifetime=settings.token_lifetime,
    )


def _create_bearer_auth() -> httpx.Auth:
    settings = BearerAuthSettings()
    if settings.token is not None:
        token = settings.token.get_secret_value()
        return BearerAuth(token_provider=lambda: token)
    else:
        return BearerAuth(token_provider=_create_jwt_provider())


def _create_basic_auth() -> httpx.Auth:
    settings: BasicAuthSettings = BasicAuthSettings()  # type: ignore[call-arg]
    return httpx.BasicAuth(
        username=settings.username,
        password=settings.password.get_secret_value(),
    )


def _create_auth(type: Literal["bearer", "basic", "none"]) -> httpx.Auth | None:
    if type == "bearer":
        return _create_bearer_auth()
    elif type == "basic":
        return _create_basic_auth()
    elif type == "none":
        return None
    else:
        raise ValueError(f"Unsupported auth type: {type}")


def _create_token_verifier(
    required_scopes: list[str] | None = None
) -> TokenVerifier:
    from analytics_mcp.settings import TokenVerifierSettings

    settings = TokenVerifierSettings(required_scopes=required_scopes)
    return TokenVerifier(
        auth=_create_auth(settings.auth),
        url=settings.url,
        method=settings.method,
        required_scopes=settings.required_scopes,
        content_type=settings.content_type,
    )


def _create_mcp_server() -> FastMCP:
    settings = FastMcpSettings()
    token_verifier = None
    if settings.auth is not None:
        token_verifier = _create_token_verifier(settings.auth.required_scopes)
    settings_dict = settings.model_dump()
    mcp = FastMCP(
        "Google Analytics MCP Server",
        token_verifier=token_verifier,
        **settings_dict,
    )
    return mcp


mcp = _create_mcp_server()
