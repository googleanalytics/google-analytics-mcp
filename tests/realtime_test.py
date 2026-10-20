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

"""Test cases for the realtime reporting module."""

import asyncio
import unittest
from unittest import mock

from analytics_mcp.tools.reporting import realtime
from google.analytics import data_v1beta


class TestRunRealtimeReport(unittest.TestCase):
    """Test cases for run_realtime_report."""

    def _run(self, **kwargs):
        client = mock.MagicMock()
        client.run_realtime_report.return_value = (
            data_v1beta.RunRealtimeReportResponse()
        )
        with mock.patch.object(
            realtime, "create_data_api_client", return_value=client
        ):
            asyncio.run(
                realtime.run_realtime_report(
                    property_id=12345,
                    dimensions=[],
                    metrics=["activeUsers"],
                    **kwargs,
                )
            )
        return client.run_realtime_report.call_args.args[0]

    def test_minute_ranges_are_passed_to_request(self):
        """Tests that minute_ranges are set on the request."""
        request = self._run(
            minute_ranges=[
                {"name": "last30", "start_minutes_ago": 29},
                {
                    "name": "last5",
                    "start_minutes_ago": 4,
                    "end_minutes_ago": 0,
                },
            ]
        )
        self.assertEqual(len(request.minute_ranges), 2)
        self.assertEqual(request.minute_ranges[0].name, "last30")
        self.assertEqual(request.minute_ranges[0].start_minutes_ago, 29)
        self.assertEqual(request.minute_ranges[1].name, "last5")
        self.assertEqual(request.minute_ranges[1].start_minutes_ago, 4)
        self.assertEqual(request.minute_ranges[1].end_minutes_ago, 0)

    def test_minute_ranges_omitted_by_default(self):
        """Tests that no minute_ranges are set when the argument is omitted."""
        request = self._run()
        self.assertEqual(len(request.minute_ranges), 0)
        self.assertEqual(request.property, "properties/12345")

    def test_description_includes_minute_ranges_hints(self):
        """Tests that the tool description documents minute_ranges."""
        description = realtime._run_realtime_report_description()
        self.assertIn("Hints for `minute_ranges`", description)
        self.assertIn('"start_minutes_ago": 4', description)


if __name__ == "__main__":
    unittest.main()
