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
import subprocess
import threading
from importlib import metadata
from unittest.mock import patch

import google.auth
from google.analytics import (
    admin_v1beta,
    data_v1beta,
    admin_v1alpha,
    data_v1alpha,
)
from google.api_core.gapic_v1.client_info import ClientInfo


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

# Edit scope for Analytics Admin API write operations.
_EDIT_ANALYTICS_SCOPE = "https://www.googleapis.com/auth/analytics.edit"


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


class _ClientManager:
    """Thread-safe manager for Google Analytics API credentials and clients."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._credentials = None
        self._allow_write = False

    def set_allow_write(self, allow_write: bool) -> None:
        """Configures whether write scopes should be requested for credentials."""
        with self._lock:
            if self._allow_write != allow_write:
                self._allow_write = allow_write
                self._credentials = None

    def _get_credentials(self):
        """Returns cached credentials, initializing them if needed."""
        # Expected to be called under self._lock
        if self._credentials is None:
            scopes = [_READ_ONLY_ANALYTICS_SCOPE]
            if self._allow_write:
                scopes.append(_EDIT_ANALYTICS_SCOPE)
            with prevent_stdio_inheritance():
                self._credentials, _ = google.auth.default(scopes=scopes)
        return self._credentials

    def create_admin_api_client(
        self,
    ) -> admin_v1beta.AnalyticsAdminServiceClient:
        with self._lock:
            return admin_v1beta.AnalyticsAdminServiceClient(
                client_info=_CLIENT_INFO, credentials=self._get_credentials()
            )

    def create_data_api_client(self) -> data_v1beta.BetaAnalyticsDataClient:
        with self._lock:
            return data_v1beta.BetaAnalyticsDataClient(
                client_info=_CLIENT_INFO, credentials=self._get_credentials()
            )

    def create_admin_alpha_api_client(
        self,
    ) -> admin_v1alpha.AnalyticsAdminServiceClient:
        with self._lock:
            return admin_v1alpha.AnalyticsAdminServiceClient(
                client_info=_CLIENT_INFO, credentials=self._get_credentials()
            )

    def create_data_api_alpha_client(
        self,
    ) -> data_v1alpha.AlphaAnalyticsDataClient:
        with self._lock:
            return data_v1alpha.AlphaAnalyticsDataClient(
                client_info=_CLIENT_INFO, credentials=self._get_credentials()
            )


_client_manager = _ClientManager()


def set_allow_write(allow_write: bool) -> None:
    """Configures whether write scopes should be requested for credentials."""
    _client_manager.set_allow_write(allow_write)


def create_admin_api_client() -> admin_v1beta.AnalyticsAdminServiceClient:
    """Returns the Google Analytics Admin API client."""
    return _client_manager.create_admin_api_client()


def create_data_api_client() -> data_v1beta.BetaAnalyticsDataClient:
    """Returns the Google Analytics Data API client."""
    return _client_manager.create_data_api_client()


def create_admin_alpha_api_client() -> (
    admin_v1alpha.AnalyticsAdminServiceClient
):
    """Returns the Google Analytics Admin API (alpha) client."""
    return _client_manager.create_admin_alpha_api_client()


def create_data_api_alpha_client() -> data_v1alpha.AlphaAnalyticsDataClient:
    """Returns the Google Analytics Data API (Alpha) client."""
    return _client_manager.create_data_api_alpha_client()
