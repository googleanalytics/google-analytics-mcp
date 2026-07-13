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

"""FastMCP-based coordinator with streamable-http and OAuth support.

This replaces the low-level MCP SDK coordinator for remote deployments.
Modeled after the Google Ads MCP server pattern.
"""

import os
import json
import logging
import sys

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

logger = logging.getLogger(__name__)

# --- OAuth Configuration (optional, enables streamable-http) ---
_CLIENT_ID = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_ID")
_CLIENT_SECRET = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_SECRET")
_BASE_URL = os.environ.get("ANALYTICS_MCP_BASE_URL", "http://localhost:8080")

if _CLIENT_ID and _CLIENT_SECRET:
    from fastmcp.server.auth.providers.google import GoogleProvider

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
    logger.info("OAuth enabled — streamable-http mode available")
else:
    mcp = FastMCP("Google Analytics MCP Server")
    logger.info("No OAuth credentials — stdio mode only")


# --- Tool Registration ---
# All tools are read-only. We annotate each one explicitly.

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

_READONLY = ToolAnnotations(readOnlyHint=True)


# --- Simple tools (no custom descriptions needed) ---

@mcp.tool(annotations=_READONLY)
async def get_account_summaries_tool() -> str:
    """Retrieves information about the user's Google Analytics accounts and properties."""
    result = await get_account_summaries()
    return json.dumps(result, indent=2)


@mcp.tool(name="list_google_ads_links", annotations=_READONLY)
async def list_google_ads_links_tool(property_id: str) -> str:
    """Returns a list of links to Google Ads accounts for a property.

    Args:
        property_id: The Google Analytics property ID (number or 'properties/NUMBER').
    """
    result = await list_google_ads_links(property_id)
    return json.dumps(result, indent=2)


@mcp.tool(name="get_property_details", annotations=_READONLY)
async def get_property_details_tool(property_id: str) -> str:
    """Returns details about a Google Analytics property.

    Args:
        property_id: The Google Analytics property ID (number or 'properties/NUMBER').
    """
    result = await get_property_details(property_id)
    return json.dumps(result, indent=2)


@mcp.tool(name="list_property_annotations", annotations=_READONLY)
async def list_property_annotations_tool(property_id: str) -> str:
    """Returns annotations for a property. Annotations are notes on GA4 for specific dates.

    Args:
        property_id: The Google Analytics property ID (number or 'properties/NUMBER').
    """
    result = await list_property_annotations(property_id)
    return json.dumps(result, indent=2)


@mcp.tool(name="get_custom_dimensions_and_metrics", annotations=_READONLY)
async def get_custom_dimensions_and_metrics_tool(property_id: str) -> str:
    """Retrieves the custom dimensions and metrics for a specific property.

    Args:
        property_id: The Google Analytics property ID (number or 'properties/NUMBER').
    """
    result = await get_custom_dimensions_and_metrics(property_id)
    return json.dumps(result, indent=2)


# --- Complex reporting tools (with generated descriptions) ---

@mcp.tool(
    name="run_report",
    description=_run_report_description(),
    annotations=_READONLY,
)
async def run_report_tool(
    property_id: str,
    date_ranges: list,
    dimensions: list,
    metrics: list,
    dimension_filter: dict = None,
    metric_filter: dict = None,
    order_bys: list = None,
    limit: int = None,
    offset: int = None,
    currency_code: str = None,
    return_property_quota: bool = False,
) -> str:
    result = await run_report(
        property_id=property_id,
        date_ranges=date_ranges,
        dimensions=dimensions,
        metrics=metrics,
        dimension_filter=dimension_filter,
        metric_filter=metric_filter,
        order_bys=order_bys,
        limit=limit,
        offset=offset,
        currency_code=currency_code,
        return_property_quota=return_property_quota,
    )
    return json.dumps(result, indent=2)


@mcp.tool(
    name="run_realtime_report",
    description=_run_realtime_report_description(),
    annotations=_READONLY,
)
async def run_realtime_report_tool(
    property_id: str,
    dimensions: list,
    metrics: list,
    dimension_filter: dict = None,
    metric_filter: dict = None,
    order_bys: list = None,
    limit: int = None,
    offset: int = None,
    return_property_quota: bool = False,
) -> str:
    result = await run_realtime_report(
        property_id=property_id,
        dimensions=dimensions,
        metrics=metrics,
        dimension_filter=dimension_filter,
        metric_filter=metric_filter,
        order_bys=order_bys,
        limit=limit,
        offset=offset,
        return_property_quota=return_property_quota,
    )
    return json.dumps(result, indent=2)


@mcp.tool(
    name="run_funnel_report",
    description=_run_funnel_report_description(),
    annotations=_READONLY,
)
async def run_funnel_report_tool(
    property_id: str,
    funnel_steps: list,
    date_ranges: list = None,
    funnel_breakdown: dict = None,
    funnel_next_action: dict = None,
    segments: list = None,
    return_property_quota: bool = False,
) -> str:
    result = await run_funnel_report(
        property_id=property_id,
        funnel_steps=funnel_steps,
        date_ranges=date_ranges,
        funnel_breakdown=funnel_breakdown,
        funnel_next_action=funnel_next_action,
        segments=segments,
        return_property_quota=return_property_quota,
    )
    return json.dumps(result, indent=2)


@mcp.tool(
    name="run_conversions_report",
    description=_run_conversions_report_description(),
    annotations=_READONLY,
)
async def run_conversions_report_tool(
    property_id: str,
    date_ranges: list,
    dimensions: list,
    metrics: list,
    conversion_spec: dict,
    dimension_filter: dict = None,
    metric_filter: dict = None,
    order_bys: list = None,
    limit: int = None,
    offset: int = None,
    currency_code: str = None,
    return_property_quota: bool = False,
) -> str:
    result = await run_conversions_report(
        property_id=property_id,
        date_ranges=date_ranges,
        dimensions=dimensions,
        metrics=metrics,
        conversion_spec=conversion_spec,
        dimension_filter=dimension_filter,
        metric_filter=metric_filter,
        order_bys=order_bys,
        limit=limit,
        offset=offset,
        currency_code=currency_code,
        return_property_quota=return_property_quota,
    )
    return json.dumps(result, indent=2)
