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

"""Test cases for the get_property_quotas tool."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from google.analytics import data_v1alpha

from analytics_mcp.tools.reporting.quotas import get_property_quotas


class TestGetPropertyQuotas(unittest.TestCase):
    """Test cases for get_property_quotas."""

    @patch("analytics_mcp.tools.reporting.quotas.create_data_api_alpha_client")
    def test_returns_quota_snapshot(self, mock_create_client):
        """Tests that the quota snapshot is fetched and converted."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        snapshot = data_v1alpha.PropertyQuotasSnapshot(
            name="properties/12345/propertyQuotasSnapshot",
            core_property_quota=data_v1alpha.PropertyQuota(
                tokens_per_day=data_v1alpha.QuotaStatus(
                    consumed=100, remaining=199900
                ),
            ),
        )
        mock_client.get_property_quotas_snapshot.return_value = snapshot

        result = asyncio.run(get_property_quotas(12345))

        request = mock_client.get_property_quotas_snapshot.call_args.kwargs[
            "request"
        ]
        self.assertEqual(
            request.name, "properties/12345/propertyQuotasSnapshot"
        )
        self.assertEqual(
            result["core_property_quota"]["tokens_per_day"]["consumed"], 100
        )
        self.assertEqual(
            result["core_property_quota"]["tokens_per_day"]["remaining"],
            199900,
        )

    def test_invalid_property_id_raises(self):
        """Tests that an invalid property ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(get_property_quotas("bogus"))


if __name__ == "__main__":
    unittest.main()
