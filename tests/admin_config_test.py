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

"""Test cases for the admin config tools, using a mocked Admin API client."""

import unittest
from unittest import mock

from google.analytics import admin_v1beta
from google.api_core import exceptions as gexc

from analytics_mcp.tools.admin import config

_FACTORY = "analytics_mcp.tools.admin.config.create_admin_api_client"
_PROPERTY = 12345


class TestCreateCustomDimension(unittest.IsolatedAsyncioTestCase):
    """Test cases for create_custom_dimension."""

    async def test_dry_run_by_default(self):
        with mock.patch(_FACTORY) as factory:
            result = await config.create_custom_dimension(
                _PROPERTY, "plan_tier"
            )
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["parent"], "properties/12345")
        self.assertEqual(
            result["body"],
            {
                "parameter_name": "plan_tier",
                "display_name": "plan_tier",
                "scope": "EVENT",
            },
        )
        self.assertEqual(result["validation_problems"], [])
        factory.assert_not_called()

    async def test_string_confirm_is_still_dry_run(self):
        with mock.patch(_FACTORY) as factory:
            result = await config.create_custom_dimension(
                _PROPERTY, "plan_tier", confirm="true"
            )
        self.assertTrue(result["dry_run"])
        factory.assert_not_called()

    async def test_invalid_input_is_dry_run_even_when_confirmed(self):
        cases = [
            {"parameter_name": "1bad"},
            {"parameter_name": "has-dash"},
            {"parameter_name": "a" * 41},
            {"parameter_name": "a" * 25, "scope": "USER"},
            {"parameter_name": "ok", "scope": "BOGUS"},
            {"parameter_name": "ok", "disallow_ads_personalization": True},
            {"parameter_name": "ok", "description": "d" * 151},
        ]
        for kwargs in cases:
            with self.subTest(**kwargs), mock.patch(_FACTORY) as factory:
                result = await config.create_custom_dimension(
                    _PROPERTY, confirm=True, **kwargs
                )
                self.assertTrue(result["dry_run"])
                self.assertTrue(result["validation_problems"])
                factory.assert_not_called()

    async def test_confirmed_create(self):
        with mock.patch(_FACTORY) as factory:
            client = factory.return_value
            client.create_custom_dimension.return_value = (
                admin_v1beta.CustomDimension(
                    name="properties/12345/customDimensions/1",
                    parameter_name="plan_tier",
                    display_name="plan_tier",
                    scope="EVENT",
                )
            )
            result = await config.create_custom_dimension(
                _PROPERTY, "plan_tier", confirm=True
            )
        client.create_custom_dimension.assert_called_once()
        request = client.create_custom_dimension.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(request.custom_dimension.parameter_name, "plan_tier")
        self.assertEqual(request.custom_dimension.display_name, "plan_tier")
        self.assertEqual(
            request.custom_dimension.scope,
            admin_v1beta.CustomDimension.DimensionScope.EVENT,
        )
        self.assertEqual(result["status"], "created")
        self.assertEqual(
            result["custom_dimension"]["name"],
            "properties/12345/customDimensions/1",
        )
        self.assertEqual(result["custom_dimension"]["scope"], "EVENT")

    async def _confirmed_with_error(self, error):
        with mock.patch(_FACTORY) as factory:
            factory.return_value.create_custom_dimension.side_effect = error
            return await config.create_custom_dimension(
                _PROPERTY, "plan_tier", confirm=True
            )

    async def test_already_exists(self):
        result = await self._confirmed_with_error(gexc.AlreadyExists("dup"))
        self.assertEqual(result["status"], "already_exists")

    async def test_permission_denied_scope_hint(self):
        result = await self._confirmed_with_error(
            gexc.PermissionDenied(
                "Request had insufficient authentication scopes."
            )
        )
        self.assertEqual(result["status"], "permission_denied")
        self.assertIn("ANALYTICS_MCP_ENABLE_WRITES", result["hint"])

    async def test_permission_denied_role_hint(self):
        result = await self._confirmed_with_error(
            gexc.PermissionDenied("User does not have sufficient permissions")
        )
        self.assertEqual(result["status"], "permission_denied")
        self.assertIn("Editor", result["hint"])

    async def test_rejected(self):
        for error in (
            gexc.InvalidArgument("bad"),
            gexc.FailedPrecondition("bad"),
            gexc.ResourceExhausted("limit"),
        ):
            with self.subTest(error=type(error).__name__):
                result = await self._confirmed_with_error(error)
                self.assertEqual(result["status"], "rejected")

    async def test_unexpected_error_is_raised(self):
        with self.assertRaises(gexc.InternalServerError):
            await self._confirmed_with_error(gexc.InternalServerError("boom"))


