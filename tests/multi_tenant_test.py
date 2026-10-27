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

"""Tests for multi-tenant HTTP mode, per-request credentials, and OAuth 2.1."""

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

from analytics_mcp import coordinator, oauth, server
from analytics_mcp.tools import client
from google.analytics import admin_v1beta
from mcp import types as mcp_types
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl


def _make_ctx_with_bearer(token: str | None):
    """Creates a minimal fake ServerRequestContext with HTTP headers."""
    headers = {}
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    return SimpleNamespace(request=SimpleNamespace(headers=headers))


class TestMultiTenantCredentials(unittest.IsolatedAsyncioTestCase):
    """Tests per-request credential isolation and HTTP mode enforcement."""

    def tearDown(self):
        client.set_allow_write(False)
        client.set_require_request_credentials(False)

    @patch("analytics_mcp.tools.client.google.auth.default")
    @patch(
        "analytics_mcp.tools.client.admin_v1beta.AnalyticsAdminServiceClient"
    )
    async def test_concurrent_tenant_token_isolation(
        self, mock_admin_client_cls, mock_auth_default
    ):
        """Verifies concurrent tool calls isolate each tenant's Bearer token."""
        captured_tokens = []

        def make_admin_client(*, client_info, credentials):
            mock_instance = MagicMock()

            def list_summaries():
                captured_tokens.append(
                    (credentials.token, tuple(credentials.scopes or ()))
                )
                return [
                    admin_v1beta.AccountSummary(
                        name=f"accountSummaries/{credentials.token}",
                        display_name=f"Tenant {credentials.token}",
                    )
                ]

            mock_instance.list_account_summaries.side_effect = list_summaries
            return mock_instance

        mock_admin_client_cls.side_effect = make_admin_client

        mcp_server = coordinator.create_server(
            allow_write=True,
            require_request_credentials=True,
        )
        call_handler = mcp_server.get_request_handler("tools/call").handler

        res_a, res_b = await asyncio.gather(
            call_handler(
                _make_ctx_with_bearer("tenant-a-token"),
                mcp_types.CallToolRequestParams(
                    name="get_account_summaries", arguments={}
                ),
            ),
            call_handler(
                _make_ctx_with_bearer("tenant-b-token"),
                mcp_types.CallToolRequestParams(
                    name="get_account_summaries", arguments={}
                ),
            ),
        )

        self.assertFalse(res_a.is_error)
        self.assertFalse(res_b.is_error)
        self.assertIn("Tenant tenant-a-token", res_a.content[0].text)
        self.assertIn("Tenant tenant-b-token", res_b.content[0].text)

        # Verify host ADC was never touched
        mock_auth_default.assert_not_called()

        expected_scopes = (
            "https://www.googleapis.com/auth/analytics.readonly",
            "https://www.googleapis.com/auth/analytics.edit",
        )
        self.assertCountEqual(
            captured_tokens,
            [
                ("tenant-a-token", expected_scopes),
                ("tenant-b-token", expected_scopes),
            ],
        )

    @patch("analytics_mcp.tools.client.google.auth.default")
    async def test_http_mode_rejects_missing_bearer_token(
        self, mock_auth_default
    ):
        """Verifies HTTP mode rejects unauthenticated tool calls without ADC fallback."""
        mcp_server = coordinator.create_server(
            allow_write=False,
            require_request_credentials=True,
        )
        call_handler = mcp_server.get_request_handler("tools/call").handler

        res = await call_handler(
            _make_ctx_with_bearer(None),
            mcp_types.CallToolRequestParams(
                name="get_account_summaries", arguments={}
            ),
        )
        self.assertTrue(res.is_error)
        self.assertIn("Missing OAuth access token", res.content[0].text)
        mock_auth_default.assert_not_called()

        # Direct client call without contextvar also raises MissingCredentialsError
        with self.assertRaises(client.MissingCredentialsError):
            client.create_admin_api_client()

    @patch("analytics_mcp.tools.client.google.auth.default")
    @patch(
        "analytics_mcp.tools.client.admin_v1beta.AnalyticsAdminServiceClient"
    )
    async def test_stdio_mode_uses_adc_by_default(
        self, mock_admin_client_cls, mock_auth_default
    ):
        """Verifies default stdio mode continues to use ADC with no breaking changes."""
        args = server.parse_args([])
        self.assertEqual(args.transport, "stdio")
        self.assertFalse(args.allow_write)
        self.assertFalse(args.oauth)

        mock_adc_creds = MagicMock(name="adc_credentials")
        mock_auth_default.return_value = (mock_adc_creds, "test-project")

        mock_instance = MagicMock()
        mock_instance.list_account_summaries.return_value = [
            admin_v1beta.AccountSummary(
                name="accountSummaries/123",
                display_name="ADC Account",
            )
        ]
        mock_admin_client_cls.return_value = mock_instance

        # Reset cached ADC on the singleton manager to verify google.auth.default call
        client._client_manager._credentials = None
        mcp_server = coordinator.create_server(allow_write=args.allow_write)
        call_handler = mcp_server.get_request_handler("tools/call").handler

        # In stdio mode, ctx has no HTTP request object
        res = await call_handler(
            SimpleNamespace(request=None),
            mcp_types.CallToolRequestParams(
                name="get_account_summaries", arguments={}
            ),
        )
        self.assertFalse(res.is_error)
        self.assertIn("ADC Account", res.content[0].text)
        mock_auth_default.assert_called_once_with(
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        mock_admin_client_cls.assert_called_once_with(
            client_info=client._CLIENT_INFO,
            credentials=mock_adc_creds,
        )


class TestGoogleOAuthProvider(unittest.IsolatedAsyncioTestCase):
    """Tests the built-in MCP OAuth 2.1 Google OAuth provider."""

    def tearDown(self):
        client.set_allow_write(False)
        client.set_require_request_credentials(False)

    async def test_oauth_authorization_and_token_exchange_flow(self):
        """Tests full dynamic client registration, authorize, callback, and token exchange."""
        provider = oauth.GoogleOAuthProvider(
            google_client_id="google-client-id",
            google_client_secret="google-client-secret",
            issuer_url="http://127.0.0.1:8080",
            allow_write=True,
        )

        # 1. Register MCP client
        mcp_client = OAuthClientInformationFull(
            client_id="mcp-test-client",
            redirect_uris=[AnyUrl("http://localhost:3000/callback")],
        )
        await provider.register_client(mcp_client)
        self.assertEqual(
            await provider.get_client("mcp-test-client"), mcp_client
        )

        # 2. Authorize -> redirects to Google OAuth
        auth_params = AuthorizationParams(
            state="client-state-xyz",
            scopes=None,
            code_challenge="challenge-123",
            redirect_uri=AnyUrl("http://localhost:3000/callback"),
            redirect_uri_provided_explicitly=True,
        )
        google_redirect_url = await provider.authorize(mcp_client, auth_params)
        parsed = urlparse(google_redirect_url)
        self.assertEqual(parsed.netloc, "accounts.google.com")
        query = parse_qs(parsed.query)
        self.assertEqual(query["client_id"], ["google-client-id"])
        self.assertEqual(
            query["redirect_uri"], ["http://127.0.0.1:8080/oauth/callback"]
        )
        self.assertIn("analytics.edit", query["scope"][0])
        internal_state = query["state"][0]

        # 3. Handle Google OAuth callback
        fake_request = SimpleNamespace(
            query_params={
                "state": internal_state,
                "code": "google-auth-code-abc",
            }
        )
        with patch.object(
            provider,
            "_exchange_code_with_google",
            new=AsyncMock(
                return_value={
                    "access_token": "ya29.google-access-token",
                    "refresh_token": "1//google-refresh-token",
                    "expires_in": 3600,
                }
            ),
        ):
            callback_response = await provider.handle_oauth_callback(
                fake_request
            )

        self.assertEqual(callback_response.status_code, 302)
        client_redirect = urlparse(callback_response.headers["location"])
        client_query = parse_qs(client_redirect.query)
        self.assertEqual(client_query["state"], ["client-state-xyz"])
        mcp_code_str = client_query["code"][0]

        # 4. Exchange MCP authorization code for OAuth tokens
        code_obj = await provider.load_authorization_code(
            mcp_client, mcp_code_str
        )
        self.assertIsNotNone(code_obj)
        oauth_token = await provider.exchange_authorization_code(
            mcp_client, code_obj
        )
        self.assertEqual(oauth_token.access_token, "ya29.google-access-token")
        self.assertEqual(oauth_token.refresh_token, "1//google-refresh-token")

        # 5. Verify access token is loaded by verifier
        loaded_access = await provider.load_access_token(
            "ya29.google-access-token"
        )
        self.assertIsNotNone(loaded_access)
        self.assertEqual(loaded_access.client_id, "mcp-test-client")

    async def test_stateless_token_introspection_fallback(self):
        """Tests that load_access_token falls back to Google tokeninfo across instances."""
        provider = oauth.GoogleOAuthProvider(
            google_client_id="google-client-id",
            google_client_secret="google-client-secret",
            issuer_url="http://127.0.0.1:8080",
            allow_write=False,
        )
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "aud": "google-client-id",
            "scope": "https://www.googleapis.com/auth/analytics.readonly",
            "expires_in": "1800",
        }
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = fake_response
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_http_client

        with patch(
            "analytics_mcp.oauth.httpx.AsyncClient",
            return_value=mock_client_cm,
        ):
            loaded_access = await provider.load_access_token(
                "ya29.stateless-token"
            )
            self.assertIsNotNone(loaded_access)
            self.assertEqual(loaded_access.token, "ya29.stateless-token")
            self.assertEqual(
                loaded_access.scopes,
                ["https://www.googleapis.com/auth/analytics.readonly"],
            )
            mock_http_client.get.assert_awaited_once_with(
                oauth.GOOGLE_TOKENINFO_URL,
                params={"access_token": "ya29.stateless-token"},
            )

    def test_server_cli_and_build_http_app(self):
        """Tests CLI argument parsing and Starlette HTTP app construction."""
        args = server.parse_args(
            [
                "--transport",
                "http",
                "--host",
                "0.0.0.0",
                "--port",
                "9000",
                "--stateless-http",
                "--oauth",
                "--allow-write",
            ]
        )
        self.assertEqual(args.transport, "http")
        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 9000)
        self.assertTrue(args.stateless_http)
        self.assertTrue(args.oauth)
        self.assertTrue(args.allow_write)

        with patch.dict(
            "os.environ",
            {
                "GOOGLE_OAUTH_CLIENT_ID": "test-id",
                "GOOGLE_OAUTH_CLIENT_SECRET": "test-secret",
            },
        ):
            starlette_app = server.build_http_app(args)
            route_paths = [
                getattr(r, "path", None) for r in starlette_app.routes
            ]
            self.assertIn("/mcp", route_paths)
            self.assertIn("/oauth/callback", route_paths)
            self.assertIn("/authorize", route_paths)
            self.assertIn("/token", route_paths)
            self.assertIn("/register", route_paths)
