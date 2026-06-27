import unittest

import analytics_mcp.coordinator as coordinator


class CoordinatorSchemaTest(unittest.TestCase):
    def test_expected_tool_names_are_exposed(self):
        names = [tool.name for tool in coordinator.mcp_tools]
        self.assertEqual(
            names,
            [
                "get_account_summaries",
                "list_accounts",
                "get_account",
                "list_google_ads_links",
                "get_property_details",
                "list_properties",
                "list_data_streams",
                "get_data_stream",
                "get_data_retention_settings",
                "get_data_sharing_settings",
                "list_firebase_links",
                "list_key_events",
                "get_key_event",
                "list_conversion_events",
                "get_conversion_event",
                "list_custom_dimensions",
                "get_custom_dimension",
                "list_custom_metrics",
                "get_custom_metric",
                "run_access_report",
                "list_property_annotations",
                "get_custom_dimensions_and_metrics",
                "get_property_metadata",
                "run_report",
                "run_pivot_report",
                "check_report_compatibility",
                "run_realtime_report",
                "run_funnel_report",
                "run_conversions_report",
                "get_property_quotas_snapshot",
                "list_audience_exports",
                "get_audience_export",
                "list_audience_lists",
                "get_audience_list",
                "list_recurring_audience_lists",
                "get_recurring_audience_list",
                "list_report_tasks",
                "get_report_task",
            ],
        )

    def test_empty_input_schema_is_normalized(self):
        tool = next(
            tool
            for tool in coordinator.mcp_tools
            if tool.name == "get_account_summaries"
        )
        self.assertEqual(tool.inputSchema, {"type": "object", "properties": {}})

    def test_reporting_tools_have_required_fields(self):
        required_fields = {
            "run_report": ["property_id", "date_ranges", "dimensions", "metrics"],
            "run_realtime_report": ["property_id", "dimensions", "metrics"],
            "run_conversions_report": [
                "property_id",
                "date_ranges",
                "dimensions",
                "metrics",
                "conversion_spec",
            ],
        }
        for tool in coordinator.mcp_tools:
            if tool.name in required_fields:
                self.assertEqual(
                    tool.inputSchema.get("required"),
                    required_fields[tool.name],
                )

    def test_input_schema_uses_boolean_additional_properties(self):
        for tool in coordinator.mcp_tools:
            self._assert_boolean_additional_properties(tool.inputSchema)

    def _assert_boolean_additional_properties(self, node):
        if isinstance(node, dict):
            if "additionalProperties" in node:
                self.assertIsInstance(node["additionalProperties"], bool)
            for value in node.values():
                self._assert_boolean_additional_properties(value)
        elif isinstance(node, list):
            for value in node:
                self._assert_boolean_additional_properties(value)
