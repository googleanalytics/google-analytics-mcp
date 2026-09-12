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

"""Test cases for the FastMCP coordinator."""

import asyncio
import unittest

from analytics_mcp import coordinator


class TestCoordinator(unittest.TestCase):
    """Test the registered MCP tools and compatibility handler."""

    def test_registers_all_google_analytics_tools(self):
        """All public tools should be visible through FastMCP."""
        tools = asyncio.run(coordinator.mcp.list_tools())
        self.assertEqual(
            {tool.name for tool in tools},
            {
                "get_account_summaries",
                "get_custom_dimensions_and_metrics",
                "get_property_details",
                "list_google_ads_links",
                "list_property_annotations",
                "run_conversions_report",
                "run_funnel_report",
                "run_realtime_report",
                "run_report",
            },
        )

    def test_subscriptions_listen_handler_is_idempotent(self):
        """The compatibility handler must not be installed twice."""
        self.assertIn(
            "subscriptions/listen",
            coordinator.mcp._mcp_server._request_handlers,
        )
        self.assertFalse(
            coordinator.ensure_subscriptions_listen(coordinator.mcp)
        )
