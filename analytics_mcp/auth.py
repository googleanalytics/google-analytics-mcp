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

"""Authentication module for Google Analytics API.

Supports two authentication methods:
1. OAuth2 with access/refresh tokens from config file
2. Application Default Credentials (fallback)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# Read-only scope for Analytics Admin API and Analytics Data API
_READ_ONLY_ANALYTICS_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"

# Global credentials cache
_cached_credentials: Optional[google.auth.credentials.Credentials] = None


def invalidate_cache():
    """Invalidate cached credentials to force refresh on next request."""
    global _cached_credentials
    logger.info("Invalidating cached credentials")
    _cached_credentials = None


def create_credentials(config_path: Optional[str] = None) -> google.auth.credentials.Credentials:
    """Create Google Analytics API credentials.

    Tries OAuth2 from config file first, then falls back to Application Default Credentials.

    Args:
        config_path: Optional path to OAuth config file

    Returns:
        Google auth credentials
    """
    global _cached_credentials

    # Return cached credentials if still valid
    if _cached_credentials and not _cached_credentials.expired:
        logger.debug("Using cached credentials (not expired)")
        return _cached_credentials
    elif _cached_credentials:
        logger.info("Cached credentials expired, recreating")

    # Try OAuth2 authentication from config file
    if config_path:
        credentials = _try_oauth_authentication(config_path)
        if credentials:
            _cached_credentials = credentials
            return credentials

    # Fallback to Application Default Credentials
    logger.info("Using Application Default Credentials")
    credentials, _ = google.auth.default(scopes=[_READ_ONLY_ANALYTICS_SCOPE])
    _cached_credentials = credentials
    return credentials


def _try_oauth_authentication(config_path: str) -> Optional[Credentials]:
    """Try to authenticate using OAuth2 credentials from config file.

    Args:
        config_path: Path to config file with OAuth credentials

    Returns:
        Credentials object if successful, None otherwise
    """
    logger.debug(f"Attempting OAuth authentication from: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        oauth_config = config.get('googleOAuthCredentials')
        tokens = config.get('googleAnalyticsTokens')

        # Check if we have OAuth configuration
        if not oauth_config or not tokens:
            logger.debug("No OAuth configuration found in config file")
            return None

        access_token = tokens.get('accessToken')
        refresh_token = tokens.get('refreshToken')
        client_id = oauth_config.get('clientId')
        client_secret = oauth_config.get('clientSecret')

        # Validate required fields
        if not all([access_token, refresh_token, client_id, client_secret]):
            logger.warning("OAuth config incomplete, missing required fields")
            return None

        # Convert expiresAt timestamp to datetime if available
        expires_at = tokens.get('expiresAt')
        expiry = datetime.fromtimestamp(expires_at, tz=timezone.utc).replace(tzinfo=None) if expires_at else None

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=[_READ_ONLY_ANALYTICS_SCOPE],
            expiry=expiry
        )

        # Refresh token if expired or no expiry info
        if not expires_at or credentials.expired:
            logger.info(f"Token expired or missing expiry, refreshing (expired={credentials.expired})")
            try:
                credentials.refresh(Request())
                logger.info("Token refreshed successfully")

                # Update the config file with new token
                if credentials.token and credentials.expiry:
                    new_expires_at = int(credentials.expiry.timestamp())
                    _update_config_file(config_path, credentials.token, new_expires_at)
                    logger.info(f"Config file updated with new token (expires: {new_expires_at})")
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}", exc_info=True)
                return None
        else:
            logger.debug(f"Using cached token (expires at {expires_at})")

        return credentials

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load OAuth config from file: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during OAuth authentication: {e}", exc_info=True)
        return None


def _update_config_file(config_path: str, new_access_token: str, expires_at: int):
    """Update the config file with new access token and expiry.

    Args:
        config_path: Path to config file
        new_access_token: New access token
        expires_at: Token expiration timestamp
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        config['googleAnalyticsTokens']['accessToken'] = new_access_token
        config['googleAnalyticsTokens']['expiresAt'] = expires_at

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to update config file: {e}")
