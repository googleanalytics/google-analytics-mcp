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

"""Test cases for the client module's credential scope selection."""

import unittest

from analytics_mcp import coordinator
from analytics_mcp.tools import client


class TestConfigToolRegistration(unittest.IsolatedAsyncioTestCase):
    """Test cases for opt-in registration of the property config tools."""

    def tearDown(self):
        client.set_allow_write(False)

    async def _tool_names(self, allow_write):
        server = coordinator.create_server(allow_write=allow_write)
        result = await server.get_request_handler("tools/list").handler(
            None, None
        )
        return {t.name for t in result.tools}

    async def test_write_tools_hidden_by_default(self):
        names = await self._tool_names(False)
        self.assertIn("list_key_events", names)
        self.assertNotIn("create_custom_dimension", names)
        self.assertNotIn("create_key_event", names)

    async def test_write_tools_registered_with_allow_write(self):
        names = await self._tool_names(True)
        self.assertIn("create_custom_dimension", names)
        self.assertIn("create_key_event", names)


if __name__ == "__main__":
    unittest.main()
