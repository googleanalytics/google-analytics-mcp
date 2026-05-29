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

"""Module declaring the singleton MCP instance."""

import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider

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
_BASE_URL = os.environ.get("ANALYTICS_MCP_BASE_URL", "http://localhost:8080")

if _CLIENT_ID and _CLIENT_SECRET:
    auth = GoogleProvider(
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
        base_url=_BASE_URL,
        required_scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/analytics.readonly",
        ],
    )
    mcp = FastMCP("Google Analytics MCP Server", auth=auth)
else:
    mcp = FastMCP("Google Analytics MCP Server")

mcp.add_tool(get_account_summaries)
mcp.add_tool(list_google_ads_links)
mcp.add_tool(get_property_details)
mcp.add_tool(list_property_annotations)
mcp.add_tool(get_custom_dimensions_and_metrics)
mcp.tool(description=_run_report_description())(run_report)
mcp.tool(description=_run_realtime_report_description())(run_realtime_report)
mcp.tool(description=_run_funnel_report_description())(run_funnel_report)
mcp.tool(description=_run_conversions_report_description())(run_conversions_report)
