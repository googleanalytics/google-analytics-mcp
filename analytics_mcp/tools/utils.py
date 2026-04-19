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

"""Common utilities used by the MCP server."""

from typing import Any, Dict

from google.analytics import admin_v1beta, data_v1beta, admin_v1alpha
from google.api_core.gapic_v1.client_info import ClientInfo
from importlib import metadata
import google.auth
import proto


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


def _create_credentials() -> google.auth.credentials.Credentials:
    """Returns Application Default Credentials with read-only scope."""
    import sys
    import os
    import google.oauth2.credentials
    print("_create_credentials started", file=sys.stderr)
    try:
        path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if path and os.path.exists(path):
            print(f"Loading credentials directly from {path}", file=sys.stderr)
            credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(path, scopes=[_READ_ONLY_ANALYTICS_SCOPE])
            print("Credentials loaded successfully from file", file=sys.stderr)
            return credentials
        else:
            print("GOOGLE_APPLICATION_CREDENTIALS not found, falling back to default", file=sys.stderr)
            credentials, _ = google.auth.default(scopes=[_READ_ONLY_ANALYTICS_SCOPE])
            print("google.auth.default finished", file=sys.stderr)
            return credentials
    except Exception as e:
        print(f"google.auth.default failed: {e}", file=sys.stderr)
        raise


def create_admin_api_client_sync() -> admin_v1beta.AnalyticsAdminServiceClient:
    return admin_v1beta.AnalyticsAdminServiceClient(
        client_info=_CLIENT_INFO, credentials=_create_credentials()
    )


def create_data_api_client_sync() -> data_v1beta.BetaAnalyticsDataClient:
    return data_v1beta.BetaAnalyticsDataClient(
        client_info=_CLIENT_INFO, credentials=_create_credentials()
    )


def create_admin_alpha_api_client_sync() -> admin_v1alpha.AnalyticsAdminServiceClient:
    return admin_v1alpha.AnalyticsAdminServiceClient(
        client_info=_CLIENT_INFO, credentials=_create_credentials()
    )


def construct_property_rn(property_value: int | str) -> str:
    """Returns a property resource name in the format required by APIs."""
    property_num = None
    if isinstance(property_value, int):
        property_num = property_value
    elif isinstance(property_value, str):
        property_value = property_value.strip()
        if property_value.isdigit():
            property_num = int(property_value)
        elif property_value.startswith("properties/"):
            numeric_part = property_value.split("/")[-1]
            if numeric_part.isdigit():
                property_num = int(numeric_part)
    if property_num is None:
        raise ValueError(
            (
                f"Invalid property ID: {property_value}. "
                "A valid property value is either a number or a string starting "
                "with 'properties/' and followed by a number."
            )
        )

    return f"properties/{property_num}"


def proto_to_dict(obj: proto.Message) -> Dict[str, Any]:
    """Converts a proto message to a dictionary."""
    return type(obj).to_dict(
        obj, use_integers_for_enums=False, preserving_proto_field_name=True
    )


def proto_to_json(obj: proto.Message) -> str:
    """Converts a proto message to a JSON string."""
    return type(obj).to_json(obj, indent=None, preserving_proto_field_name=True)
