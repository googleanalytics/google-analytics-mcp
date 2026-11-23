# Copyright 2026 Google LLC All Rights Reserved.
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

"""Test cases for the report tasks reporting module."""

import asyncio
import json
import unittest
from unittest import mock

from analytics_mcp import coordinator
from analytics_mcp.tools.reporting import report_tasks
from google.analytics import data_v1alpha
from mcp import types as mcp_types


def _report_task(state, error_message=""):
    """Builds a ReportTask in the given state."""
    return data_v1alpha.ReportTask(
        name="properties/12345/reportTasks/abc",
        report_metadata=data_v1alpha.ReportTask.ReportMetadata(
            state=state,
            error_message=error_message,
            task_row_count=1,
            total_row_count=1,
        ),
    )


class TestRunReportTask(unittest.TestCase):
    """Test cases for run_report_task."""

    def setUp(self):
        self._sleep_patcher = mock.patch.object(
            report_tasks.time, "sleep", return_value=None
        )
        self._sleep_patcher.start()
        self.addCleanup(self._sleep_patcher.stop)

    def _run(self, report_task=None, query_response=None, **kwargs):
        """Runs the tool against a fake client and returns the create request.

        Args:
            report_task: The active ReportTask the fake client returns.
            query_response: The response returned by query_report_task.
            **kwargs: Extra arguments passed to run_report_task.
        """
        if report_task is None:
            report_task = _report_task(
                data_v1alpha.ReportTask.ReportMetadata.State.ACTIVE
            )
        if query_response is None:
            query_response = data_v1alpha.QueryReportTaskResponse()

        client = mock.MagicMock()
        client.create_report_task.return_value.result.return_value = report_task
        client.get_report_task.return_value = report_task
        client.query_report_task.return_value = query_response
        self.client = client

        arguments = dict(
            property_id=12345,
            date_ranges=[{"start_date": "7daysAgo", "end_date": "today"}],
            dimensions=["country"],
            metrics=["totalUsers"],
        )
        arguments.update(kwargs)
        with mock.patch.object(
            report_tasks, "create_data_api_alpha_client", return_value=client
        ):
            self.result = asyncio.run(report_tasks.run_report_task(**arguments))
        client.query_report_task.assert_called_once_with(name=report_task.name)
        return client.create_report_task.call_args.args[0]

    def test_report_definition_is_passed_to_create_request(self):
        """Tests that the report definition carries the report arguments."""
        request = self._run()

        self.assertEqual(request.parent, "properties/12345")
        definition = request.report_task.report_definition
        self.assertEqual(definition.dimensions[0].name, "country")
        self.assertEqual(definition.metrics[0].name, "totalUsers")
        self.assertEqual(len(definition.date_ranges), 1)

    def test_sampling_level_is_set_on_report_definition(self):
        """Tests that sampling_level accepts the documented level names."""
        expected_levels = {
            "LOW": data_v1alpha.SamplingLevel.LOW,
            "MEDIUM": data_v1alpha.SamplingLevel.MEDIUM,
            "UNSAMPLED": data_v1alpha.SamplingLevel.UNSAMPLED,
        }
        for name, expected in expected_levels.items():
            with self.subTest(sampling_level=name):
                request = self._run(sampling_level=name)
                self.assertEqual(
                    request.report_task.report_definition.sampling_level,
                    expected,
                )

    def test_sampling_level_is_case_insensitive(self):
        """Tests that sampling_level accepts lowercase names."""
        request = self._run(sampling_level=" medium ")

        self.assertEqual(
            request.report_task.report_definition.sampling_level,
            data_v1alpha.SamplingLevel.MEDIUM,
        )

    def test_sampling_level_omitted_keeps_api_default(self):
        """Tests that an omitted sampling_level leaves the field unset."""
        request = self._run()

        self.assertEqual(
            request.report_task.report_definition.sampling_level,
            data_v1alpha.SamplingLevel.SAMPLING_LEVEL_UNSPECIFIED,
        )

    def test_invalid_sampling_level_is_rejected(self):
        """Tests that an unsupported sampling_level raises ValueError."""
        with self.assertRaises(ValueError):
            self._run(sampling_level="unsampled please")

    def test_non_string_sampling_level_is_rejected(self):
        """Tests that a non-string sampling_level raises ValueError."""
        with self.assertRaises(ValueError):
            self._run(sampling_level=3)

    def test_filters_limits_and_currency_are_set(self):
        """Tests that the optional report arguments reach the definition."""
        request = self._run(
            dimension_filter={
                "filter": {
                    "field_name": "country",
                    "string_filter": {"value": "Japan"},
                }
            },
            metric_filter={
                "filter": {
                    "field_name": "totalUsers",
                    "numeric_filter": {"value": {"int64_value": 5}},
                }
            },
            order_bys=[{"metric": {"metric_name": "totalUsers"}}],
            limit=100,
            offset=50,
            currency_code="USD",
        )
        definition = request.report_task.report_definition

        self.assertEqual(
            definition.dimension_filter.filter.field_name, "country"
        )
        self.assertEqual(
            definition.metric_filter.filter.field_name, "totalUsers"
        )
        self.assertEqual(
            definition.order_bys[0].metric.metric_name, "totalUsers"
        )
        self.assertEqual(definition.limit, 100)
        self.assertEqual(definition.offset, 50)
        self.assertEqual(definition.currency_code, "USD")

    def test_rows_are_returned_with_the_report_task(self):
        """Tests that the queried rows are returned with the report task."""
        response = data_v1alpha.QueryReportTaskResponse(
            rows=[
                data_v1alpha.Row(
                    dimension_values=[
                        data_v1alpha.DimensionValue(value="Japan")
                    ],
                    metric_values=[data_v1alpha.MetricValue(value="42")],
                )
            ]
        )
        self._run(query_response=response)

        self.assertEqual(
            self.result["name"], "properties/12345/reportTasks/abc"
        )
        self.assertEqual(self.result["report_metadata"]["state"], "ACTIVE")
        self.assertEqual(
            self.result["rows"][0]["dimension_values"][0], {"value": "Japan"}
        )
        self.assertEqual(
            self.result["rows"][0]["metric_values"][0], {"value": "42"}
        )

    def test_creating_task_is_polled_until_active(self):
        """Tests that a CREATING report task is polled until it is ACTIVE."""
        active = _report_task(
            data_v1alpha.ReportTask.ReportMetadata.State.ACTIVE
        )
        creating = _report_task(
            data_v1alpha.ReportTask.ReportMetadata.State.CREATING
        )
        client = mock.MagicMock()
        client.create_report_task.return_value.result.return_value = creating
        client.get_report_task.side_effect = [creating, active]
        client.query_report_task.return_value = (
            data_v1alpha.QueryReportTaskResponse()
        )

        with mock.patch.object(
            report_tasks, "create_data_api_alpha_client", return_value=client
        ):
            asyncio.run(
                report_tasks.run_report_task(
                    property_id=12345,
                    date_ranges=[{"start_date": "today", "end_date": "today"}],
                    dimensions=[],
                    metrics=["totalUsers"],
                )
            )

        self.assertEqual(client.get_report_task.call_count, 2)

    def test_failed_task_raises_runtime_error(self):
        """Tests that a FAILED report task surfaces the API error message."""
        failed = _report_task(
            data_v1alpha.ReportTask.ReportMetadata.State.FAILED,
            error_message="unsampled report too large",
        )
        with self.assertRaises(RuntimeError) as context:
            self._run(report_task=failed)
        self.assertIn("unsampled report too large", str(context.exception))

    def test_creating_task_times_out(self):
        """Tests that a task still CREATING after the timeout raises."""
        creating = _report_task(
            data_v1alpha.ReportTask.ReportMetadata.State.CREATING
        )
        with self.assertRaises(TimeoutError):
            self._run(report_task=creating, timeout_seconds=1)

    def test_timeout_seconds_bounds_are_enforced(self):
        """Tests that timeout_seconds outside 1-300 raises ValueError."""
        for timeout_seconds in (0, 301):
            with self.subTest(timeout_seconds=timeout_seconds):
                with self.assertRaises(ValueError):
                    self._run(timeout_seconds=timeout_seconds)

    def test_description_documents_sampling_level(self):
        """Tests that the tool description documents sampling_level."""
        description = report_tasks._run_report_task_description()

        self.assertIn("Hints for `sampling_level`", description)
        self.assertIn("UNSAMPLED", description)


