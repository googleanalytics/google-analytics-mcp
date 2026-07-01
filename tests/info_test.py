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

"""Test cases for the admin info tools."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from google.analytics import admin_v1alpha, admin_v1beta

from analytics_mcp.tools.admin.info import (
    get_data_retention_settings,
    list_audiences,
    list_custom_dimensions,
    list_custom_metrics,
    list_data_streams,
    list_key_events,
    list_properties,
)


class TestListKeyEvents(unittest.TestCase):
    """Test cases for list_key_events."""

    @patch("analytics_mcp.tools.admin.info.create_admin_api_client")
    def test_returns_key_events(self, mock_create_client):
        """Tests that key events are listed and converted to dicts."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        key_event = admin_v1beta.KeyEvent(
            name="properties/12345/keyEvents/67890",
            event_name="purchase",
            counting_method=(
                admin_v1beta.KeyEvent.CountingMethod.ONCE_PER_EVENT
            ),
        )
        mock_client.list_key_events.return_value = [key_event]

        result = asyncio.run(list_key_events(12345))

        request = mock_client.list_key_events.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["event_name"], "purchase")
        self.assertEqual(result[0]["name"], "properties/12345/keyEvents/67890")

    @patch("analytics_mcp.tools.admin.info.create_admin_api_client")
    def test_accepts_property_rn_string(self, mock_create_client):
        """Tests that a 'properties/' prefixed string is accepted."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_key_events.return_value = []

        result = asyncio.run(list_key_events("properties/9876"))

        request = mock_client.list_key_events.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/9876")
        self.assertEqual(result, [])

    def test_invalid_property_id_raises(self):
        """Tests that an invalid property ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(list_key_events("not-a-property"))


class TestListDataStreams(unittest.TestCase):
    """Test cases for list_data_streams."""

    @patch("analytics_mcp.tools.admin.info.create_admin_api_client")
    def test_returns_data_streams(self, mock_create_client):
        """Tests that data streams are listed and converted to dicts."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        web_stream = admin_v1beta.DataStream(
            name="properties/12345/dataStreams/111",
            type_=admin_v1beta.DataStream.DataStreamType.WEB_DATA_STREAM,
            display_name="Web stream",
            web_stream_data=admin_v1beta.DataStream.WebStreamData(
                measurement_id="G-ABC123",
                default_uri="https://www.example.com",
            ),
        )
        mock_client.list_data_streams.return_value = [web_stream]

        result = asyncio.run(list_data_streams(12345))

        request = mock_client.list_data_streams.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["display_name"], "Web stream")
        self.assertEqual(
            result[0]["web_stream_data"]["measurement_id"], "G-ABC123"
        )

    def test_invalid_property_id_raises(self):
        """Tests that an invalid property ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(list_data_streams("bogus"))


