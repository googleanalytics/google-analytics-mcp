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

"""Test cases for quota warning functionality."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from analytics_mcp.tools.reporting import core, realtime


class TestQuotaWarning(unittest.IsolatedAsyncioTestCase):
    """Test cases for quota warning functionality in reporting tools."""

    def _create_mock_response(self, quota_consumed, quota_remaining):
        """Helper to create a mock response with quota data."""
        mock_response = MagicMock()
        mock_response.row_count = 5
        mock_response.dimension_headers = [MagicMock(name="country")]
        mock_response.metric_headers = [MagicMock(name="sessions")]
        mock_response.rows = []
        mock_response.metadata = None
        mock_response.totals = None
        mock_response.maximums = None
        mock_response.minimums = None
        
        # Create quota mock
        mock_quota = MagicMock()
        mock_quota_dict = {
            "tokens_per_day": {
                "consumed": quota_consumed,
                "remaining": quota_remaining
            },
            "tokens_per_hour": {
                "consumed": 10,
                "remaining": 39990
            }
        }
        mock_response.property_quota = mock_quota
        
        return mock_response, mock_quota_dict

    @patch("analytics_mcp.tools.reporting.core.create_data_api_client")
    @patch("analytics_mcp.tools.reporting.core.construct_property_rn")
    @patch("analytics_mcp.tools.reporting.core.proto_to_dict")
    async def test_quota_warning_not_triggered_low_usage(
        self, mock_proto_to_dict, mock_construct_rn, mock_client
    ):
        """Tests that quota warning is NOT triggered when usage is low
        (<90%).
        """
        # Setup mocks for low usage (1%)
        mock_construct_rn.return_value = "properties/12345"
        mock_response, mock_quota_dict = self._create_mock_response(
            quota_consumed=100, quota_remaining=9900
        )
        mock_client.return_value.run_report = AsyncMock(
            return_value=mock_response
        )
        mock_proto_to_dict.return_value = mock_quota_dict

        # Call run_report with return_property_quota=False
        result = await core.run_report(
            property_id="12345",
            date_ranges=[
                {"start_date": "yesterday", "end_date": "yesterday"}
            ],
            dimensions=["country"],
            metrics=["sessions"],
            return_property_quota=False,
        )

        # Verify quota is NOT included (usage < 90%)
        self.assertNotIn(
            "quota", result, "Quota should not be included when usage < 90%"
        )
        self.assertNotIn(
            "quota_warning",
            result,
            "No warning should be present when usage < 90%",
        )

    @patch("analytics_mcp.tools.reporting.core.create_data_api_client")
    @patch("analytics_mcp.tools.reporting.core.construct_property_rn")
    @patch("analytics_mcp.tools.reporting.core.proto_to_dict")
    async def test_quota_warning_triggered_high_usage(
        self, mock_proto_to_dict, mock_construct_rn, mock_client
    ):
        """Tests that quota warning IS triggered when usage is high
        (>90%).
        """
        # Setup mocks for high usage (91%)
        mock_construct_rn.return_value = "properties/12345"
        mock_response, mock_quota_dict = self._create_mock_response(
            quota_consumed=18200, quota_remaining=1800
        )
        mock_client.return_value.run_report = AsyncMock(
            return_value=mock_response
        )
        mock_proto_to_dict.return_value = mock_quota_dict

        # Call run_report with return_property_quota=False
        result = await core.run_report(
            property_id="12345",
            date_ranges=[
                {"start_date": "yesterday", "end_date": "yesterday"}
            ],
            dimensions=["country"],
            metrics=["sessions"],
            return_property_quota=False,
        )

        # Verify quota IS included (usage > 90%)
        self.assertIn(
            "quota", result, "Quota should be included when usage > 90%"
        )
        self.assertIn(
            "quota_warning",
            result,
            "Warning should be present when usage > 90%",
        )
        
        # Verify warning message format
        warning = result["quota_warning"]
        self.assertIn("WARNING", warning)
        self.assertIn("tokens_per_day", warning)
        self.assertIn("91.0%", warning)
        self.assertIn("18200/20000", warning)

    @patch("analytics_mcp.tools.reporting.core.create_data_api_client")
    @patch("analytics_mcp.tools.reporting.core.construct_property_rn")
    @patch("analytics_mcp.tools.reporting.core.proto_to_dict")
    async def test_quota_warning_edge_case_exactly_90_percent(
        self, mock_proto_to_dict, mock_construct_rn, mock_client
    ):
        """Tests that quota warning is NOT triggered at exactly 90%
        (threshold is >90%).
        """
        # Setup mocks for exactly 90% usage
        mock_construct_rn.return_value = "properties/12345"
        mock_response, mock_quota_dict = self._create_mock_response(
            quota_consumed=9000, quota_remaining=1000
        )
        mock_client.return_value.run_report = AsyncMock(
            return_value=mock_response
        )
        mock_proto_to_dict.return_value = mock_quota_dict

        # Call run_report with return_property_quota=False
        result = await core.run_report(
            property_id="12345",
            date_ranges=[
                {"start_date": "yesterday", "end_date": "yesterday"}
            ],
            dimensions=["country"],
            metrics=["sessions"],
            return_property_quota=False,
        )

        # Verify quota is NOT included (exactly 90% is not > 90%)
        self.assertNotIn(
            "quota", result, "Quota should not be included at exactly 90%"
        )
        self.assertNotIn("quota_warning", result, "No warning at exactly 90%")

    @patch("analytics_mcp.tools.reporting.core.create_data_api_client")
    @patch("analytics_mcp.tools.reporting.core.construct_property_rn")
    @patch("analytics_mcp.tools.reporting.core.proto_to_dict")
    async def test_quota_included_when_explicitly_requested(
        self, mock_proto_to_dict, mock_construct_rn, mock_client
    ):
        """Tests that quota is always included when explicitly
        requested.
        """
        # Setup mocks for low usage
        mock_construct_rn.return_value = "properties/12345"
        mock_response, mock_quota_dict = self._create_mock_response(
            quota_consumed=10, quota_remaining=19990
        )
        mock_client.return_value.run_report = AsyncMock(
            return_value=mock_response
        )
        mock_proto_to_dict.return_value = mock_quota_dict

        # Call run_report with return_property_quota=True
        result = await core.run_report(
            property_id="12345",
            date_ranges=[
                {"start_date": "yesterday", "end_date": "yesterday"}
            ],
            dimensions=["country"],
            metrics=["sessions"],
            return_property_quota=True,
        )

        # Verify quota IS included even with low usage
        self.assertIn(
            "quota",
            result,
            "Quota should be included when explicitly requested",
        )

    @patch("analytics_mcp.tools.reporting.realtime.create_data_api_client")
    @patch("analytics_mcp.tools.reporting.realtime.construct_property_rn")
    @patch("analytics_mcp.tools.reporting.realtime.proto_to_dict")
    async def test_realtime_quota_warning_triggered(
        self, mock_proto_to_dict, mock_construct_rn, mock_client
    ):
        """Tests that quota warning works for realtime reports too."""
        # Setup mocks for high usage (95%)
        mock_construct_rn.return_value = "properties/12345"
        mock_response, mock_quota_dict = self._create_mock_response(
            quota_consumed=19000, quota_remaining=1000
        )
        mock_client.return_value.run_realtime_report = AsyncMock(
            return_value=mock_response
        )
        mock_proto_to_dict.return_value = mock_quota_dict

        # Call run_realtime_report with return_property_quota=False
        result = await realtime.run_realtime_report(
            property_id="12345",
            dimensions=["country"],
            metrics=["activeUsers"],
            return_property_quota=False,
        )

        # Verify quota warning for realtime
        self.assertIn(
            "quota",
            result,
            "Quota should be included for realtime when usage > 90%",
        )
        self.assertIn(
            "quota_warning",
            result,
            "Warning should be present for realtime",
        )
        
        # Verify warning format
        warning = result["quota_warning"]
        self.assertIn("WARNING", warning)
        self.assertIn("95.0%", warning)

    @patch("analytics_mcp.tools.reporting.core.create_data_api_client")
    @patch("analytics_mcp.tools.reporting.core.construct_property_rn")
    @patch("analytics_mcp.tools.reporting.core.proto_to_dict")
    async def test_quota_warning_checks_multiple_metrics(
        self, mock_proto_to_dict, mock_construct_rn, mock_client
    ):
        """Tests that quota warning checks all quota metrics and
        triggers on first >90%.
        """
        # Setup mocks with tokens_per_day OK but tokens_per_hour high
        mock_construct_rn.return_value = "properties/12345"
        mock_response = MagicMock()
        mock_response.row_count = 5
        mock_response.dimension_headers = [MagicMock(name="country")]
        mock_response.metric_headers = [MagicMock(name="sessions")]
        mock_response.rows = []
        mock_response.metadata = None
        mock_response.totals = None
        mock_response.maximums = None
        mock_response.minimums = None

        mock_quota_dict = {
            "tokens_per_day": {"consumed": 100, "remaining": 199900},
            "tokens_per_hour": {"consumed": 36400, "remaining": 3600},
        }
        mock_response.property_quota = MagicMock()
        mock_client.return_value.run_report = AsyncMock(
            return_value=mock_response
        )
        mock_proto_to_dict.return_value = mock_quota_dict

        # Call run_report
        result = await core.run_report(
            property_id="12345",
            date_ranges=[
                {"start_date": "yesterday", "end_date": "yesterday"}
            ],
            dimensions=["country"],
            metrics=["sessions"],
            return_property_quota=False,
        )
        
        # Verify warning is triggered by tokens_per_hour
        self.assertIn("quota_warning", result)
        self.assertIn("tokens_per_hour", result["quota_warning"])
        self.assertIn("91.0%", result["quota_warning"])


if __name__ == "__main__":
    unittest.main()
