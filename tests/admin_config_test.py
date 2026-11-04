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

"""Test cases for the admin config tools: custom dimensions and key events."""

import unittest
from unittest.mock import MagicMock, patch

from analytics_mcp import coordinator
from analytics_mcp.tools import client
from analytics_mcp.tools.admin import config
from google.analytics import admin_v1beta
from google.api_core import exceptions as google_exceptions

_FACTORY = "analytics_mcp.tools.admin.config.create_admin_api_client"


class TestCreateCustomDimension(unittest.IsolatedAsyncioTestCase):
    """Test cases for create_custom_dimension."""

    @patch(_FACTORY)
    async def test_create_with_defaults(self, mock_create_client):
        """Tests creating an EVENT-scoped dimension with default arguments."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.create_custom_dimension.return_value = (
            admin_v1beta.CustomDimension(
                name="properties/12345/customDimensions/1",
                parameter_name="plan_tier",
                display_name="plan_tier",
                scope=admin_v1beta.CustomDimension.DimensionScope.EVENT,
            )
        )

        result = await config.create_custom_dimension(12345, "plan_tier")

        self.assertEqual(result["name"], "properties/12345/customDimensions/1")
        self.assertEqual(result["scope"], "EVENT")
        mock_client.create_custom_dimension.assert_called_once()
        request = mock_client.create_custom_dimension.call_args.kwargs[
            "request"
        ]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(request.custom_dimension.parameter_name, "plan_tier")
        self.assertEqual(request.custom_dimension.display_name, "plan_tier")
        self.assertEqual(
            request.custom_dimension.scope,
            admin_v1beta.CustomDimension.DimensionScope.EVENT,
        )

    @patch(_FACTORY)
    async def test_create_user_scope_with_all_fields(self, mock_create_client):
        """Tests that scope is normalized and optional fields are sent."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.create_custom_dimension.return_value = (
            admin_v1beta.CustomDimension()
        )

        await config.create_custom_dimension(
            "properties/12345",
            "plan_tier",
            display_name="Előfizetés",
            scope=" user ",
            description="Customer plan",
            disallow_ads_personalization=True,
        )

        request = mock_client.create_custom_dimension.call_args.kwargs[
            "request"
        ]
        dimension = request.custom_dimension
        self.assertEqual(dimension.display_name, "Előfizetés")
        self.assertEqual(
            dimension.scope, admin_v1beta.CustomDimension.DimensionScope.USER
        )
        self.assertEqual(dimension.description, "Customer plan")
        self.assertTrue(dimension.disallow_ads_personalization)

    @patch(_FACTORY)
    async def test_invalid_input_raises_before_any_api_call(
        self, mock_create_client
    ):
        """Tests that validation errors raise ValueError without a client."""
        cases = [
            ({"parameter_name": "1bad"}, "parameter_name must be"),
            ({"parameter_name": "has-dash"}, "parameter_name must be"),
            ({"parameter_name": "a" * 41}, "at most 40 characters"),
            (
                {"parameter_name": "a" * 25, "scope": "USER"},
                "at most 24 characters",
            ),
            ({"parameter_name": "ok", "scope": "BOGUS"}, "Invalid scope"),
            (
                {"parameter_name": "ok", "display_name": "  "},
                "display_name must be a non-empty",
            ),
            (
                {"parameter_name": "ok", "display_name": "d" * 83},
                "display_name must be at most 82",
            ),
            (
                {"parameter_name": "ok", "description": "d" * 151},
                "description must be at most 150",
            ),
            (
                {"parameter_name": "ok", "disallow_ads_personalization": True},
                "only valid for USER scope",
            ),
        ]
        for kwargs, message in cases:
            with self.subTest(**kwargs):
                with self.assertRaisesRegex(ValueError, message):
                    await config.create_custom_dimension(12345, **kwargs)
        mock_create_client.assert_not_called()

    @patch(_FACTORY)
    async def test_api_errors_propagate(self, mock_create_client):
        """Tests that API errors reach the coordinator unchanged."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        for error in (
            google_exceptions.AlreadyExists("dup"),
            google_exceptions.PermissionDenied("no access"),
            google_exceptions.InvalidArgument("bad"),
            google_exceptions.ResourceExhausted("limit"),
        ):
            with self.subTest(error=type(error).__name__):
                mock_client.create_custom_dimension.side_effect = error
                with self.assertRaises(type(error)):
                    await config.create_custom_dimension(12345, "plan_tier")


class TestCreateKeyEvent(unittest.IsolatedAsyncioTestCase):
    """Test cases for create_key_event."""

    @patch(_FACTORY)
    async def test_create_with_defaults(self, mock_create_client):
        """Tests creating a key event with default arguments."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.create_key_event.return_value = admin_v1beta.KeyEvent(
            name="properties/12345/keyEvents/2",
            event_name="referral_click",
            counting_method=admin_v1beta.KeyEvent.CountingMethod.ONCE_PER_EVENT,
        )

        result = await config.create_key_event(12345, "referral_click")

        self.assertEqual(result["name"], "properties/12345/keyEvents/2")
        self.assertEqual(result["counting_method"], "ONCE_PER_EVENT")
        request = mock_client.create_key_event.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(request.key_event.event_name, "referral_click")
        self.assertEqual(
            request.key_event.counting_method,
            admin_v1beta.KeyEvent.CountingMethod.ONCE_PER_EVENT,
        )
        self.assertFalse(request.key_event.default_value.currency_code)

    @patch(_FACTORY)
    async def test_create_with_default_value(self, mock_create_client):
        """Tests that counting_method is normalized and default value sent."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.create_key_event.return_value = admin_v1beta.KeyEvent()

        await config.create_key_event(
            12345,
            "sample_submit",
            counting_method=" once_per_session ",
            default_value=2.5,
            default_currency_code="EUR",
        )

        request = mock_client.create_key_event.call_args.kwargs["request"]
        self.assertEqual(
            request.key_event.counting_method,
            admin_v1beta.KeyEvent.CountingMethod.ONCE_PER_SESSION,
        )
        self.assertEqual(request.key_event.default_value.numeric_value, 2.5)
        self.assertEqual(request.key_event.default_value.currency_code, "EUR")

    @patch(_FACTORY)
    async def test_invalid_input_raises_before_any_api_call(
        self, mock_create_client
    ):
        """Tests that validation errors raise ValueError without a client."""
        cases = [
            ({"event_name": "1bad"}, "event_name must be"),
            ({"event_name": "a" * 41}, "at most 40 characters"),
            (
                {"event_name": "ok", "counting_method": "NOPE"},
                "Invalid counting_method",
            ),
            (
                {"event_name": "ok", "default_value": 1.5},
                "must be given together",
            ),
            (
                {"event_name": "ok", "default_currency_code": "EUR"},
                "must be given together",
            ),
        ]
        for kwargs, message in cases:
            with self.subTest(**kwargs):
                with self.assertRaisesRegex(ValueError, message):
                    await config.create_key_event(12345, **kwargs)
        mock_create_client.assert_not_called()

    @patch(_FACTORY)
    async def test_api_errors_propagate(self, mock_create_client):
        """Tests that API errors reach the coordinator unchanged."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.create_key_event.side_effect = (
            google_exceptions.AlreadyExists("dup")
        )

        with self.assertRaises(google_exceptions.AlreadyExists):
            await config.create_key_event(12345, "referral_click")


