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

import importlib
import os
import unittest
from unittest import mock

from analytics_mcp.tools import client

_READ = "https://www.googleapis.com/auth/analytics.readonly"
_EDIT = "https://www.googleapis.com/auth/analytics.edit"


class TestGetCredentials(unittest.TestCase):
    """Test cases for _get_credentials scope selection."""

    def _requested_scopes(self, env):
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(client, "_CREDENTIALS", None),
            mock.patch(
                "google.auth.default", return_value=(mock.Mock(), None)
            ) as default,
        ):
            client._get_credentials()
        return default.call_args.kwargs["scopes"]

    def test_read_only_by_default(self):
        self.assertEqual(self._requested_scopes({}), [_READ])
        self.assertEqual(
            self._requested_scopes({"ANALYTICS_MCP_ENABLE_WRITES": "false"}),
            [_READ],
        )

    def test_edit_scope_added_when_writes_enabled(self):
        self.assertEqual(
            self._requested_scopes({"ANALYTICS_MCP_ENABLE_WRITES": "true"}),
            [_READ, _EDIT],
        )


class TestWriteToolRegistration(unittest.TestCase):
    """Test cases for opt-in registration of the write tools."""

    def _tool_names(self, env):
        from analytics_mcp import coordinator

        with mock.patch.dict(os.environ, env, clear=True):
            try:
                importlib.reload(coordinator)
                return set(coordinator.tool_map)
            finally:
                os.environ.pop("ANALYTICS_MCP_ENABLE_WRITES", None)
                importlib.reload(coordinator)

    def test_write_tools_hidden_by_default(self):
        names = self._tool_names({})
        self.assertIn("list_key_events", names)
        self.assertNotIn("create_custom_dimension", names)
        self.assertNotIn("create_key_event", names)

    def test_write_tools_registered_when_enabled(self):
        names = self._tool_names({"ANALYTICS_MCP_ENABLE_WRITES": "true"})
        self.assertIn("create_custom_dimension", names)
        self.assertIn("create_key_event", names)


if __name__ == "__main__":
    unittest.main()
