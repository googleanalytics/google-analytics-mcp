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

from typing import Any, Dict, Callable, TypeVar, Awaitable
import logging
import sys

from google.analytics import admin_v1beta, data_v1beta
from google.api_core.gapic_v1.client_info import ClientInfo
from google.api_core.exceptions import Unauthenticated, Forbidden
from importlib import metadata
import proto

from ..auth import create_credentials, invalidate_cache as invalidate_auth_cache

T = TypeVar('T')

# Configure logger
logger = logging.getLogger(__name__)


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

# Global client cache
_cached_admin_client = None
_cached_data_client = None


def invalidate_cached_credentials():
    """Invalidate cached credentials and clients to force refresh on next request."""
    global _cached_admin_client, _cached_data_client
    logger.info("Invalidating cached API clients and credentials")
    invalidate_auth_cache()
    _cached_admin_client = None
    _cached_data_client = None


async def retry_on_auth_error(func: Callable[[], Awaitable[T]], max_retries: int = 1) -> T:
    """Retry a function call if it fails with authentication errors.

    This handles cases where the cached credentials are expired by invalidating
    the cache and retrying once with fresh credentials.

    Args:
        func: Async function to call
        max_retries: Maximum number of retries (default: 1)

    Returns:
        The result of the function call

    Raises:
        The original exception if all retries are exhausted
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except (Unauthenticated, Forbidden) as e:
            last_exception = e
            error_msg = str(e).lower()
            logger.warning(f"Auth error caught: {error_msg[:200]}")

            # Check if it's an authentication/authorization error
            if any(keyword in error_msg for keyword in [
                '401', 'unauthorized', 'unauthenticated',
                'invalid authentication', 'authentication credential',
                'access token', 'expired', 'refresh'
            ]):
                if attempt < max_retries:
                    logger.info(f"Authentication error detected, refreshing credentials and retrying (attempt {attempt + 1}/{max_retries + 1})")
                    invalidate_cached_credentials()
                    continue
                else:
                    logger.error(f"Authentication failed after {max_retries + 1} attempts: {e}")
                    print("💡 Try running: python refresh_and_update_config.py <config_path>", file=sys.stderr)

            # Re-raise if it's not an auth error or we've exhausted retries
            raise
        except Exception as e:
            # For non-auth errors, don't retry
            logger.debug(f"Non-auth error (not retrying): {type(e).__name__}: {str(e)[:100]}")
            raise

    # This shouldn't be reached, but just in case
    if last_exception:
        raise last_exception


def _get_config_path() -> str:
    """Get the config file path from coordinator."""
    # Import here to avoid circular imports
    from ..coordinator import get_config_path

    try:
        return get_config_path()
    except RuntimeError:
        return None


def create_admin_api_client() -> admin_v1beta.AnalyticsAdminServiceAsyncClient:
    """Returns a properly configured Google Analytics Admin API async client.

    Automatically handles credential refresh and caching.
    """
    global _cached_admin_client

    # Get config path from coordinator
    config_path = _get_config_path()

    # If cache was invalidated, recreate client with fresh credentials
    if _cached_admin_client is None:
        logger.debug("Creating new Admin API client (cache was cleared)")
        creds = create_credentials(config_path)
        _cached_admin_client = admin_v1beta.AnalyticsAdminServiceAsyncClient(
            client_info=_CLIENT_INFO, credentials=creds
        )
        return _cached_admin_client

    # Check if cached client's credentials are still valid
    creds = create_credentials(config_path)
    if creds.expired:
        logger.debug("Recreating Admin API client (credentials expired)")
        _cached_admin_client = admin_v1beta.AnalyticsAdminServiceAsyncClient(
            client_info=_CLIENT_INFO, credentials=creds
        )
    else:
        logger.debug("Reusing cached Admin API client")

    return _cached_admin_client


def create_data_api_client() -> data_v1beta.BetaAnalyticsDataAsyncClient:
    """Returns a properly configured Google Analytics Data API async client.

    Automatically handles credential refresh and caching.
    """
    global _cached_data_client

    # Get config path from coordinator
    config_path = _get_config_path()

    # If cache was invalidated, recreate client with fresh credentials
    if _cached_data_client is None:
        logger.debug("Creating new Data API client (cache was cleared)")
        creds = create_credentials(config_path)
        _cached_data_client = data_v1beta.BetaAnalyticsDataAsyncClient(
            client_info=_CLIENT_INFO, credentials=creds
        )
        return _cached_data_client

    # Check if cached client's credentials are still valid
    creds = create_credentials(config_path)
    if creds.expired:
        logger.debug("Recreating Data API client (credentials expired)")
        _cached_data_client = data_v1beta.BetaAnalyticsDataAsyncClient(
            client_info=_CLIENT_INFO, credentials=creds
        )
    else:
        logger.debug("Reusing cached Data API client")

    return _cached_data_client


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
