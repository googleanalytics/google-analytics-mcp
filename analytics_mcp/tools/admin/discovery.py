# Copyright 2026 Google LLC All Rights Reserved.
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

"""Additional read-only admin tools for GA4 MCP."""

import asyncio
from typing import Any, Dict, List

from analytics_mcp.tools.client import create_admin_api_client
from analytics_mcp.tools.utils import (
    construct_account_rn,
    construct_conversion_event_rn,
    construct_custom_dimension_rn,
    construct_custom_metric_rn,
    construct_data_retention_settings_rn,
    construct_data_sharing_settings_rn,
    construct_data_stream_rn,
    construct_key_event_rn,
    construct_property_rn,
    proto_to_dict,
)
from google.analytics import admin_v1beta


async def list_accounts() -> List[Dict[str, Any]]:
    """Returns accessible Google Analytics accounts."""

    def _sync_call():
        pager = create_admin_api_client().list_accounts(
            request=admin_v1beta.ListAccountsRequest()
        )
        return [proto_to_dict(account) for account in pager]

    return await asyncio.to_thread(_sync_call)


async def get_account(account_id: int | str) -> Dict[str, Any]:
    """Returns details for one Google Analytics account."""
    request = admin_v1beta.GetAccountRequest(
        name=construct_account_rn(account_id)
    )

    def _sync_call():
        return create_admin_api_client().get_account(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def list_properties(
    account_id: int | str | None = None,
    show_deleted: bool = False,
) -> List[Dict[str, Any]]:
    """Returns accessible properties, optionally filtered to one account."""
    request = admin_v1beta.ListPropertiesRequest(show_deleted=show_deleted)
    if account_id is not None:
        request.filter = f"parent:{construct_account_rn(account_id)}"

    def _sync_call():
        pager = create_admin_api_client().list_properties(request=request)
        return [proto_to_dict(prop) for prop in pager]

    return await asyncio.to_thread(_sync_call)


async def list_data_streams(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns data streams for a property."""
    request = admin_v1beta.ListDataStreamsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_admin_api_client().list_data_streams(request=request)
        return [proto_to_dict(stream) for stream in pager]

    return await asyncio.to_thread(_sync_call)


async def get_data_stream(
    property_id: int | str,
    data_stream_id: int | str,
) -> Dict[str, Any]:
    """Returns one data stream for a property."""
    request = admin_v1beta.GetDataStreamRequest(
        name=construct_data_stream_rn(property_id, data_stream_id)
    )

    def _sync_call():
        return create_admin_api_client().get_data_stream(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def get_data_retention_settings(property_id: int | str) -> Dict[str, Any]:
    """Returns data retention settings for a property."""
    request = admin_v1beta.GetDataRetentionSettingsRequest(
        name=construct_data_retention_settings_rn(property_id)
    )

    def _sync_call():
        return create_admin_api_client().get_data_retention_settings(
            request=request
        )

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def get_data_sharing_settings(account_id: int | str) -> Dict[str, Any]:
    """Returns data sharing settings for an account."""
    request = admin_v1beta.GetDataSharingSettingsRequest(
        name=construct_data_sharing_settings_rn(account_id)
    )

    def _sync_call():
        return create_admin_api_client().get_data_sharing_settings(
            request=request
        )

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def list_firebase_links(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns Firebase links for a property."""
    request = admin_v1beta.ListFirebaseLinksRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_admin_api_client().list_firebase_links(request=request)
        return [proto_to_dict(link) for link in pager]

    return await asyncio.to_thread(_sync_call)


async def list_key_events(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns key events for a property."""
    request = admin_v1beta.ListKeyEventsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_admin_api_client().list_key_events(request=request)
        return [proto_to_dict(event) for event in pager]

    return await asyncio.to_thread(_sync_call)


async def get_key_event(
    property_id: int | str,
    key_event_id: int | str,
) -> Dict[str, Any]:
    """Returns one key event for a property."""
    request = admin_v1beta.GetKeyEventRequest(
        name=construct_key_event_rn(property_id, key_event_id)
    )

    def _sync_call():
        return create_admin_api_client().get_key_event(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def list_conversion_events(
    property_id: int | str,
) -> List[Dict[str, Any]]:
    """Returns conversion events for a property."""
    request = admin_v1beta.ListConversionEventsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_admin_api_client().list_conversion_events(request=request)
        return [proto_to_dict(event) for event in pager]

    return await asyncio.to_thread(_sync_call)


async def get_conversion_event(
    property_id: int | str,
    conversion_event_id: int | str,
) -> Dict[str, Any]:
    """Returns one conversion event for a property."""
    request = admin_v1beta.GetConversionEventRequest(
        name=construct_conversion_event_rn(property_id, conversion_event_id)
    )

    def _sync_call():
        return create_admin_api_client().get_conversion_event(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def list_custom_dimensions(
    property_id: int | str,
) -> List[Dict[str, Any]]:
    """Returns custom dimensions for a property."""
    request = admin_v1beta.ListCustomDimensionsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_admin_api_client().list_custom_dimensions(request=request)
        return [proto_to_dict(dimension) for dimension in pager]

    return await asyncio.to_thread(_sync_call)


async def get_custom_dimension(
    property_id: int | str,
    custom_dimension_id: int | str,
) -> Dict[str, Any]:
    """Returns one custom dimension for a property."""
    request = admin_v1beta.GetCustomDimensionRequest(
        name=construct_custom_dimension_rn(property_id, custom_dimension_id)
    )

    def _sync_call():
        return create_admin_api_client().get_custom_dimension(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def list_custom_metrics(
    property_id: int | str,
) -> List[Dict[str, Any]]:
    """Returns custom metrics for a property."""
    request = admin_v1beta.ListCustomMetricsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_admin_api_client().list_custom_metrics(request=request)
        return [proto_to_dict(metric) for metric in pager]

    return await asyncio.to_thread(_sync_call)


async def get_custom_metric(
    property_id: int | str,
    custom_metric_id: int | str,
) -> Dict[str, Any]:
    """Returns one custom metric for a property."""
    request = admin_v1beta.GetCustomMetricRequest(
        name=construct_custom_metric_rn(property_id, custom_metric_id)
    )

    def _sync_call():
        return create_admin_api_client().get_custom_metric(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def run_access_report(
    property_id: int | str,
    dimensions: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
    date_ranges: List[Dict[str, Any]],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    limit: int = None,
    offset: int = None,
    time_zone: str = None,
) -> Dict[str, Any]:
    """Runs an Analytics Admin access report for a property.

    This report often requires administrator-level access on the property.
    """
    request = admin_v1beta.RunAccessReportRequest(
        entity=construct_property_rn(property_id),
        dimensions=[
            admin_v1beta.AccessDimension(dimension) for dimension in dimensions
        ],
        metrics=[admin_v1beta.AccessMetric(metric) for metric in metrics],
        date_ranges=[
            admin_v1beta.AccessDateRange(date_range)
            for date_range in date_ranges
        ],
    )
    if dimension_filter:
        request.dimension_filter = admin_v1beta.AccessFilterExpression(
            dimension_filter
        )
    if metric_filter:
        request.metric_filter = admin_v1beta.AccessFilterExpression(metric_filter)
    if limit:
        request.limit = limit
    if offset:
        request.offset = offset
    if time_zone:
        request.time_zone = time_zone

    def _sync_call():
        return create_admin_api_client().run_access_report(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))
