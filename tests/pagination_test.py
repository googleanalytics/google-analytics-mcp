# Copyright 2026 Google LLC All Rights Reserved.
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

"""Tests for reporting pagination validation."""

import unittest

from analytics_mcp.tools.reporting.pagination import validate_pagination


class TestPaginationValidation(unittest.TestCase):
    def test_accepts_omitted_values(self):
        validate_pagination(None, None)

    def test_accepts_valid_boundaries(self):
        validate_pagination(1, 0)
        validate_pagination(250_000, 2_147_483_647)

    def test_rejects_limit_outside_api_range(self):
        for limit in (0, -1, 250_001):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(ValueError, "limit"):
                    validate_pagination(limit, None)

    def test_rejects_non_integer_limit(self):
        for limit in (True, False, 1.5, "10"):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(ValueError, "limit"):
                    validate_pagination(limit, None)

    def test_rejects_negative_offset(self):
        with self.assertRaisesRegex(ValueError, "offset"):
            validate_pagination(None, -1)

    def test_rejects_non_integer_offset(self):
        for offset in (True, False, 1.5, "10"):
            with self.subTest(offset=offset):
                with self.assertRaisesRegex(ValueError, "offset"):
                    validate_pagination(None, offset)


if __name__ == "__main__":
    unittest.main()
