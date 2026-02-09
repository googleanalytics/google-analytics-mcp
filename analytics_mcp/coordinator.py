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
from mcp import types as mcp_types # Use alias to avoid conflict
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
from analytics_mcp.tools.reporting.core import run_report, _run_report_description
from analytics_mcp.tools.reporting.realtime import (
    run_realtime_report,
    _run_realtime_report_description,
)
from analytics_mcp.tools.reporting.metadata import get_custom_dimensions_and_metrics

# 1. Instantiate the ADK tools
tools = [
    # FunctionTool(get_account_summaries),
    FunctionTool(list_google_ads_links),
    FunctionTool(get_property_details),
    FunctionTool(list_property_annotations),
    FunctionTool(get_custom_dimensions_and_metrics),
    FunctionTool(run_report),
    FunctionTool(run_realtime_report),
]
tool_map = {t.name: t for t in tools}

app = Server(
    name="Google Analytics Server",
)

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [adk_to_mcp_tool_type(tool) for tool in tools]

@app.call_tool()
async def call_mcp_tool(
    name: str, arguments: dict
) -> list[mcp_types.Content]: # MCP uses mcp_types.Content
    if name in tool_map:
        tool = tool_map[name]
        # 4a. Execute the tool
        tool_result = await tool.run_async(arguments)
        # 4b. Format the response for MCP
        response_text = json.dumps(tool_result, indent=2)
        return [mcp_types.TextContent(type="text", text=response_text)]
    
    print("Tool not found:", name)
    error_text = json.dumps({"error": f"Tool '{name}' not implemented by this server."})
    return [mcp_types.TextContent(type="text", text=error_text)]

