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

"""Test cases for the reporting metadata tools."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from google.analytics import data_v1beta

from analytics_mcp.tools.reporting.metadata import (
    get_custom_dimensions_and_metrics,
    get_metadata,
)


def _sample_metadata() -> data_v1beta.Metadata:
    """Returns a Metadata proto with standard and custom entries."""
    return data_v1beta.Metadata(
        name="properties/12345/metadata",
        dimensions=[
            data_v1beta.DimensionMetadata(
                api_name="country",
                ui_name="Country",
                description="The country from which activity originated.",
                category="Geography",
                custom_definition=False,
            ),
            data_v1beta.DimensionMetadata(
                api_name="customEvent:plan_type",
                ui_name="Plan type",
                description="Custom event-scoped dimension.",
                category="Custom",
                custom_definition=True,
            ),
        ],
        metrics=[
            data_v1beta.MetricMetadata(
                api_name="activeUsers",
                ui_name="Active users",
                description="The number of distinct active users.",
                category="User",
                custom_definition=False,
            ),
        ],
    )


class TestGetMetadata(unittest.TestCase):
    """Test cases for get_metadata."""

    @patch("analytics_mcp.tools.reporting.metadata.create_data_api_client")
    def test_returns_full_catalog(self, mock_create_client):
        """Tests that the full catalog is returned, not just custom."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.get_metadata.return_value = _sample_metadata()

        result = asyncio.run(get_metadata(12345))

        mock_client.get_metadata.assert_called_once_with(
            name="properties/12345/metadata"
        )
        dimension_names = [d["api_name"] for d in result["dimensions"]]
        self.assertIn("country", dimension_names)
        self.assertIn("customEvent:plan_type", dimension_names)
        self.assertEqual(result["metrics"][0]["api_name"], "activeUsers")
        self.assertEqual(result["dimensions"][0]["category"], "Geography")

    def test_invalid_property_id_raises(self):
        """Tests that an invalid property ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(get_metadata("bogus"))


class TestGetCustomDimensionsAndMetrics(unittest.TestCase):
    """Test cases for get_custom_dimensions_and_metrics."""

    @patch("analytics_mcp.tools.reporting.metadata.create_data_api_client")
    def test_returns_only_custom_definitions(self, mock_create_client):
        """Tests that only custom definitions are returned."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.get_metadata.return_value = _sample_metadata()

        result = asyncio.run(get_custom_dimensions_and_metrics(12345))

        self.assertEqual(len(result["custom_dimensions"]), 1)
        self.assertEqual(
            result["custom_dimensions"][0]["api_name"],
            "customEvent:plan_type",
        )
        self.assertEqual(result["custom_metrics"], [])


if __name__ == "__main__":
    unittest.main()
