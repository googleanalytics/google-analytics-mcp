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

"""Test cases for the run_access_report tool."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from google.analytics import admin_v1beta

from analytics_mcp.tools.admin.access import (
    _construct_access_report_entity,
    run_access_report,
)


class TestConstructAccessReportEntity(unittest.TestCase):
    """Test cases for _construct_access_report_entity."""

    def test_property_forms(self):
        """Tests property ID forms resolve to a property entity."""
        self.assertEqual(
            _construct_access_report_entity(12345), "properties/12345"
        )
        self.assertEqual(
            _construct_access_report_entity("properties/12345"),
            "properties/12345",
        )

    def test_account_form(self):
        """Tests an 'accounts/' string resolves to an account entity."""
        self.assertEqual(
            _construct_access_report_entity("accounts/678"), "accounts/678"
        )

    def test_invalid_entity_raises(self):
        """Tests that invalid entities raise a ValueError."""
        with self.assertRaises(ValueError):
            _construct_access_report_entity("bogus")
        with self.assertRaises(ValueError):
            _construct_access_report_entity("accounts/abc")


class TestRunAccessReport(unittest.TestCase):
    """Test cases for run_access_report."""

    @patch("analytics_mcp.tools.admin.access.create_admin_api_client")
    def test_builds_request(self, mock_create_client):
        """Tests that the request proto is built correctly."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.run_access_report.return_value = (
            admin_v1beta.RunAccessReportResponse(row_count=0)
        )

        asyncio.run(
            run_access_report(
                12345,
                date_ranges=[{"start_date": "7daysAgo", "end_date": "today"}],
                dimensions=["userEmail", "accessMechanism"],
                metrics=["accessCount"],
                limit=50,
            )
        )

        request = mock_client.run_access_report.call_args.kwargs["request"]
        self.assertEqual(request.entity, "properties/12345")
        self.assertEqual(len(request.date_ranges), 1)
        self.assertEqual(request.date_ranges[0].start_date, "7daysAgo")
        self.assertEqual(
            [d.dimension_name for d in request.dimensions],
            ["userEmail", "accessMechanism"],
        )
        self.assertEqual(
            [m.metric_name for m in request.metrics], ["accessCount"]
        )
        self.assertEqual(request.limit, 50)
        self.assertFalse(request.return_entity_quota)

    @patch("analytics_mcp.tools.admin.access.create_admin_api_client")
    def test_account_level_report(self, mock_create_client):
        """Tests that account-level entities are passed through."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.run_access_report.return_value = (
            admin_v1beta.RunAccessReportResponse()
        )

        asyncio.run(
            run_access_report(
                "accounts/99",
                date_ranges=[
                    {"start_date": "2025-01-01", "end_date": "2025-01-31"}
                ],
                dimensions=["userEmail"],
                metrics=["accessCount"],
            )
        )

        request = mock_client.run_access_report.call_args.kwargs["request"]
        self.assertEqual(request.entity, "accounts/99")

    @patch("analytics_mcp.tools.admin.access.create_admin_api_client")
    def test_converts_response(self, mock_create_client):
        """Tests that the proto response is converted to a dict."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.run_access_report.return_value = (
            admin_v1beta.RunAccessReportResponse(row_count=2)
        )

        result = asyncio.run(
            run_access_report(
                12345,
                date_ranges=[{"start_date": "yesterday", "end_date": "today"}],
                dimensions=["userEmail"],
                metrics=["accessCount"],
            )
        )

        self.assertEqual(result["row_count"], 2)


if __name__ == "__main__":
    unittest.main()
