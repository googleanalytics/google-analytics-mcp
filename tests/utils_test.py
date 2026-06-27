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

"""Test cases for the utils module."""

import unittest

from analytics_mcp.tools import utils


class TestUtils(unittest.TestCase):
    """Test cases for the utils module."""

    def test_construct_property_rn(self):
        """Tests construct_property_rn using valid input."""
        self.assertEqual(
            utils.construct_property_rn(12345),
            "properties/12345",
            "Numeric property ID should b considered valid",
        )
        self.assertEqual(
            utils.construct_property_rn("12345"),
            "properties/12345",
            "Numeric property ID as string should be considered valid",
        )
        self.assertEqual(
            utils.construct_property_rn(" 12345  "),
            "properties/12345",
            "Whitespace around property ID should be considered valid",
        )
        self.assertEqual(
            utils.construct_property_rn("properties/12345"),
            "properties/12345",
            "Full resource name should be considered valid",
        )
        self.assertEqual(
            utils.construct_account_rn("accounts/32636632"),
            "accounts/32636632",
        )
        self.assertEqual(
            utils.construct_account_rn("32636632"),
            "accounts/32636632",
        )
        self.assertEqual(
            utils.construct_data_stream_rn(252198517, "4268733166"),
            "properties/252198517/dataStreams/4268733166",
        )
        self.assertEqual(
            utils.construct_key_event_rn(252198517, "purchase"),
            "properties/252198517/keyEvents/purchase",
        )
        self.assertEqual(
            utils.construct_data_retention_settings_rn(252198517),
            "properties/252198517/dataRetentionSettings",
        )
        self.assertEqual(
            utils.construct_conversion_event_rn(252198517, "2564717350"),
            "properties/252198517/conversionEvents/2564717350",
        )
        self.assertEqual(
            utils.construct_custom_dimension_rn(252198517, "5688242159"),
            "properties/252198517/customDimensions/5688242159",
        )
        self.assertEqual(
            utils.construct_custom_metric_rn(252198517, "987654321"),
            "properties/252198517/customMetrics/987654321",
        )
        self.assertEqual(
            utils.construct_data_sharing_settings_rn(32636632),
            "accounts/32636632/dataSharingSettings",
        )
        self.assertEqual(
            utils.construct_property_quotas_snapshot_rn(252198517),
            "properties/252198517/propertyQuotasSnapshot",
        )
        self.assertEqual(
            utils.construct_audience_export_rn(
                252198517, "properties/252198517/audienceExports/test-export"
            ),
            "properties/252198517/audienceExports/test-export",
        )
        self.assertEqual(
            utils.construct_audience_list_rn(252198517, "test-list"),
            "properties/252198517/audienceLists/test-list",
        )
        self.assertEqual(
            utils.construct_recurring_audience_list_rn(
                252198517, "test-recurring"
            ),
            "properties/252198517/recurringAudienceLists/test-recurring",
        )
        self.assertEqual(
            utils.construct_report_task_rn(252198517, "test-task"),
            "properties/252198517/reportTasks/test-task",
        )

    def test_construct_property_rn_invalid_input(self):
        """Tests that construct_property_rn raises a ValueError for invalid input."""
        with self.assertRaises(ValueError, msg="None should fail"):
            utils.construct_property_rn(None)
        with self.assertRaises(ValueError, msg="Empty string should fail"):
            utils.construct_property_rn("")
        with self.assertRaises(
            ValueError, msg="Non-numeric string should fail"
        ):
            utils.construct_property_rn("abc")
        with self.assertRaises(
            ValueError, msg="Resource name without ID should fail"
        ):
            utils.construct_property_rn("properties/")
        with self.assertRaises(
            ValueError, msg="Resource name with non-numeric ID should fail"
        ):
            utils.construct_property_rn("properties/abc")
        with self.assertRaises(
            ValueError,
            msg="Resource name with more than 2 components should fail",
        ):
            utils.construct_property_rn("properties/123/abc")
        with self.assertRaises(ValueError):
            utils.construct_account_rn("accounts/abc")
        with self.assertRaises(ValueError):
            utils.construct_data_stream_rn(252198517, "")
        with self.assertRaises(ValueError):
            utils.construct_key_event_rn(252198517, "")
        with self.assertRaises(ValueError):
            utils.construct_conversion_event_rn(252198517, "")
        with self.assertRaises(ValueError):
            utils.construct_custom_dimension_rn(252198517, "")
        with self.assertRaises(ValueError):
            utils.construct_custom_metric_rn(252198517, "")
        with self.assertRaises(ValueError):
            utils.construct_audience_export_rn(252198517, "")
