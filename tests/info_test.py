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

from google.analytics import admin_v1beta

from analytics_mcp.tools.admin.info import list_key_events


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


if __name__ == "__main__":
    unittest.main()
