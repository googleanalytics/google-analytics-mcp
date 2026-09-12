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

"""Test cases for transport configuration."""

import os
import unittest
from unittest import mock

from analytics_mcp import server


class TestServer(unittest.TestCase):
    """Test the stdio and Streamable HTTP entry points."""

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch.object(server.mcp, "run")
    def test_stdio_is_the_default(self, run):
        """Existing stdio clients should retain the default behavior."""
        server.run_server()
        run.assert_called_once_with()

    @mock.patch.dict(
        os.environ,
        {
            "ANALYTICS_MCP_TRANSPORT": "streamable-http",
            "HOST": "0.0.0.0",
            "PORT": "9090",
        },
        clear=True,
    )
    @mock.patch.object(server.mcp, "run")
    def test_streamable_http_configuration(self, run):
        """HTTP configuration should map to the stateful FastMCP transport."""
        server.run_server()
        run.assert_called_once_with(
            transport="streamable-http",
            host="0.0.0.0",
            port=9090,
            uvicorn_config={"access_log": False},
        )

    @mock.patch.dict(
        os.environ,
        {"ANALYTICS_MCP_TRANSPORT": "invalid"},
        clear=True,
    )
    def test_rejects_unknown_transport(self):
        """Mistyped transports should fail instead of silently using stdio."""
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            server.run_server()

    @mock.patch.dict(os.environ, {"PORT": "70000"}, clear=True)
    def test_rejects_invalid_port(self):
        """HTTP ports must be valid TCP ports."""
        with self.assertRaisesRegex(ValueError, "between 1 and 65535"):
            server._configured_port()
