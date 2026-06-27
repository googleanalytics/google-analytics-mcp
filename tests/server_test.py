import unittest
from unittest.mock import patch

from analytics_mcp import server


class ServerVersionTest(unittest.TestCase):
    @patch("analytics_mcp.server.metadata.version", return_value="0.6.0")
    def test_server_version_uses_installed_package_version(self, version_mock):
        self.assertEqual(server._server_version(), "0.6.0")
        version_mock.assert_called_once_with("analytics-mcp")

    @patch(
        "analytics_mcp.server.metadata.version",
        side_effect=server.metadata.PackageNotFoundError,
    )
    def test_server_version_falls_back_when_package_metadata_missing(
        self, version_mock
    ):
        self.assertEqual(server._server_version(), "unknown")
        version_mock.assert_called_once_with("analytics-mcp")