class TestListKeyEvents(unittest.IsolatedAsyncioTestCase):
    """Test cases for list_key_events."""

    @patch(_FACTORY)
    async def test_list_key_events(self, mock_create_client):
        """Tests listing key events."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_key_events.return_value = iter(
            [
                admin_v1beta.KeyEvent(
                    event_name="purchase",
                    counting_method=(
                        admin_v1beta.KeyEvent.CountingMethod.ONCE_PER_EVENT
                    ),
                ),
                admin_v1beta.KeyEvent(
                    event_name="sign_up",
                    counting_method=(
                        admin_v1beta.KeyEvent.CountingMethod.ONCE_PER_SESSION
                    ),
                ),
            ]
        )

        result = await config.list_key_events("properties/12345")

        request = mock_client.list_key_events.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(
            [(k["event_name"], k["counting_method"]) for k in result],
            [("purchase", "ONCE_PER_EVENT"), ("sign_up", "ONCE_PER_SESSION")],
        )


class TestConfigToolRegistration(unittest.IsolatedAsyncioTestCase):
    """Test cases for --allow-write registration of the config tools."""

    def tearDown(self):
        client.set_allow_write(False)

    async def _tool_names(self, allow_write):
        server = coordinator.create_server(allow_write=allow_write)
        result = await server.get_request_handler("tools/list").handler(
            None, None
        )
        return {t.name for t in result.tools}

    async def test_write_tools_hidden_by_default(self):
        """Tests that only the read-only list_key_events is registered."""
        names = await self._tool_names(False)
        self.assertIn("list_key_events", names)
        self.assertNotIn("create_custom_dimension", names)
        self.assertNotIn("create_key_event", names)

    async def test_write_tools_registered_with_allow_write(self):
        """Tests that the create_* tools are registered with allow_write."""
        names = await self._tool_names(True)
        self.assertIn("create_custom_dimension", names)
        self.assertIn("create_key_event", names)


if __name__ == "__main__":
    unittest.main()
