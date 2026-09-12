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

"""Declare and configure the singleton Google Analytics MCP server."""

from collections.abc import Callable
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import Tool
from mcp import types as mcp_types
from mcp.server.subscriptions import InMemorySubscriptionBus, ListenHandler

from analytics_mcp.tools.admin.info import (
    get_account_summaries,
    get_property_details,
    list_google_ads_links,
    list_property_annotations,
)
from analytics_mcp.tools.reporting.conversions import (
    _run_conversions_report_description,
    run_conversions_report,
)
from analytics_mcp.tools.reporting.core import (
    _run_report_description,
    run_report,
)
from analytics_mcp.tools.reporting.funnel import (
    _run_funnel_report_description,
    run_funnel_report,
)
from analytics_mcp.tools.reporting.metadata import (
    get_custom_dimensions_and_metrics,
)
from analytics_mcp.tools.reporting.realtime import (
    _run_realtime_report_description,
    run_realtime_report,
)

mcp = FastMCP("Google Analytics MCP Server")


def _register_tool(
    function: Callable[..., Any], description: str | None = None
) -> None:
    """Register an existing async function as a FastMCP tool."""
    mcp.add_tool(Tool.from_function(fn=function, description=description))


_register_tool(get_account_summaries)
_register_tool(list_google_ads_links)
_register_tool(get_property_details)
_register_tool(list_property_annotations)
_register_tool(get_custom_dimensions_and_metrics)
_register_tool(run_report, _run_report_description())
_register_tool(run_realtime_report, _run_realtime_report_description())
_register_tool(run_funnel_report, _run_funnel_report_description())
_register_tool(run_conversions_report, _run_conversions_report_description())


def ensure_subscriptions_listen(server: FastMCP) -> bool:
    """Install the optional MCP 2 subscription handler when absent.

    Some clients probe ``subscriptions/listen`` during connection setup. The
    handler is added idempotently so the same stateful Streamable HTTP endpoint
    works with those clients without affecting clients that do not use it.

    Returns:
        True when the handler was installed, otherwise False.
    """
    low_level_server = server._mcp_server
    if "subscriptions/listen" in low_level_server._request_handlers:
        return False

    subscription_bus = InMemorySubscriptionBus()
    low_level_server.add_request_handler(
        "subscriptions/listen",
        mcp_types.SubscriptionsListenRequestParams,
        ListenHandler(subscription_bus),
    )
    return True


ensure_subscriptions_listen(mcp)
