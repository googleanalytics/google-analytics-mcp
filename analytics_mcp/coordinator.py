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
]

tool_map = {t.name: t for t in tools}

app = Server(
    name="Google Analytics MCP Server",
)

mcp_tools = [adk_to_mcp_tool_type(tool) for tool in tools]


def _fix_additional_properties(schema: dict) -> None:
    """Recursively convert non-boolean additionalProperties to boolean.

    Some MCP clients (Claude Desktop, OpenAI Codex) expect
    additionalProperties to be a boolean, not a schema object.
    See https://github.com/googleanalytics/google-analytics-mcp/issues/40
    """
    if not isinstance(schema, dict):
        return
    if "additionalProperties" in schema and not isinstance(
        schema["additionalProperties"], bool
    ):
        schema["additionalProperties"] = True
    for value in schema.values():
        if isinstance(value, dict):
            _fix_additional_properties(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _fix_additional_properties(item)


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
    # Fix non-boolean additionalProperties that break some MCP clients
    _fix_additional_properties(tool.inputSchema)


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
