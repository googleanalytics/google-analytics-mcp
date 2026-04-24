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

"""Test cases for the compatibility module."""

import unittest

from analytics_mcp.tools.reporting import compatibility


class TestCheckCompatibility(unittest.TestCase):
    """Test cases for the check_compatibility tool."""

    def test_check_compatibility_is_importable(self):
        """Tests that check_compatibility can be imported."""
        self.assertTrue(
            callable(compatibility.check_compatibility),
            "check_compatibility should be a callable function",
        )

    def test_check_compatibility_is_async(self):
        """Tests that check_compatibility is an async function."""
        import asyncio

        self.assertTrue(
            asyncio.iscoroutinefunction(compatibility.check_compatibility),
            "check_compatibility should be an async function",
        )