class TestListProperties(unittest.TestCase):
    """Test cases for list_properties."""

    @patch("analytics_mcp.tools.admin.info.create_admin_api_client")
    def test_returns_properties(self, mock_create_client):
        """Tests that properties are listed with an account filter."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        prop = admin_v1beta.Property(
            name="properties/12345",
            display_name="My property",
            time_zone="America/New_York",
            currency_code="USD",
        )
        mock_client.list_properties.return_value = [prop]

        result = asyncio.run(list_properties(98765))

        request = mock_client.list_properties.call_args.kwargs["request"]
        self.assertEqual(request.filter, "parent:accounts/98765")
        self.assertFalse(request.show_deleted)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["display_name"], "My property")

    @patch("analytics_mcp.tools.admin.info.create_admin_api_client")
    def test_show_deleted_passthrough(self, mock_create_client):
        """Tests that show_deleted is passed through to the request."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_properties.return_value = []

        asyncio.run(list_properties("accounts/55", show_deleted=True))

        request = mock_client.list_properties.call_args.kwargs["request"]
        self.assertEqual(request.filter, "parent:accounts/55")
        self.assertTrue(request.show_deleted)

    def test_invalid_account_id_raises(self):
        """Tests that an invalid account ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(list_properties("properties/123"))


class TestListCustomDimensions(unittest.TestCase):
    """Test cases for list_custom_dimensions."""

    @patch("analytics_mcp.tools.admin.info.create_admin_api_client")
    def test_returns_custom_dimensions(self, mock_create_client):
        """Tests that custom dimensions include Admin API detail."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        dimension = admin_v1beta.CustomDimension(
            name="properties/12345/customDimensions/1",
            parameter_name="plan_type",
            display_name="Plan type",
            description="The subscription plan type.",
            scope=admin_v1beta.CustomDimension.DimensionScope.EVENT,
        )
        mock_client.list_custom_dimensions.return_value = [dimension]

        result = asyncio.run(list_custom_dimensions(12345))

        request = mock_client.list_custom_dimensions.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["parameter_name"], "plan_type")
        self.assertEqual(result[0]["scope"], "EVENT")

    def test_invalid_property_id_raises(self):
        """Tests that an invalid property ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(list_custom_dimensions("bogus"))


class TestListCustomMetrics(unittest.TestCase):
    """Test cases for list_custom_metrics."""

    @patch("analytics_mcp.tools.admin.info.create_admin_api_client")
    def test_returns_custom_metrics(self, mock_create_client):
        """Tests that custom metrics include Admin API detail."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        metric = admin_v1beta.CustomMetric(
            name="properties/12345/customMetrics/1",
            parameter_name="loyalty_points",
            display_name="Loyalty points",
            measurement_unit=(
                admin_v1beta.CustomMetric.MeasurementUnit.STANDARD
            ),
            scope=admin_v1beta.CustomMetric.MetricScope.EVENT,
        )
        mock_client.list_custom_metrics.return_value = [metric]

        result = asyncio.run(list_custom_metrics(12345))

        request = mock_client.list_custom_metrics.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["parameter_name"], "loyalty_points")
        self.assertEqual(result[0]["measurement_unit"], "STANDARD")

    def test_invalid_property_id_raises(self):
        """Tests that an invalid property ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(list_custom_metrics("bogus"))


class TestGetDataRetentionSettings(unittest.TestCase):
    """Test cases for get_data_retention_settings."""

    @patch("analytics_mcp.tools.admin.info.create_admin_api_client")
    def test_returns_settings(self, mock_create_client):
        """Tests that retention settings are fetched and converted."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        settings = admin_v1beta.DataRetentionSettings(
            name="properties/12345/dataRetentionSettings",
            event_data_retention=(
                admin_v1beta.DataRetentionSettings.RetentionDuration.FOURTEEN_MONTHS
            ),
            reset_user_data_on_new_activity=True,
        )
        mock_client.get_data_retention_settings.return_value = settings

        result = asyncio.run(get_data_retention_settings(12345))

        request = mock_client.get_data_retention_settings.call_args.kwargs[
            "request"
        ]
        self.assertEqual(request.name, "properties/12345/dataRetentionSettings")
        self.assertEqual(result["event_data_retention"], "FOURTEEN_MONTHS")
        self.assertTrue(result["reset_user_data_on_new_activity"])

    def test_invalid_property_id_raises(self):
        """Tests that an invalid property ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(get_data_retention_settings("bogus"))


class TestListAudiences(unittest.TestCase):
    """Test cases for list_audiences."""

    @patch("analytics_mcp.tools.admin.info.create_admin_alpha_api_client")
    def test_returns_audiences(self, mock_create_client):
        """Tests that audiences are listed via the alpha client."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        audience = admin_v1alpha.Audience(
            name="properties/12345/audiences/777",
            display_name="Purchasers",
            description="Users who purchased.",
            membership_duration_days=30,
        )
        mock_client.list_audiences.return_value = [audience]

        result = asyncio.run(list_audiences(12345))

        request = mock_client.list_audiences.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["display_name"], "Purchasers")
        self.assertEqual(result[0]["membership_duration_days"], 30)

    def test_invalid_property_id_raises(self):
        """Tests that an invalid property ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(list_audiences("bogus"))


if __name__ == "__main__":
    unittest.main()