class TestCreateKeyEvent(unittest.IsolatedAsyncioTestCase):
    """Test cases for create_key_event."""

    async def test_dry_run_by_default(self):
        with mock.patch(_FACTORY) as factory:
            result = await config.create_key_event(_PROPERTY, "referral_click")
        self.assertTrue(result["dry_run"])
        self.assertEqual(
            result["body"],
            {
                "event_name": "referral_click",
                "counting_method": "ONCE_PER_EVENT",
            },
        )
        self.assertEqual(result["validation_problems"], [])
        factory.assert_not_called()

    async def test_default_value_requires_currency(self):
        with mock.patch(_FACTORY) as factory:
            result = await config.create_key_event(
                _PROPERTY, "referral_click", default_value=1.5, confirm=True
            )
        self.assertTrue(result["dry_run"])
        self.assertTrue(result["validation_problems"])
        factory.assert_not_called()

    async def test_invalid_counting_method(self):
        with mock.patch(_FACTORY) as factory:
            result = await config.create_key_event(
                _PROPERTY,
                "referral_click",
                counting_method="NOPE",
                confirm=True,
            )
        self.assertTrue(result["dry_run"])
        self.assertTrue(result["validation_problems"])
        factory.assert_not_called()

    async def test_confirmed_create(self):
        with mock.patch(_FACTORY) as factory:
            client = factory.return_value
            client.create_key_event.return_value = admin_v1beta.KeyEvent(
                name="properties/12345/keyEvents/2",
                event_name="sample_submit",
                counting_method="ONCE_PER_SESSION",
            )
            result = await config.create_key_event(
                _PROPERTY,
                "sample_submit",
                counting_method="ONCE_PER_SESSION",
                default_value=2.5,
                default_currency_code="EUR",
                confirm=True,
            )
        request = client.create_key_event.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(request.key_event.event_name, "sample_submit")
        self.assertEqual(
            request.key_event.counting_method,
            admin_v1beta.KeyEvent.CountingMethod.ONCE_PER_SESSION,
        )
        self.assertEqual(request.key_event.default_value.numeric_value, 2.5)
        self.assertEqual(request.key_event.default_value.currency_code, "EUR")
        self.assertEqual(result["status"], "created")
        self.assertEqual(
            result["key_event"]["counting_method"], "ONCE_PER_SESSION"
        )

    async def test_already_exists(self):
        with mock.patch(_FACTORY) as factory:
            factory.return_value.create_key_event.side_effect = (
                gexc.AlreadyExists("dup")
            )
            result = await config.create_key_event(
                _PROPERTY, "referral_click", confirm=True
            )
        self.assertEqual(result["status"], "already_exists")


class TestListKeyEvents(unittest.IsolatedAsyncioTestCase):
    """Test cases for list_key_events."""

    async def test_list_key_events(self):
        with mock.patch(_FACTORY) as factory:
            client = factory.return_value
            client.list_key_events.return_value = iter(
                [
                    admin_v1beta.KeyEvent(
                        event_name="purchase", counting_method="ONCE_PER_EVENT"
                    ),
                    admin_v1beta.KeyEvent(
                        event_name="sign_up", counting_method="ONCE_PER_SESSION"
                    ),
                ]
            )
            result = await config.list_key_events(f"properties/{_PROPERTY}")
        request = client.list_key_events.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(
            [(k["event_name"], k["counting_method"]) for k in result],
            [("purchase", "ONCE_PER_EVENT"), ("sign_up", "ONCE_PER_SESSION")],
        )


if __name__ == "__main__":
    unittest.main()
