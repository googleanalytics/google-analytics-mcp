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
from json import tool
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
from analytics_mcp.tools.reporting.core import (
    run_report,
    _run_report_description,
)
from analytics_mcp.tools.reporting.realtime import (
    run_realtime_report,
    _run_realtime_report_description,
)
from analytics_mcp.tools.reporting.compatibility import (
    check_compatibility,
)
from analytics_mcp.tools.reporting.metadata import (
    get_custom_dimensions_and_metrics,
)

run_report_with_description = FunctionTool(run_report)
run_report_with_description.description = _run_report_description()
run_realtime_report_with_description = FunctionTool(run_realtime_report)
run_realtime_report_with_description.description = (
    _run_realtime_report_description()
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
    FunctionTool(check_compatibility),
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


@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return mcp_tools


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
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
            print(f"MCP Server: Error executing ADK tool '{name}': {e}")
            # Return an error message in MCP format
            error_text = json.dumps(
                {"error": f"Failed to execute tool '{name}': {str(e)}"}
            )
            return [mcp_types.TextContent(type="text", text=error_text)]

    error_text = json.dumps(
        {"error": f"Tool '{name}' not implemented by this server."}
    )
    return [mcp_types.TextContent(type="text", text=error_text)]
