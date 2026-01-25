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
from mcp.server.fastmcp import FastMCP

from analytics_mcp.auth import TokenVerifier
from analytics_mcp.settings import FastMcpSettings


def _create_token_verifier(issuer_url: str, required_scopes: list[str] | None = None) -> TokenVerifier:
    from analytics_mcp.settings import TokenVerifierSettings

    settings = TokenVerifierSettings(url=issuer_url, required_scopes=required_scopes)
    return TokenVerifier(
        url=settings.url,
        method=settings.method,
        required_scopes=settings.required_scopes,
        content_type=settings.content_type,
    )


def _create_mcp_server() -> FastMCP:
    settings = FastMcpSettings()
    token_verifier = None
    if settings.auth is not None:
        token_verifier = _create_token_verifier(str(settings.auth.issuer_url), settings.auth.required_scopes)
    settings_dict = settings.model_dump()
    mcp = FastMCP(
        "Google Analytics MCP Server",
        token_verifier=token_verifier,
        **settings_dict,
    )
    return mcp


mcp = _create_mcp_server()
