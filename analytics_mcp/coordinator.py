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
server.
"""

# MCP Server Imports
import json
import sys

from mcp import types as mcp_types  # Use alias to avoid conflict
from mcp.server.context import (
    CallNext,
    HandlerResult,
    ServerRequestContext,
)
from mcp.server.lowlevel import Server

# ADK Tool Imports
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

from analytics_mcp.tools.client import (
    REFRESH_TOKEN_HEADER,
    clear_refresh_token,
    set_refresh_token,
)

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

run_report_with_description = FunctionTool(run_report)
run_report_with_description.description = _run_report_description()
run_realtime_report_with_description = FunctionTool(run_realtime_report)
run_realtime_report_with_description.description = (
    _run_realtime_report_description()
)
run_funnel_report_with_description = FunctionTool(run_funnel_report)
run_funnel_report_with_description.description = (
    _run_funnel_report_description()
)
run_conversions_report_with_description = FunctionTool(run_conversions_report)
run_conversions_report_with_description.description = (
    _run_conversions_report_description()
)

# Instantiate the ADK tools
tools = [
    FunctionTool(get_account_summaries),
    FunctionTool(list_google_ads_links),
    FunctionTool(get_property_details),
    FunctionTool(list_property_annotations),
    FunctionTool(get_custom_dimensions_and_metrics),
    run_report_with_description,
    run_realtime_report_with_description,
    run_funnel_report_with_description,
    run_conversions_report_with_description,
]

tool_map = {t.name: t for t in tools}


mcp_tools = [adk_to_mcp_tool_type(tool) for tool in tools]


def sanitize_mcp_schema_properties(node: dict) -> None:
    """Ensure additionalProperties is a boolean value to satisfy certain MCP clients.

    This addresses issues with clients like Claude Desktop that fail when
    additionalProperties is a schema object instead of a boolean.
    """
    if not isinstance(node, dict):
        return

    # Check and update the current node
    if "additionalProperties" in node:
        val = node["additionalProperties"]
        if not isinstance(val, bool):
            node["additionalProperties"] = True

    # Traverse children
    for key, child in node.items():
        if isinstance(child, dict):
            sanitize_mcp_schema_properties(child)
        elif isinstance(child, list):
            for element in child:
                if isinstance(element, dict):
                    sanitize_mcp_schema_properties(element)


# Update the input_schema for tools that do not have parameters.
# NOTE: The Pydantic field on mcp_types.Tool is `input_schema` (Python
# attribute) with wire alias `inputSchema`. Programmatically we always use
# the Python attribute name.
# TODO: This is a bug in the ADK and can be removed once it is fixed.
# https://github.com/google/adk-python/issues/948
for tool in mcp_tools:
    # Check if input_schema is empty
    if tool.input_schema == {}:
        tool.input_schema = {"type": "object", "properties": {}}
    # Fix union type hints generating spurious "type": "null"
    for prop in tool.input_schema.get("properties", {}).values():
        if "anyOf" in prop and prop.get("type") == "null":
            del prop["type"]

    # Ensure additionalProperties is compatible with all MCP clients
    sanitize_mcp_schema_properties(tool.input_schema)

    # Explicitly mark required fields for reporting tools to guide the LLM
    if tool.name == "run_report":
        tool.input_schema["required"] = [
            "property_id",
            "date_ranges",
            "dimensions",
            "metrics",
        ]
    elif tool.name == "run_realtime_report":
        tool.input_schema["required"] = ["property_id", "dimensions", "metrics"]
    elif tool.name == "run_conversions_report":
        tool.input_schema["required"] = [
            "property_id",
            "date_ranges",
            "dimensions",
            "metrics",
            "conversion_spec",
        ]


# ---- MCP request handlers -------------------------------------------------


async def _handle_list_tools(
    ctx: ServerRequestContext,
    params: mcp_types.PaginatedRequestParams | None,
) -> mcp_types.ListToolsResult:
    """Handler for the MCP tools/list request."""
    return mcp_types.ListToolsResult(tools=mcp_tools)


async def _handle_call_tool(
    ctx: ServerRequestContext,
    params: mcp_types.CallToolRequestParams,
) -> mcp_types.CallToolResult:
    """Handler for the MCP tools/call request."""
    name = params.name
    arguments = params.arguments or {}

    if name in tool_map:
        tool = tool_map[name]
        try:
            adk_tool_response = await tool.run_async(
                args=arguments,
                tool_context=None,
            )
            response_text = json.dumps(adk_tool_response, indent=2)
            return mcp_types.CallToolResult(
                content=[mcp_types.TextContent(type="text", text=response_text)]
            )

        except Exception as e:
            print(
                f"MCP Server: Error executing ADK tool '{name}': {e}",
                file=sys.stderr,
            )
            error_text = json.dumps(
                {"error": f"Failed to execute tool '{name}': {str(e)}"}
            )
            return mcp_types.CallToolResult(
                content=[mcp_types.TextContent(type="text", text=error_text)],
                is_error=True,
            )

    error_text = json.dumps(
        {"error": f"Tool '{name}' not implemented by this server."}
    )
    return mcp_types.CallToolResult(
        content=[mcp_types.TextContent(type="text", text=error_text)],
        is_error=True,
    )


# ---- Middleware -----------------------------------------------------------


async def refresh_token_middleware(
    ctx: ServerRequestContext,
    call_next: CallNext,
) -> HandlerResult:
    """Server middleware that extracts a Google OAuth refresh token from the
    inbound HTTP request header (x-ga-refresh-token) and places it into the
    request-scoped ContextVar.

    The ContextVar is read by the Google client factory functions in
    :mod:`analytics_mcp.tools.client` when building credentials.

    No-op when running over STDIO or when the header is absent.
    """
    request = ctx.request
    refresh_token = None
    if request is not None and hasattr(request, "headers"):
        refresh_token = request.headers.get(REFRESH_TOKEN_HEADER)

    if refresh_token:
        token = set_refresh_token(refresh_token)
        try:
            return await call_next(ctx)
        finally:
            clear_refresh_token(token)
    else:
        return await call_next(ctx)


# ---- Server construction --------------------------------------------------

app = Server(
    name="Google Analytics MCP Server",
    on_list_tools=_handle_list_tools,
    on_call_tool=_handle_call_tool,
)

# Register as the outermost user middleware. SDK's built-ins run inside it so
# the refresh token context is available for all user handlers including
# list_tools and call_tool.
app.middleware.append(refresh_token_middleware)
