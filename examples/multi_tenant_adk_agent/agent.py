# Copyright 2026 Google LLC All Rights Reserved.
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

"""Example multi-tenant ADK agent with interactive Google OAuth 2.0 sign-in.

End users interacting with this agent (e.g., via `adk web` or Vertex AI Agent
Engine) are automatically prompted with a "Sign in" button in the chat UI to
authorize access to their own Google Analytics properties.
"""

import os

from fastapi.openapi.models import (
    OAuth2,
    OAuthFlowAuthorizationCode,
    OAuthFlows,
)
from google.adk.agents import LlmAgent
from google.adk.auth.auth_credential import (
    AuthCredential,
    AuthCredentialTypes,
    OAuth2Auth,
)
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

ANALYTICS_MCP_URL = os.environ.get(
    "ANALYTICS_MCP_URL", "http://127.0.0.1:8080/mcp"
)
ANALYTICS_MCP_ALLOW_WRITE = os.environ.get(
    "ANALYTICS_MCP_ALLOW_WRITE", ""
).lower() in ("1", "true", "yes")
GOOGLE_OAUTH_CLIENT_ID = os.environ.get(
    "GOOGLE_OAUTH_CLIENT_ID", "YOUR_GOOGLE_OAUTH_CLIENT_ID"
)
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get(
    "GOOGLE_OAUTH_CLIENT_SECRET", "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
)


def create_google_analytics_toolset(
    mcp_url: str = ANALYTICS_MCP_URL,
    client_id: str = GOOGLE_OAUTH_CLIENT_ID,
    client_secret: str = GOOGLE_OAUTH_CLIENT_SECRET,
    allow_write: bool = False,
) -> McpToolset:
    """Creates a multi-tenant Google Analytics McpToolset with end-user OAuth."""
    scopes = {
        "https://www.googleapis.com/auth/analytics.readonly": (
            "View your Google Analytics data"
        ),
    }
    if allow_write:
        scopes["https://www.googleapis.com/auth/analytics.edit"] = (
            "Edit Google Analytics management entities (such as annotations)"
        )

    auth_scheme = OAuth2(
        flows=OAuthFlows(
            authorizationCode=OAuthFlowAuthorizationCode(
                authorizationUrl="https://accounts.google.com/o/oauth2/v2/auth",
                tokenUrl="https://oauth2.googleapis.com/token",
                scopes=scopes,
            )
        )
    )
    auth_credential = AuthCredential(
        auth_type=AuthCredentialTypes.OAUTH2,
        oauth2=OAuth2Auth(
            client_id=client_id,
            client_secret=client_secret,
        ),
    )

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=mcp_url),
        auth_scheme=auth_scheme,
        auth_credential=auth_credential,
    )


ga_mcp_toolset = create_google_analytics_toolset(
    allow_write=ANALYTICS_MCP_ALLOW_WRITE
)

# Note: You can combine multiple MCP servers from different providers (e.g.,
# Google Analytics MCP + Meta Ads MCP) in the same agent. Each McpToolset
# carries its own independent `auth_scheme` and `auth_credential`, so ADK
# prompts the end user to sign in to each provider separately and sends each
# token only to its corresponding MCP server.
root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="google_analytics_assistant",
    instruction=(
        "You are a helpful data analyst assistant that can access the user's "
        "Google Analytics data via the provided MCP tools. Help the user "
        "understand and analyze their analytics data."
    ),
    tools=[ga_mcp_toolset],
)
