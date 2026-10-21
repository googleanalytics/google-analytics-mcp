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

"""Test cases for property annotations and --allow-write configuration."""

import unittest
from unittest.mock import MagicMock, patch

from analytics_mcp import coordinator, server
from analytics_mcp.tools import client
from analytics_mcp.tools.admin import info
from google.analytics import admin_v1alpha
from google.api_core import exceptions as google_exceptions
from google.type import date_pb2
from mcp import types as mcp_types


class TestCreatePropertyAnnotation(unittest.IsolatedAsyncioTestCase):
    """Test cases for create_property_annotation."""

    def tearDown(self):
        client.set_allow_write(False)

    @patch("analytics_mcp.tools.admin.info.create_admin_alpha_api_client")
    async def test_create_single_date_annotation(self, mock_create_client):
        """Tests creating a single-date annotation."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.create_reporting_data_annotation.return_value = (
            admin_v1alpha.ReportingDataAnnotation(
                name="properties/12345/reportingDataAnnotations/999",
                title="GTM Container Published",
                description="Published version 42",
                color=admin_v1alpha.ReportingDataAnnotation.Color.BLUE,
                annotation_date=date_pb2.Date(year=2026, month=10, day=21),
            )
        )

        result = await info.create_property_annotation(
            property_id=12345,
            title="GTM Container Published",
            start_date="2026-10-21",
            color="blue",
            description="Published version 42",
        )

        self.assertEqual(
            result["name"],
            "properties/12345/reportingDataAnnotations/999",
        )
        self.assertEqual(result["title"], "GTM Container Published")
        self.assertEqual(result["color"], "BLUE")
        self.assertEqual(
            result["annotation_date"],
            {"year": 2026, "month": 10, "day": 21},
        )

        mock_client.create_reporting_data_annotation.assert_called_once()
        call_kwargs = (
            mock_client.create_reporting_data_annotation.call_args.kwargs
        )
        req = call_kwargs["request"]
        self.assertEqual(req.parent, "properties/12345")
        self.assertEqual(
            req.reporting_data_annotation.title, "GTM Container Published"
        )
        self.assertEqual(
            req.reporting_data_annotation.color,
            admin_v1alpha.ReportingDataAnnotation.Color.BLUE,
        )
        self.assertEqual(
            req.reporting_data_annotation.annotation_date,
            date_pb2.Date(year=2026, month=10, day=21),
        )

    @patch("analytics_mcp.tools.admin.info.create_admin_alpha_api_client")
    async def test_create_date_range_annotation(self, mock_create_client):
        """Tests creating a date-range annotation."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.create_reporting_data_annotation.return_value = (
            admin_v1alpha.ReportingDataAnnotation(
                name="properties/12345/reportingDataAnnotations/1000",
                title="Holiday Promo",
                color=admin_v1alpha.ReportingDataAnnotation.Color.GREEN,
                annotation_date_range=(
                    admin_v1alpha.ReportingDataAnnotation.DateRange(
                        start_date=date_pb2.Date(year=2026, month=10, day=20),
                        end_date=date_pb2.Date(year=2026, month=10, day=25),
                    )
                ),
            )
        )

        result = await info.create_property_annotation(
            property_id="properties/12345",
            title="Holiday Promo",
            start_date="2026-10-20",
            end_date="2026-10-25",
            color="GREEN",
        )

        self.assertEqual(result["title"], "Holiday Promo")
        self.assertEqual(result["color"], "GREEN")
        self.assertEqual(
            result["annotation_date_range"],
            {
                "start_date": {"year": 2026, "month": 10, "day": 20},
                "end_date": {"year": 2026, "month": 10, "day": 25},
            },
        )

    async def test_create_property_annotation_validation(self):
        """Tests validation errors for invalid inputs."""
        with self.assertRaisesRegex(ValueError, "title must be a non-empty"):
            await info.create_property_annotation(
                property_id=12345,
                title="   ",
                start_date="2026-10-21",
            )

        with self.assertRaisesRegex(
            ValueError, "title must be at most 60 characters"
        ):
            await info.create_property_annotation(
                property_id=12345,
                title="a" * 61,
                start_date="2026-10-21",
            )

        with self.assertRaisesRegex(
            ValueError, "description must be at most 150 characters"
        ):
            await info.create_property_annotation(
                property_id=12345,
                title="Release",
                start_date="2026-10-21",
                description="a" * 151,
            )

        with self.assertRaisesRegex(ValueError, "Invalid color"):
            await info.create_property_annotation(
                property_id=12345,
                title="Release",
                start_date="2026-10-21",
                color="ORANGE",
            )

        with self.assertRaisesRegex(ValueError, "Expected YYYY-MM-DD"):
            await info.create_property_annotation(
                property_id=12345,
                title="Release",
                start_date="10/21/2026",
            )

        with self.assertRaisesRegex(
            ValueError, "end_date .* must be greater than or equal"
        ):
            await info.create_property_annotation(
                property_id=12345,
                title="Release",
                start_date="2026-10-21",
                end_date="2026-10-20",
            )

    @patch("analytics_mcp.tools.admin.info.create_admin_alpha_api_client")
    async def test_mcp_handlers_list_and_call_tool(self, mock_create_client):
        """Tests MCP v2 list_tools and call_mcp_tool handlers."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.create_reporting_data_annotation.return_value = (
            admin_v1alpha.ReportingDataAnnotation(
                name="properties/12345/reportingDataAnnotations/999",
                title="GTM Release",
                color=admin_v1alpha.ReportingDataAnnotation.Color.BLUE,
                annotation_date=date_pb2.Date(year=2026, month=10, day=21),
            )
        )

        # In read-only mode, calling create_property_annotation should fail
        ro_server = coordinator.create_server(allow_write=False)
        ro_call_handler = ro_server.get_request_handler("tools/call").handler
        ro_call_res = await ro_call_handler(
            None,
            mcp_types.CallToolRequestParams(
                name="create_property_annotation",
                arguments={
                    "property_id": 12345,
                    "title": "GTM Release",
                    "start_date": "2026-10-21",
                },
            ),
        )
        self.assertTrue(ro_call_res.is_error)
        self.assertIn("--allow-write", ro_call_res.content[0].text)

        # Enable write mode and verify list_tools and call_mcp_tool
        rw_server = coordinator.create_server(allow_write=True)
        rw_list_handler = rw_server.get_request_handler("tools/list").handler
        rw_call_handler = rw_server.get_request_handler("tools/call").handler
        list_res = await rw_list_handler(None, None)
        tool_names = [t.name for t in list_res.tools]
        self.assertIn("create_property_annotation", tool_names)

        rw_call_res = await rw_call_handler(
            None,
            mcp_types.CallToolRequestParams(
                name="create_property_annotation",
                arguments={
                    "property_id": 12345,
                    "title": "GTM Release",
                    "start_date": "2026-10-21",
                },
            ),
        )
        self.assertFalse(rw_call_res.is_error)
        self.assertIn("GTM Release", rw_call_res.content[0].text)

        # Verify 403 PermissionDenied on a write tool includes actionable scope hint
        mock_client.create_reporting_data_annotation.side_effect = (
            google_exceptions.PermissionDenied(
                "Request had insufficient authentication scopes."
            )
        )
        err_call_res = await rw_call_handler(
            None,
            mcp_types.CallToolRequestParams(
                name="create_property_annotation",
                arguments={
                    "property_id": 12345,
                    "title": "GTM Release",
                    "start_date": "2026-10-21",
                },
            ),
        )
        self.assertTrue(err_call_res.is_error)
        self.assertIn("analytics.edit", err_call_res.content[0].text)
        self.assertIn(
            "gcloud auth application-default login",
            err_call_res.content[0].text,
        )


class TestAllowWriteConfiguration(unittest.IsolatedAsyncioTestCase):
    """Tests for --allow-write CLI flag, tool registration, and OAuth scopes."""

    def tearDown(self):
        client.set_allow_write(False)

    def test_parse_args(self):
        """Tests CLI argument parsing for --allow-write."""
        args_default = server.parse_args([])
        self.assertFalse(args_default.allow_write)

        args_write = server.parse_args(["--allow-write"])
        self.assertTrue(args_write.allow_write)

    async def test_create_server_toggles_write_tools(self):
        """Tests that write tools are only registered when allow_write=True."""
        ro_server = coordinator.create_server(allow_write=False)
        ro_list = await ro_server.get_request_handler("tools/list").handler(
            None, None
        )
        mcp_names_ro = [t.name for t in ro_list.tools]
        self.assertNotIn("create_property_annotation", mcp_names_ro)

        rw_server = coordinator.create_server(allow_write=True)
        rw_list = await rw_server.get_request_handler("tools/list").handler(
            None, None
        )
        mcp_names_rw = [t.name for t in rw_list.tools]
        self.assertIn("create_property_annotation", mcp_names_rw)

    async def test_mcp_tool_annotations(self):
        """Tests that MCP tools carry appropriate ToolAnnotations."""
        rw_server = coordinator.create_server(allow_write=True)
        rw_list = await rw_server.get_request_handler("tools/list").handler(
            None, None
        )
        self.assertEqual(
            len({id(t.annotations) for t in rw_list.tools}),
            len(rw_list.tools),
            "Each tool should have its own ToolAnnotations instance",
        )
        for mcp_tool in rw_list.tools:
            self.assertIsNotNone(mcp_tool.annotations)
            dumped = mcp_tool.annotations.model_dump(
                by_alias=True, exclude_none=True
            )
            if mcp_tool.name == "create_property_annotation":
                self.assertEqual(
                    dumped,
                    {
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": False,
                        "openWorldHint": True,
                    },
                )
            else:
                self.assertEqual(
                    dumped,
                    {
                        "readOnlyHint": True,
                        "destructiveHint": False,
                        "openWorldHint": True,
                    },
                )

    @patch("analytics_mcp.tools.client.google.auth.default")
    def test_credentials_scopes_respect_allow_write(self, mock_auth_default):
        """Tests that google.auth.default requests edit scope only when enabled."""
        mock_auth_default.return_value = (MagicMock(), "test-project")
        manager = client._ClientManager()

        manager.set_allow_write(False)
        manager._get_credentials()
        mock_auth_default.assert_called_with(
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )

        manager.set_allow_write(True)
        manager._get_credentials()
        mock_auth_default.assert_called_with(
            scopes=[
                "https://www.googleapis.com/auth/analytics.readonly",
                "https://www.googleapis.com/auth/analytics.edit",
            ]
        )
