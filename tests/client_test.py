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

"""Test cases for credential resolution in the client module."""

import os
import unittest
from unittest import mock

from analytics_mcp.tools import client

_OAUTH_ENV = {
    "ANALYTICS_MCP_OAUTH_CLIENT_ID": "test-client-id",
    "ANALYTICS_MCP_OAUTH_CLIENT_SECRET": "test-client-secret",
}


class TestOAuthMode(unittest.TestCase):
    """Test cases for OAuth-mode detection and fail-closed behavior."""

    def test_oauth_mode_disabled_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(client._is_oauth_mode())

    def test_oauth_mode_requires_both_env_vars(self):
        for partial in (
            {"ANALYTICS_MCP_OAUTH_CLIENT_ID": "test-client-id"},
            {"ANALYTICS_MCP_OAUTH_CLIENT_SECRET": "test-client-secret"},
        ):
            with mock.patch.dict(os.environ, partial, clear=True):
                self.assertFalse(client._is_oauth_mode())

    def test_oauth_mode_enabled_with_both_env_vars(self):
        with mock.patch.dict(os.environ, _OAUTH_ENV, clear=True):
            self.assertTrue(client._is_oauth_mode())

    def test_fails_closed_without_request_token(self):
        """In OAuth mode a missing per-request token must raise.

        Falling back to Application Default Credentials would serve the
        server operator's Analytics data to the calling user.
        """
        with mock.patch.dict(os.environ, _OAUTH_ENV):
            # Outside of a FastMCP request context, get_access_token()
            # returns None, so credential resolution must fail.
            with self.assertRaises(RuntimeError):
                client._get_credentials()

    def test_uses_request_token_in_oauth_mode(self):
        token = mock.Mock()
        token.token = "test-access-token"
        with mock.patch.dict(os.environ, _OAUTH_ENV):
            with mock.patch(
                "fastmcp.server.dependencies.get_access_token",
                return_value=token,
            ):
                credentials = client._get_credentials()
        self.assertEqual(credentials.token, "test-access-token")

    def test_never_uses_adc_in_oauth_mode(self):
        with mock.patch.dict(os.environ, _OAUTH_ENV):
            with mock.patch(
                "google.auth.default",
                side_effect=AssertionError(
                    "google.auth.default must not be called in OAuth mode"
                ),
            ):
                with self.assertRaises(RuntimeError):
                    client._get_credentials()


if __name__ == "__main__":
    unittest.main()
