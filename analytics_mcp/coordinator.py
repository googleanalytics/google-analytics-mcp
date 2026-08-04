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

"""Module declaring the singleton MCP server.

The singleton allows other modules to register their tools with the same MCP
server. When OAuth client credentials are provided, the server authenticates
each user with their personal Google account via FastMCP's OAuth proxy
(``GoogleProvider``); every tool call then runs with that user's access token
(see ``analytics_mcp.tools.client``). Without OAuth credentials the server still
starts, but tool calls fail because no access token is available.
"""

import os

from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider

from analytics_mcp.usage_log import UsageLogMiddleware
from analytics_mcp.tools.admin.info import (
    get_account_summaries,
    list_google_ads_links,
    get_property_details,
    list_property_annotations,
)
from analytics_mcp.tools.reporting.core import (
    run_report,
    _run_report_description,
)
from analytics_mcp.tools.reporting.realtime import (
    run_realtime_report,
    _run_realtime_report_description,
)
from analytics_mcp.tools.reporting.metadata import (
    get_custom_dimensions_and_metrics,
)
from analytics_mcp.tools.reporting.funnel import (
    run_funnel_report,
    _run_funnel_report_description,
)
from analytics_mcp.tools.reporting.conversions import (
    run_conversions_report,
    _run_conversions_report_description,
)

_CLIENT_ID = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_ID")
_CLIENT_SECRET = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_SECRET")
_BASE_URL = os.environ.get("ANALYTICS_MCP_BASE_URL", "http://localhost:8000")

# Scopes requested during the OAuth consent flow. ``analytics.readonly`` grants
# read access to the Admin and Data APIs; the identity scopes let the OAuth
# proxy resolve the signed-in user.
_REQUIRED_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/analytics.readonly",
]


def _build_mcp() -> FastMCP:
    """Builds the FastMCP server, enabling OAuth when client creds are set."""
    if _CLIENT_ID and _CLIENT_SECRET:
        auth = GoogleProvider(
            client_id=_CLIENT_ID,
            client_secret=_CLIENT_SECRET,
            base_url=_BASE_URL,
            required_scopes=_REQUIRED_SCOPES,
        )
        mcp = FastMCP("Google Analytics MCP Server", auth=auth)
        mcp.add_middleware(UsageLogMiddleware.from_env(server="google-analytics"))
        return mcp
    return FastMCP("Google Analytics MCP Server")


app = _build_mcp()

# Tools without custom descriptions rely on their docstrings for the schema.
for _tool in (
    get_account_summaries,
    list_google_ads_links,
    get_property_details,
    list_property_annotations,
    get_custom_dimensions_and_metrics,
):
    app.tool(_tool)

# Reporting tools carry generated descriptions with argument hints that are too
# large to keep inline as docstrings.
app.tool(run_report, description=_run_report_description())
app.tool(
    run_realtime_report, description=_run_realtime_report_description()
)
app.tool(run_funnel_report, description=_run_funnel_report_description())
app.tool(
    run_conversions_report,
    description=_run_conversions_report_description(),
)
