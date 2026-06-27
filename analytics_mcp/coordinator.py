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
from mcp.server.lowlevel import Server

# ADK Tool Imports
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

from analytics_mcp.tools.admin.info import (
    get_account_summaries,
    list_google_ads_links,
    get_property_details,
    list_property_annotations,
)
from analytics_mcp.tools.admin.discovery import (
    list_accounts,
    get_account,
    list_properties,
    list_data_streams,
    get_data_stream,
    get_data_retention_settings,
    get_data_sharing_settings,
    list_firebase_links,
    list_key_events,
    get_key_event,
    list_conversion_events,
    get_conversion_event,
    list_custom_dimensions,
    get_custom_dimension,
    list_custom_metrics,
    get_custom_metric,
    run_access_report,
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
from analytics_mcp.tools.reporting.advanced import (
    get_property_metadata,
    run_pivot_report,
    check_report_compatibility,
    get_property_quotas_snapshot,
)
from analytics_mcp.tools.reporting.async_reads import (
    list_audience_exports,
    get_audience_export,
    list_audience_lists,
    get_audience_list,
    list_recurring_audience_lists,
    get_recurring_audience_list,
    list_report_tasks,
    get_report_task,
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
    FunctionTool(list_accounts),
    FunctionTool(get_account),
    FunctionTool(list_google_ads_links),
    FunctionTool(get_property_details),
    FunctionTool(list_properties),
    FunctionTool(list_data_streams),
    FunctionTool(get_data_stream),
    FunctionTool(get_data_retention_settings),
    FunctionTool(get_data_sharing_settings),
    FunctionTool(list_firebase_links),
    FunctionTool(list_key_events),
    FunctionTool(get_key_event),
    FunctionTool(list_conversion_events),
    FunctionTool(get_conversion_event),
    FunctionTool(list_custom_dimensions),
    FunctionTool(get_custom_dimension),
    FunctionTool(list_custom_metrics),
    FunctionTool(get_custom_metric),
    FunctionTool(run_access_report),
    FunctionTool(list_property_annotations),
    FunctionTool(get_custom_dimensions_and_metrics),
    FunctionTool(get_property_metadata),
    run_report_with_description,
    FunctionTool(run_pivot_report),
    FunctionTool(check_report_compatibility),
    run_realtime_report_with_description,
    run_funnel_report_with_description,
    run_conversions_report_with_description,
    FunctionTool(get_property_quotas_snapshot),
    FunctionTool(list_audience_exports),
    FunctionTool(get_audience_export),
    FunctionTool(list_audience_lists),
    FunctionTool(get_audience_list),
    FunctionTool(list_recurring_audience_lists),
    FunctionTool(get_recurring_audience_list),
    FunctionTool(list_report_tasks),
    FunctionTool(get_report_task),
]

tool_map = {t.name: t for t in tools}

app = Server(
    name="Google Analytics MCP Server",
)

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


# Update the inputSchema for tools that do not have parameters.
# TODO: This is a bug in the ADK and can be removed once it is fixed.
# https://github.com/google/adk-python/issues/948
for tool in mcp_tools:
    # Check if inputSchema is empty
    if tool.inputSchema == {}:
        tool.inputSchema = {"type": "object", "properties": {}}
    # Fix union type hints generating spurious "type": "null"
    for prop in tool.inputSchema.get("properties", {}).values():
        if "anyOf" in prop and prop.get("type") == "null":
            del prop["type"]

    # Ensure additionalProperties is compatible with all MCP clients
    sanitize_mcp_schema_properties(tool.inputSchema)

    # Explicitly mark required fields for reporting tools to guide the LLM
    if tool.name == "run_report":
        tool.inputSchema["required"] = [
            "property_id",
            "date_ranges",
            "dimensions",
            "metrics",
        ]
    elif tool.name == "run_realtime_report":
        tool.inputSchema["required"] = ["property_id", "dimensions", "metrics"]
    elif tool.name == "run_conversions_report":
        tool.inputSchema["required"] = [
            "property_id",
            "date_ranges",
            "dimensions",
            "metrics",
            "conversion_spec",
        ]


@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    """Returns the MCP tool surface exposed by this server."""
    return mcp_tools


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    """Executes one registered tool and serializes the result to MCP text content."""
    if name in tool_map:
        tool = tool_map[name]
        try:
            adk_tool_response = await tool.run_async(
                args=arguments,
                tool_context=None,
            )
            # Serialize the ADK tool response to JSON for MCP response
            response_text = json.dumps(adk_tool_response, indent=2)
            # MCP expects a list of mcp_types.Content parts
            return [mcp_types.TextContent(type="text", text=response_text)]

        except Exception as e:
            print(
                f"MCP Server: Error executing ADK tool '{name}': {e}",
                file=sys.stderr,
            )
            # Return an error message in MCP format
            error_text = json.dumps(
                {"error": f"Failed to execute tool '{name}': {str(e)}"}
            )
            return [mcp_types.TextContent(type="text", text=error_text)]

    error_text = json.dumps(
        {"error": f"Tool '{name}' not implemented by this server."}
    )
    return [mcp_types.TextContent(type="text", text=error_text)]
