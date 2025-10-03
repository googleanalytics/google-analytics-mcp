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
            utils.construct_property_rn("12345"),
            "properties/12345",
            "Numeric property ID as string should be considered valid",
        )
        self.assertEqual(
            utils.construct_property_rn(" 12345  "),
            "properties/12345",
            (
                "Whitespace around property ID should be trimmed "
                "and considered valid"
            ),
        )
        self.assertEqual(
            utils.construct_property_rn("213025502"),
            "properties/213025502",
            "Real-world property ID should be considered valid",
        )

    def test_construct_property_rn_invalid_input(self):
        """Tests that construct_property_rn raises a ValueError for invalid input."""
        with self.assertRaises(ValueError, msg="Empty string should fail"):
            utils.construct_property_rn("")
        with self.assertRaises(
            ValueError, msg="Whitespace-only string should fail"
        ):
            utils.construct_property_rn("   ")
        with self.assertRaises(
            ValueError, msg="Non-numeric string should fail"
        ):
            utils.construct_property_rn("abc")
        with self.assertRaises(
            ValueError, msg="Alphanumeric string should fail"
        ):
            utils.construct_property_rn("abc123")
        with self.assertRaises(
            ValueError, msg="Negative number string should fail"
        ):
            utils.construct_property_rn("-12345")
        with self.assertRaises(
            ValueError, msg="Full resource name format no longer supported"
        ):
            utils.construct_property_rn("properties/12345")
        with self.assertRaises(
            ValueError, msg="Number with decimal should fail"
        ):
            utils.construct_property_rn("123.45")
