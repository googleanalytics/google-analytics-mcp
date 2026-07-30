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

"""Test cases for the coordinator module (FastMCP tool registration)."""

import unittest

from analytics_mcp.coordinator import mcp
from analytics_mcp.tools.reporting.core import _run_report_description

EXPECTED_TOOLS = {
    "get_account_summaries",
    "list_google_ads_links",
    "get_property_details",
    "list_property_annotations",
    "get_custom_dimensions_and_metrics",
    "run_report",
    "run_realtime_report",
    "run_funnel_report",
    "run_conversions_report",
}

# Fields that must be marked required in each tool's generated input schema.
EXPECTED_REQUIRED = {
    "get_account_summaries": set(),
    "list_google_ads_links": {"property_id"},
    "get_property_details": {"property_id"},
    "list_property_annotations": {"property_id"},
    "get_custom_dimensions_and_metrics": {"property_id"},
    "run_report": {"property_id", "date_ranges", "dimensions", "metrics"},
    "run_realtime_report": {"property_id", "dimensions", "metrics"},
    "run_funnel_report": {"property_id", "funnel_steps"},
    "run_conversions_report": {
        "property_id",
        "date_ranges",
        "dimensions",
        "metrics",
        "conversion_spec",
    },
}


def _assert_bool_additional_properties(test, tool_name, node, path="$"):
    """Recursively asserts additionalProperties is a bool wherever present.

    Some MCP clients (e.g. Claude Desktop) fail when additionalProperties
    is a schema object instead of a boolean.
    """
    if isinstance(node, dict):
        if "additionalProperties" in node:
            test.assertIsInstance(
                node["additionalProperties"],
                bool,
                f"{tool_name}: non-bool additionalProperties at {path}",
            )
        for key, child in node.items():
            _assert_bool_additional_properties(
                test, tool_name, child, f"{path}.{key}"
            )
    elif isinstance(node, list):
        for index, child in enumerate(node):
            _assert_bool_additional_properties(
                test, tool_name, child, f"{path}[{index}]"
            )


class TestCoordinator(unittest.IsolatedAsyncioTestCase):
    """Test cases for FastMCP tool registration and generated schemas."""

    async def asyncSetUp(self):
        tools = await mcp.list_tools()
        self.tools = {tool.name: tool for tool in tools}
        self.mcp_tools = {
            name: tool.to_mcp_tool(name=name)
            for name, tool in self.tools.items()
        }

    async def test_all_tools_registered(self):
        self.assertEqual(set(self.tools.keys()), EXPECTED_TOOLS)

    async def test_required_fields(self):
        for name, expected in EXPECTED_REQUIRED.items():
            schema = self.mcp_tools[name].inputSchema
            self.assertEqual(
                set(schema.get("required", [])),
                expected,
                f"Unexpected required fields for '{name}'",
            )

    async def test_all_tools_marked_read_only(self):
        for name, mcp_tool in self.mcp_tools.items():
            annotations = mcp_tool.annotations
            self.assertIsNotNone(
                annotations, f"Tool '{name}' has no annotations"
            )
            self.assertTrue(
                annotations.readOnlyHint,
                f"Tool '{name}' is missing readOnlyHint=True",
            )

    async def test_all_tools_have_descriptions(self):
        for name, mcp_tool in self.mcp_tools.items():
            self.assertTrue(
                (mcp_tool.description or "").strip(),
                f"Tool '{name}' has an empty description",
            )

    async def test_run_report_uses_extended_description(self):
        self.assertEqual(
            self.tools["run_report"].description, _run_report_description()
        )

    async def test_additional_properties_are_booleans(self):
        for name, mcp_tool in self.mcp_tools.items():
            _assert_bool_additional_properties(self, name, mcp_tool.inputSchema)

    async def test_no_auth_provider_without_oauth_env_vars(self):
        # This module is imported without the OAuth env vars set, so the
        # server must be in stdio mode with no auth provider.
        self.assertIsNone(mcp.auth)


if __name__ == "__main__":
    unittest.main()
