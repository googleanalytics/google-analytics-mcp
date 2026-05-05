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

from google.analytics import (
    admin_v1beta,
    data_v1beta,
    admin_v1alpha,
    data_v1alpha,
)
from google.api_core.gapic_v1.client_info import ClientInfo
from importlib import metadata
import google.auth
import threading


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


def _get_credentials():
    global _CREDENTIALS
    # Expected to be called under _client_lock
    if _CREDENTIALS is None:
        _CREDENTIALS, _ = google.auth.default(scopes=[_READ_ONLY_ANALYTICS_SCOPE])
    return _CREDENTIALS


def create_admin_api_client() -> admin_v1beta.AnalyticsAdminServiceClient:
    """Returns the Google Analytics Admin API client."""
    with _client_lock:
        return admin_v1beta.AnalyticsAdminServiceClient(
            client_info=_CLIENT_INFO, credentials=_get_credentials()
        )


def create_data_api_client() -> data_v1beta.BetaAnalyticsDataClient:
    """Returns the Google Analytics Data API client."""
    with _client_lock:
        return data_v1beta.BetaAnalyticsDataClient(
            client_info=_CLIENT_INFO, credentials=_get_credentials()
        )


def create_admin_alpha_api_client() -> (
    admin_v1alpha.AnalyticsAdminServiceClient
):
    """Returns the Google Analytics Admin API (alpha) client."""
    with _client_lock:
        return admin_v1alpha.AnalyticsAdminServiceClient(
            client_info=_CLIENT_INFO, credentials=_get_credentials()
        )


def create_data_api_alpha_client() -> data_v1alpha.AlphaAnalyticsDataClient:
    """Returns the Google Analytics Data API (Alpha) client."""
    with _client_lock:
        return data_v1alpha.AlphaAnalyticsDataClient(
            client_info=_CLIENT_INFO, credentials=_get_credentials()
        )
