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

"""Module declaring the singleton MCP instance.

The singleton allows other modules to register their tools with the same MCP
server using `@mcp.tool` annotations, thereby 'coordinating' the bootstrapping
of the server.
"""

from adk.tools import FunctionTool
from adk.tools.mcp_adapters import adk_to_mcp_tool_type
from mcp import McpApp, ToolCall, ToolResult

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
    FunctionTool(get_account_summaries),
    FunctionTool(list_google_ads_links),
    FunctionTool(get_property_details),
    FunctionTool(list_property_annotations),
    FunctionTool(get_custom_dimensions_and_metrics),
    FunctionTool(
        run_report,
        name="run_report",
        description=_run_report_description(),
    ),
    FunctionTool(
        run_realtime_report,
        name="run_realtime_report",
        description=_run_realtime_report_description(),
    ),
]
tool_map = {t.name: t for t in tools}

# 2. Create an MCP application
app = McpApp(
    title="Google Analytics Server",
    description="An MCP server for Google Analytics.",
)


# 3. Implement list_tools to advertise the ADK tool
@app.list_tools
async def list_tools():
    return {
        "tools": [adk_to_mcp_tool_type(tool.tool_type) for tool in tools],
    }


# 4. Implement call_tool to execute the tool
@app.call_tool
async def call_tool(tool_call: ToolCall) -> ToolResult:
    if tool_call.function.name in tool_map:
        tool = tool_map[tool_call.function.name]
        # 4a. Execute the tool
        tool_result = await tool.run_async(tool_call.function.arguments)
        # 4b. Format the response for MCP
        return ToolResult(
            call_id=tool_call.call_id,
            content=str(tool_result.content),
        )
    raise ValueError(f"Tool {tool_call.function.name} not found")

mcp = app
