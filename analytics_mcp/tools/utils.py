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
import time

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
        print(f"Attempting to update config file: {config_path}", file=sys.stderr)
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Store old token for debugging
        old_token = config['googleAnalyticsTokens']['accessToken'][:50] + "..."
        
        config['googleAnalyticsTokens']['accessToken'] = new_access_token
        config['googleAnalyticsTokens']['expiresAt'] = expires_at
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Successfully updated config file", file=sys.stderr)
        print(f"  Old token: {old_token}", file=sys.stderr)
        print(f"  New token: {new_access_token[:50]}...", file=sys.stderr)
        print(f"  Expires at: {expires_at}", file=sys.stderr)
        
    except Exception as e:
        print(f"❌ Failed to update config file: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)


def _create_credentials() -> google.auth.credentials.Credentials:
    """Returns OAuth2 credentials from config file with read-only scope and auto-refresh."""
    global _cached_credentials
    
    print(f"🔥 _create_credentials called", file=sys.stderr)
    
    # FORCE REFRESH - don't use cached credentials for debugging
    # if _cached_credentials and not _cached_credentials.expired:
    #     return _cached_credentials
    
    # Import here to avoid circular imports
    from ..coordinator import get_config_path
    
    try:
        config_path = get_config_path()
        print(f"🔥 Using config path from coordinator: {config_path}", file=sys.stderr)
    except RuntimeError as e:
        print(f"🔥 Coordinator not initialized: {e}", file=sys.stderr)
        # Fallback to environment variable if coordinator not initialized
        config_path = os.environ.get('GOOGLE_ANALYTICS_CONFIG_PATH')
        print(f"🔥 Using env config path: {config_path}", file=sys.stderr)
        if not config_path:
            raise RuntimeError("No config path provided. Set GOOGLE_ANALYTICS_CONFIG_PATH environment variable.")
    
    print(f"🔥 Loading config from: {config_path}", file=sys.stderr)
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print(f"🔥 Config loaded successfully", file=sys.stderr)
        
        oauth_config = config.get('googleOAuthCredentials', {})
        tokens = config.get('googleAnalyticsTokens', {})
        
        # Check if token is expired before creating credentials
        expires_at = tokens.get('expiresAt')
        current_time = int(time.time())
        
        print(f"🔥 Token expires at: {expires_at}, current time: {current_time}", file=sys.stderr)
        
        # If we have expiry info and token is not expired, use current token
        if expires_at and current_time < expires_at:
            print(f"🔥 Using existing valid access token", file=sys.stderr)
        else:
            print(f"🔥 Access token expired or no expiry info, will refresh", file=sys.stderr)
        
        access_token = tokens.get('accessToken')
        refresh_token = tokens.get('refreshToken')
        client_id = oauth_config.get('clientId')
        client_secret = oauth_config.get('clientSecret')
        
        print(f"🔥 Creating credentials with:", file=sys.stderr)
        print(f"  Access token: {access_token[:50] if access_token else 'NONE'}...", file=sys.stderr)
        print(f"  Refresh token: {refresh_token[:50] if refresh_token else 'NONE'}...", file=sys.stderr)
        print(f"  Client ID: {client_id}", file=sys.stderr)
        
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=[_READ_ONLY_ANALYTICS_SCOPE]
        )
        
        print(f"🔥 Credentials created. Expired: {credentials.expired}, Valid: {credentials.valid}", file=sys.stderr)
        
        # FORCE REFRESH - Always refresh if no expiry info or if expired
        if (not expires_at or credentials.expired) and credentials.refresh_token:
            print(f"🔥 Forcing token refresh (no expiry info or expired)...", file=sys.stderr)
            try:
                credentials.refresh(Request())
                print(f"🔥 Token refresh SUCCESS! New token: {credentials.token[:50]}...", file=sys.stderr)
                
                # Update the config file with new token
                if credentials.token and credentials.expiry:
                    expires_at = int(credentials.expiry.timestamp())
                    _update_config_file(config_path, credentials.token, expires_at)
                    
            except Exception as refresh_error:
                print(f"🔥 Token refresh FAILED: {refresh_error}", file=sys.stderr)
                raise
        else:
            print(f"🔥 Credentials are valid, no refresh needed", file=sys.stderr)
        
        # Cache the credentials for reuse
        _cached_credentials = credentials
        return credentials
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        # Fallback to Application Default Credentials if config file is not found or invalid
        print(f"Warning: Could not load OAuth credentials from config file: {e}", file=sys.stderr)
        print("Falling back to Application Default Credentials", file=sys.stderr)
        (credentials, _) = google.auth.default(scopes=[_READ_ONLY_ANALYTICS_SCOPE])
        return credentials


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