class TestRunReportTaskMcpHandlers(unittest.IsolatedAsyncioTestCase):
    """Test cases for the run_report_task tool exposed over MCP."""

    def _client(self):
        """Returns a fake client for an ACTIVE report task."""
        client = mock.MagicMock()
        client.create_report_task.return_value.result.return_value = (
            _report_task(data_v1alpha.ReportTask.ReportMetadata.State.ACTIVE)
        )
        client.get_report_task.return_value = _report_task(
            data_v1alpha.ReportTask.ReportMetadata.State.ACTIVE
        )
        client.query_report_task.return_value = (
            data_v1alpha.QueryReportTaskResponse(
                rows=[
                    data_v1alpha.Row(
                        dimension_values=[
                            data_v1alpha.DimensionValue(value="Japan")
                        ],
                        metric_values=[data_v1alpha.MetricValue(value="42")],
                    )
                ]
            )
        )
        return client

    async def test_tool_is_listed_as_read_only(self):
        """Tests that run_report_task is listed with a read-only hint."""
        server = coordinator.create_server()
        list_handler = server.get_request_handler("tools/list").handler
        tools = (await list_handler(None, None)).tools
        tool = {t.name: t for t in tools}["run_report_task"]

        self.assertTrue(tool.annotations.read_only_hint)
        self.assertEqual(
            tool.input_schema["required"],
            ["property_id", "date_ranges", "dimensions", "metrics"],
        )
        self.assertIn("sampling_level", tool.input_schema["properties"])

    async def test_call_tool_forwards_sampling_level(self):
        """Tests that sampling_level reaches the API through tools/call."""
        client = self._client()
        server = coordinator.create_server()
        call_handler = server.get_request_handler("tools/call").handler

        with mock.patch.object(
            report_tasks, "create_data_api_alpha_client", return_value=client
        ):
            result = await call_handler(
                None,
                mcp_types.CallToolRequestParams(
                    name="run_report_task",
                    arguments={
                        "property_id": 12345,
                        "date_ranges": [
                            {"start_date": "7daysAgo", "end_date": "today"}
                        ],
                        "dimensions": ["country"],
                        "metrics": ["totalUsers"],
                        "sampling_level": "UNSAMPLED",
                    },
                ),
            )

        self.assertFalse(result.is_error)
        request = client.create_report_task.call_args.args[0]
        self.assertEqual(
            request.report_task.report_definition.sampling_level,
            data_v1alpha.SamplingLevel.UNSAMPLED,
        )
        payload = json.loads(result.content[0].text)
        self.assertEqual(payload["report_metadata"]["state"], "ACTIVE")
        self.assertEqual(
            payload["rows"][0]["dimension_values"][0]["value"], "Japan"
        )

    async def test_call_tool_reports_invalid_sampling_level(self):
        """Tests that an invalid sampling_level returns an MCP error."""
        client = self._client()
        server = coordinator.create_server()
        call_handler = server.get_request_handler("tools/call").handler

        with mock.patch.object(
            report_tasks, "create_data_api_alpha_client", return_value=client
        ):
            result = await call_handler(
                None,
                mcp_types.CallToolRequestParams(
                    name="run_report_task",
                    arguments={
                        "property_id": 12345,
                        "date_ranges": [
                            {"start_date": "7daysAgo", "end_date": "today"}
                        ],
                        "dimensions": [],
                        "metrics": ["totalUsers"],
                        "sampling_level": "everything",
                    },
                ),
            )

        self.assertTrue(result.is_error)
        self.assertIn("sampling_level", result.content[0].text)


if __name__ == "__main__":
    unittest.main()
