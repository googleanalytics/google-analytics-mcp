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

"""Client initialization for the Google Analytics APIs."""

import contextlib
import contextvars
import os
import subprocess
import threading
from importlib import metadata
from unittest.mock import patch

import google.auth
from google.analytics import (
    admin_v1beta,
    admin_v1alpha,
    data_v1alpha,
    data_v1beta,
)
from google.api_core.gapic_v1.client_info import ClientInfo
from google.oauth2 import credentials as oauth2_credentials


def _get_package_version_with_fallback():
    """Returns the version of the package.

    Falls back to 'unknown' if the version can't be resolved.
    """
    try:
        return metadata.version("analytics-mcp")
    except:
        return "unknown"


# Client information that adds a custom user agent to all API requests.
_CLIENT_INFO = ClientInfo(
    user_agent=f"analytics-mcp/{_get_package_version_with_fallback()}"
)

# Read-only scope for Analytics Admin API and Analytics Data API.
_READ_ONLY_ANALYTICS_SCOPE = (
    "https://www.googleapis.com/auth/analytics.readonly"
)

# Lock to ensure client and credential creation is thread-safe
_client_lock = threading.Lock()
_CREDENTIALS = None

# Per-request refresh token context. Populated by middleware from HTTP header
# x-ga-refresh-token when running over streamable-HTTP transport. Propagates
# correctly across asyncio tasks and asyncio.to_thread() workers.
_refresh_token_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "ga_refresh_token", default=None
)

# Header name used to carry the Google OAuth refresh token on inbound HTTP
# requests to the streamable-HTTP MCP endpoint.
REFRESH_TOKEN_HEADER = "x-ga-refresh-token"


def set_refresh_token(refresh_token: str) -> contextvars.Token:
    """Set the request-scoped OAuth refresh token.

    Returns the contextvars Token so the caller can reset the variable using
    :func:`clear_refresh_token` after the request is complete.
    """
    return _refresh_token_ctx.set(refresh_token)


def clear_refresh_token(token: contextvars.Token) -> None:
    """Reset the request-scoped refresh token using a prior Token."""
    _refresh_token_ctx.reset(token)


@contextlib.contextmanager
def prevent_stdio_inheritance():
    """Prevents child processes from inheriting the parent's stdio handles.

    Fixes a deadlock on Windows where `google.auth.default()` spawns `gcloud`
    via subprocess without redirecting stdin, causing it to inherit the
    ProactorEventLoop's overlapping I/O handles used by MCP's stdio transport.
    """
    original_popen = subprocess.Popen

    def safe_popen(*args, **kwargs):
        if kwargs.get("stdin") is None:
            kwargs["stdin"] = subprocess.DEVNULL
        return original_popen(*args, **kwargs)

    with patch("subprocess.Popen", new=safe_popen):
        yield


def _build_authorized_user_credentials(refresh_token: str):
    """Build Google OAuth credentials using a user-supplied refresh token.

    Equivalent in intent to the Node.js pattern:

        credentials = {
            type: "authorized_user",
            client_id: process.env.GOOGLE_ANALYTICS_CLIENT_ID,
            client_secret: process.env.GOOGLE_ANALYTICS_CLIENT_SECRET,
            refresh_token: <refresh_token>,
        }

    Raises ValueError with actionable message if either required env var is
    missing.
    """
    client_id = os.getenv("GOOGLE_ANALYTICS_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_ANALYTICS_CLIENT_SECRET")
    missing: list[str] = []
    if not client_id:
        missing.append("GOOGLE_ANALYTICS_CLIENT_ID")
    if not client_secret:
        missing.append("GOOGLE_ANALYTICS_CLIENT_SECRET")
    if missing:
        raise ValueError(
            "Cannot build Google authorized_user credentials: missing "
            "required environment variable(s): "
            + ", ".join(missing)
            + ". Please set these environment variables on the server process."
        )

    return oauth2_credentials.Credentials.from_authorized_user_info(
        info={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        scopes=[_READ_ONLY_ANALYTICS_SCOPE],
    )


def _get_default_credentials_cached():
    """Return the application-default credentials, cached in-process.

    Used as the fallback when no per-request refresh token is present (e.g.
    running over STDIO transport). Thread-safe.
    """
    global _CREDENTIALS
    if _CREDENTIALS is None:
        with _client_lock:
            if _CREDENTIALS is None:
                with prevent_stdio_inheritance():
                    _CREDENTIALS, _ = google.auth.default(
                        scopes=[_READ_ONLY_ANALYTICS_SCOPE]
                    )
    return _CREDENTIALS


def _get_credentials():
    """Return credentials for the current request.

    Priority:
      1. Per-request refresh token set via :func:`set_refresh_token`
         (HTTP transport).
      2. In-process cached application-default credentials
         (STDIO transport / local development).

    Per-request credentials are NOT cached module-globally to avoid leaking
    credentials across users/requests.
    """
    refresh_token = _refresh_token_ctx.get()
    if refresh_token:
        return _build_authorized_user_credentials(refresh_token)
    return _get_default_credentials_cached()


def create_admin_api_client(
    credentials=None,
) -> admin_v1beta.AnalyticsAdminServiceClient:
    """Returns the Google Analytics Admin API client.

    Args:
        credentials: Optional explicit credentials. If omitted, credentials
            are resolved from the per-request refresh token context or the
            application-default credentials cache.
    """
    creds = credentials if credentials is not None else _get_credentials()
    return admin_v1beta.AnalyticsAdminServiceClient(
        client_info=_CLIENT_INFO, credentials=creds
    )


def create_data_api_client(
    credentials=None,
) -> data_v1beta.BetaAnalyticsDataClient:
    """Returns the Google Analytics Data API client.

    Args:
        credentials: Optional explicit credentials. If omitted, credentials
            are resolved from the per-request refresh token context or the
            application-default credentials cache.
    """
    creds = credentials if credentials is not None else _get_credentials()
    return data_v1beta.BetaAnalyticsDataClient(
        client_info=_CLIENT_INFO, credentials=creds
    )


def create_admin_alpha_api_client(
    credentials=None,
) -> admin_v1alpha.AnalyticsAdminServiceClient:
    """Returns the Google Analytics Admin API (alpha) client.

    Args:
        credentials: Optional explicit credentials. If omitted, credentials
            are resolved from the per-request refresh token context or the
            application-default credentials cache.
    """
    creds = credentials if credentials is not None else _get_credentials()
    return admin_v1alpha.AnalyticsAdminServiceClient(
        client_info=_CLIENT_INFO, credentials=creds
    )


def create_data_api_alpha_client(
    credentials=None,
) -> data_v1alpha.AlphaAnalyticsDataClient:
    """Returns the Google Analytics Data API (Alpha) client.

    Args:
        credentials: Optional explicit credentials. If omitted, credentials
            are resolved from the per-request refresh token context or the
            application-default credentials cache.
    """
    creds = credentials if credentials is not None else _get_credentials()
    return data_v1alpha.AlphaAnalyticsDataClient(
        client_info=_CLIENT_INFO, credentials=creds
    )
