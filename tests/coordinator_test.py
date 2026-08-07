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

"""Test cases for the coordinator module."""

import asyncio
import unittest

from analytics_mcp import coordinator

# Names of every tool the server returns from a 'tools/list' request.
_EXPECTED_TOOL_NAMES = {
    "get_account_summaries",
    "get_custom_dimensions_and_metrics",
    "get_property_details",
    "list_google_ads_links",
    "list_property_annotations",
    "run_conversions_report",
    "run_funnel_report",
    "run_realtime_report",
    "run_report",
}

# The annotations every tool should report. Keys that aren't listed here must
# be unset, since ToolAnnotations documents destructiveHint and idempotentHint
# as meaningful only when readOnlyHint is False.
_EXPECTED_ANNOTATIONS = {
    "readOnlyHint": True,
    "openWorldHint": True,
}


class TestCoordinator(unittest.TestCase):
    """Test cases for the coordinator module."""

    def test_list_tools_returns_expected_tools(self):
        """Tests that list_tools returns every registered tool."""
        tools = asyncio.run(coordinator.list_tools())
        self.assertEqual(
            {tool.name for tool in tools},
            _EXPECTED_TOOL_NAMES,
            "Tools added or removed here need an annotations review",
        )

    def test_list_tools_annotations(self):
        """Tests the annotations returned for each tool."""
        tools = asyncio.run(coordinator.list_tools())
        for tool in tools:
            with self.subTest(tool=tool.name):
                self.assertIsNotNone(
                    tool.annotations,
                    f"Tool '{tool.name}' should have annotations",
                )
                self.assertEqual(
                    tool.annotations.model_dump(exclude_none=True),
                    _EXPECTED_ANNOTATIONS,
                    f"Unexpected annotations for tool '{tool.name}'",
                )

    def test_annotations_are_not_shared_between_tools(self):
        """Tests that each tool owns its annotations.

        ToolAnnotations is mutable, so a shared instance would let a change to
        one tool's annotations affect every other tool.
        """
        tools = asyncio.run(coordinator.list_tools())
        self.assertEqual(
            len({id(tool.annotations) for tool in tools}),
            len(tools),
            "Each tool should have its own ToolAnnotations instance",
        )
