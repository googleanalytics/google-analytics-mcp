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
import json
import os
import sys

from google.analytics import admin_v1beta, data_v1beta
from google.api_core.gapic_v1.client_info import ClientInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
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

# Global credentials cache to avoid recreating credentials
_cached_credentials = None


def _update_config_file(config_path: str, new_access_token: str, expires_at: int):
    """Update the config file with new access token and expiry."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        config['googleAnalyticsTokens']['accessToken'] = new_access_token
        config['googleAnalyticsTokens']['expiresAt'] = expires_at
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        # Log error but don't fail - let the caller handle it
        print(f"Warning: Failed to update config file: {e}", file=sys.stderr)


def _create_credentials() -> google.auth.credentials.Credentials:
    """Returns Google Analytics API credentials.
    
    Supports two authentication methods:
    1. OAuth2 with access/refresh tokens from config file (preferred)
    2. Application Default Credentials (fallback)
    
    The config file format for OAuth2:
    {
      "googleOAuthCredentials": {
        "clientId": "YOUR_CLIENT_ID",
        "clientSecret": "YOUR_CLIENT_SECRET"
      },
      "googleAnalyticsTokens": {
        "accessToken": "YOUR_ACCESS_TOKEN",
        "refreshToken": "YOUR_REFRESH_TOKEN",
        "expiresAt": UNIX_TIMESTAMP
      }
    }
    """
    global _cached_credentials
    
    # Return cached credentials if still valid
    if _cached_credentials and not _cached_credentials.expired:
        return _cached_credentials
    
    # Try to get config path from coordinator or environment
    config_path = _get_config_path()
    
    if config_path:
        # Attempt OAuth2 authentication from config file
        credentials = _try_oauth_authentication(config_path)
        if credentials:
            _cached_credentials = credentials
            return credentials
    
    # Fallback to Application Default Credentials
    print("Using Application Default Credentials", file=sys.stderr)
    (credentials, _) = google.auth.default(scopes=[_READ_ONLY_ANALYTICS_SCOPE])
    _cached_credentials = credentials
    return credentials


def _get_config_path() -> str:
    """Get the config file path from coordinator or environment."""
    # Import here to avoid circular imports
    from ..coordinator import get_config_path
    
    try:
        return get_config_path()
    except RuntimeError:
        # Fallback to environment variable if coordinator not initialized
        return os.environ.get('GOOGLE_ANALYTICS_CONFIG_PATH')


def _try_oauth_authentication(config_path: str) -> google.auth.credentials.Credentials:
    """Try to authenticate using OAuth2 credentials from config file.
    
    Returns:
        Credentials object if successful, None otherwise.
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        oauth_config = config.get('googleOAuthCredentials')
        tokens = config.get('googleAnalyticsTokens')
        
        # Check if we have OAuth configuration
        if not oauth_config or not tokens:
            return None
        
        access_token = tokens.get('accessToken')
        refresh_token = tokens.get('refreshToken')
        client_id = oauth_config.get('clientId')
        client_secret = oauth_config.get('clientSecret')
        
        # Validate required fields
        if not all([access_token, refresh_token, client_id, client_secret]):
            print("OAuth config incomplete, missing required fields", file=sys.stderr)
            return None
        
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=[_READ_ONLY_ANALYTICS_SCOPE]
        )
        
        # Refresh token if expired or no expiry info
        expires_at = tokens.get('expiresAt')
        if not expires_at or credentials.expired:
            try:
                credentials.refresh(Request())
                # Update the config file with new token
                if credentials.token and credentials.expiry:
                    new_expires_at = int(credentials.expiry.timestamp())
                    _update_config_file(config_path, credentials.token, new_expires_at)
            except Exception as e:
                print(f"Failed to refresh token: {e}", file=sys.stderr)
                return None
        
        return credentials
        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Could not load OAuth config from file: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error during OAuth authentication: {e}", file=sys.stderr)
        return None


def create_admin_api_client() -> admin_v1beta.AnalyticsAdminServiceAsyncClient:
    """Returns a properly configured Google Analytics Admin API async client.

    Uses Application Default Credentials with read-only scope.
    """
    return admin_v1beta.AnalyticsAdminServiceAsyncClient(
        client_info=_CLIENT_INFO, credentials=_create_credentials()
    )


def create_data_api_client() -> data_v1beta.BetaAnalyticsDataAsyncClient:
    """Returns a properly configured Google Analytics Data API async client.

    Uses Application Default Credentials with read-only scope.
    """
    return data_v1beta.BetaAnalyticsDataAsyncClient(
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
