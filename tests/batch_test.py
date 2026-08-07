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

"""Test cases for the batch_run_reports tool."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from google.analytics import data_v1beta

from analytics_mcp.tools.reporting.batch import (
    batch_run_reports,
    _build_report_request,
)


class TestBuildReportRequest(unittest.TestCase):
    """Test cases for _build_report_request."""

    def test_required_fields(self):
        """Tests that required fields are set correctly."""
        report = {
            "dimensions": ["country", "city"],
            "metrics": ["activeUsers", "sessions"],
            "date_ranges": [
                {
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                }
            ],
        }
        request = _build_report_request("properties/12345", report)

        self.assertIsInstance(request, data_v1beta.RunReportRequest)
        self.assertEqual(request.property, "properties/12345")
        self.assertEqual(len(request.dimensions), 2)
        self.assertEqual(request.dimensions[0].name, "country")
        self.assertEqual(request.dimensions[1].name, "city")
        self.assertEqual(len(request.metrics), 2)
        self.assertEqual(request.metrics[0].name, "activeUsers")
        self.assertEqual(request.metrics[1].name, "sessions")
        self.assertEqual(len(request.date_ranges), 1)
        self.assertFalse(request.return_property_quota)

    def test_optional_fields(self):
        """Tests that optional fields are set when provided."""
        report = {
            "dimensions": ["country"],
            "metrics": ["activeUsers"],
            "date_ranges": [
                {
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                }
            ],
            "limit": 100,
            "offset": 50,
            "currency_code": "USD",
            "return_property_quota": True,
        }
        request = _build_report_request("properties/12345", report)

        self.assertEqual(request.limit, 100)
        self.assertEqual(request.offset, 50)
        self.assertEqual(request.currency_code, "USD")
        self.assertTrue(request.return_property_quota)

    def test_dimension_filter(self):
        """Tests that dimension_filter is set when provided."""
        report = {
            "dimensions": ["country"],
            "metrics": ["activeUsers"],
            "date_ranges": [
                {
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                }
            ],
            "dimension_filter": {
                "filter": {
                    "field_name": "country",
                    "string_filter": {
                        "match_type": "EXACT",
                        "value": "US",
                    },
                }
            },
        }
        request = _build_report_request("properties/12345", report)

        self.assertIsNotNone(request.dimension_filter)

    def test_metric_filter(self):
        """Tests that metric_filter is set when provided."""
        report = {
            "dimensions": ["country"],
            "metrics": ["activeUsers"],
            "date_ranges": [
                {
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                }
            ],
            "metric_filter": {
                "filter": {
                    "field_name": "activeUsers",
                    "numeric_filter": {
                        "operation": "GREATER_THAN",
                        "value": {"int64_value": 10},
                    },
                }
            },
        }
        request = _build_report_request("properties/12345", report)

        self.assertIsNotNone(request.metric_filter)

    def test_order_bys(self):
        """Tests that order_bys are set when provided."""
        report = {
            "dimensions": ["country"],
            "metrics": ["activeUsers"],
            "date_ranges": [
                {
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                }
            ],
            "order_bys": [
                {
                    "metric": {
                        "metric_name": "activeUsers",
                    },
                    "desc": True,
                }
            ],
        }
        request = _build_report_request("properties/12345", report)

        self.assertEqual(len(request.order_bys), 1)

    def test_optional_fields_absent(self):
        """Tests that optional fields are absent when not provided."""
        report = {
            "dimensions": ["country"],
            "metrics": ["activeUsers"],
            "date_ranges": [
                {
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                }
            ],
        }
        request = _build_report_request("properties/12345", report)

        self.assertEqual(request.limit, 0)
        self.assertEqual(request.offset, 0)
        self.assertEqual(request.currency_code, "")
        self.assertEqual(len(request.order_bys), 0)


class TestBatchRunReports(unittest.TestCase):
    """Test cases for batch_run_reports validation."""

    def test_empty_requests_raises(self):
        """Tests that an empty requests list raises ValueError."""
        with self.assertRaises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                batch_run_reports(12345, [])
            )

    def test_too_many_requests_raises(self):
        """Tests that more than 5 requests raises ValueError."""
        reports = [
            {
                "dimensions": ["country"],
                "metrics": ["activeUsers"],
                "date_ranges": [
                    {
                        "start_date": "2025-01-01",
                        "end_date": "2025-01-31",
                    }
                ],
            }
        ] * 6

        with self.assertRaises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                batch_run_reports(12345, reports)
            )

    def test_requests_not_a_list_raises(self):
        """Tests that a non-list requests value raises ValueError."""
        with self.assertRaises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                batch_run_reports(
                    12345,
                    {
                        "dimensions": ["country"],
                        "metrics": ["activeUsers"],
                        "date_ranges": [
                            {
                                "start_date": "2025-01-01",
                                "end_date": "2025-01-31",
                            }
                        ],
                    },
                )
            )

    def test_non_dict_request_raises(self):
        """Tests that a non-dict request raises ValueError."""
        with self.assertRaises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                batch_run_reports(12345, ["not a dict"])
            )

    def test_dimensions_not_a_list_raises(self):
        """Tests that a non-list dimensions value raises ValueError."""
        reports = [
            {
                "dimensions": "country",
                "metrics": ["activeUsers"],
                "date_ranges": [
                    {
                        "start_date": "2025-01-01",
                        "end_date": "2025-01-31",
                    }
                ],
            }
        ]

        with self.assertRaises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                batch_run_reports(12345, reports)
            )

    def test_missing_dimensions_raises(self):
        """Tests that a request missing dimensions raises ValueError."""
        reports = [
            {
                "metrics": ["activeUsers"],
                "date_ranges": [
                    {
                        "start_date": "2025-01-01",
                        "end_date": "2025-01-31",
                    }
                ],
            }
        ]

        with self.assertRaises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                batch_run_reports(12345, reports)
            )

    def test_missing_metrics_raises(self):
        """Tests that a request missing metrics raises ValueError."""
        reports = [
            {
                "dimensions": ["country"],
                "date_ranges": [
                    {
                        "start_date": "2025-01-01",
                        "end_date": "2025-01-31",
                    }
                ],
            }
        ]

        with self.assertRaises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                batch_run_reports(12345, reports)
            )

    def test_missing_date_ranges_raises(self):
        """Tests that a request missing date_ranges raises ValueError."""
        reports = [
            {
                "dimensions": ["country"],
                "metrics": ["activeUsers"],
            }
        ]

        with self.assertRaises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                batch_run_reports(12345, reports)
            )

    @patch("analytics_mcp.tools.reporting.batch." "create_data_api_client")
    def test_api_called_with_correct_request(self, mock_client):
        """Tests that the API is called with the correct request."""
        mock_response = MagicMock()
        mock_response.__class__ = data_v1beta.BatchRunReportsResponse
        mock_client_instance = MagicMock()
        mock_client_instance.batch_run_reports.return_value = mock_response
        mock_client.return_value = mock_client_instance

        reports = [
            {
                "dimensions": ["country"],
                "metrics": ["activeUsers"],
                "date_ranges": [
                    {
                        "start_date": "2025-01-01",
                        "end_date": "2025-01-31",
                    }
                ],
            },
            {
                "dimensions": ["city"],
                "metrics": ["sessions"],
                "date_ranges": [
                    {
                        "start_date": "2025-02-01",
                        "end_date": "2025-02-28",
                    }
                ],
            },
        ]

        with patch(
            "analytics_mcp.tools.reporting.batch.proto_to_dict",
            return_value={"reports": []},
        ):
            result = asyncio.get_event_loop().run_until_complete(
                batch_run_reports(12345, reports)
            )

        mock_client_instance.batch_run_reports.assert_called_once()
        call_args = mock_client_instance.batch_run_reports.call_args
        batch_request = call_args[0][0]

        self.assertEqual(batch_request.property, "properties/12345")
        self.assertEqual(len(batch_request.requests), 2)
        self.assertEqual(
            batch_request.requests[0].dimensions[0].name,
            "country",
        )
        self.assertEqual(
            batch_request.requests[1].dimensions[0].name,
            "city",
        )
        self.assertEqual(result, {"reports": []})
