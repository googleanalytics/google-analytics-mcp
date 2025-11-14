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

from mcp.server.auth.handlers.metadata import (
    ProtectedResourceMetadataHandler,
)
from mcp.server.auth.routes import cors_middleware
from mcp.server.fastmcp import FastMCP
from mcp.shared.auth import ProtectedResourceMetadata

from analytics_mcp.auth import GoogleTokenVerifier
from analytics_mcp.settings import FastMcpSettings


def _create_mcp_server() -> FastMCP:
    settings = FastMcpSettings()
    token_verifier = None
    if settings.auth is not None:
        token_verifier = GoogleTokenVerifier(
            required_scopes=settings.auth.required_scopes
        )
    settings_dict = settings.model_dump()
    mcp = FastMCP(
        "Google Analytics MCP Server",
        token_verifier=token_verifier,
        **settings_dict,
    )
    if mcp.settings.auth and mcp.settings.auth.resource_server_url:
        protected_resource_metadata = ProtectedResourceMetadata(
            resource=mcp.settings.auth.resource_server_url,
            authorization_servers=(
                [mcp.settings.auth.issuer_url]
                if mcp.settings.auth.issuer_url
                else []
            ),
            scopes_supported=mcp.settings.auth.required_scopes,
        )

        handler = cors_middleware(
            ProtectedResourceMetadataHandler(
                protected_resource_metadata
            ).handle,
            ["GET", "OPTIONS"],
        )

        mcp.custom_route(
            f"{mcp.settings.sse_path.rstrip('/')}/.well-known/oauth-protected-resource",
            methods=["GET", "OPTIONS"],
        )(handler)
        mcp.custom_route(
            f"{mcp.settings.streamable_http_path.rstrip('/')}/.well-known/oauth-protected-resource",
            methods=["GET", "OPTIONS"],
        )(handler)
    return mcp


mcp = _create_mcp_server()
