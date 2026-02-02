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

"""Test cases for the ADK-based MCP server."""

import unittest
import asyncio
from unittest.mock import patch

from adk.tools.results import ToolResult
from mcp import ToolCall, Function
from analytics_mcp.coordinator import list_tools, call_tool, tool_map


class TestAdkServer(unittest.TestCase):
    """Test cases for the ADK-based MCP server."""

    def test_list_tools(self):
        """Tests that the list_tools function returns the correct tools."""
        loop = asyncio.get_event_loop()
        tool_list = loop.run_until_complete(list_tools())
        self.assertIn("tools", tool_list)
        self.assertEqual(len(tool_list["tools"]), 7)

    def test_call_tool(self):
        """Tests that the call_tool function correctly calls a tool."""

        async def run_test():
            with patch.object(
                tool_map["get_account_summaries"],
                "run_async",
                return_value=ToolResult(content={"accounts": []}),
            ) as mock_run_async:
                tool_call = ToolCall(
                    call_id="123",
                    function=Function(name="get_account_summaries", arguments={}),
                )
                result = await call_tool(tool_call)
                mock_run_async.assert_called_once_with({})
                self.assertEqual(result.call_id, "123")
                self.assertIn("'accounts': []", result.content)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()