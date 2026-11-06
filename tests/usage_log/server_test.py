from unittest.mock import patch

import pytest

from analytics_mcp import server
from analytics_mcp.tools import client

OAUTH_ENV = {
    "GOOGLE_OAUTH_CLIENT_ID": "test-id",
    "GOOGLE_OAUTH_CLIENT_SECRET": "test-secret",
}
HTTP_OAUTH_ARGS = ["--transport", "http", "--oauth", "--usage-log"]


@pytest.fixture(autouse=True)
def reset_client_policy():
    yield
    client.set_allow_write(False)
    client.set_require_request_credentials(False)


def test_usage_log_is_off_by_default():
    with patch.dict("os.environ", {"ANALYTICS_MCP_USAGE_LOG": ""}):
        assert server.parse_args([]).usage_log is False


def test_usage_log_flag_from_cli():
    assert server.parse_args(["--usage-log"]).usage_log is True


def test_usage_log_flag_from_env():
    with patch.dict("os.environ", {"ANALYTICS_MCP_USAGE_LOG": "true"}):
        assert server.parse_args([]).usage_log is True


def test_http_app_without_dsn_refuses_to_start():
    args = server.parse_args(HTTP_OAUTH_ARGS)
    with patch.dict("os.environ", {**OAUTH_ENV, "MCP_USAGE_DSN": ""}):
        with pytest.raises(RuntimeError, match="MCP_USAGE_DSN"):
            server.build_http_app(args)


def test_http_app_with_dsn_serves_oauth_and_mcp():
    args = server.parse_args(HTTP_OAUTH_ARGS)
    env = {
        **OAUTH_ENV,
        "MCP_USAGE_DSN": "postgresql://usage@db/mcp_usage?sslmode=require",
    }
    with patch.dict("os.environ", env):
        app = server.build_http_app(args)

    route_paths = [getattr(route, "path", None) for route in app.routes]
    assert "/mcp" in route_paths
    assert "/oauth/callback" in route_paths
