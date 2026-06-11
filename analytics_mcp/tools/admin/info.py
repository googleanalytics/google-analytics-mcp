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

"""Tools for gathering Google Analytics account and property information."""

import asyncio
from typing import Any, Dict, List

from analytics_mcp.tools.utils import (
    construct_account_rn,
    construct_property_rn,
    proto_to_dict,
)
from analytics_mcp.tools.client import (
    create_admin_api_client,
    create_admin_alpha_api_client,
)
from google.analytics import admin_v1beta, admin_v1alpha


async def get_account_summaries() -> List[Dict[str, Any]]:
    """Retrieves information about the user's Google Analytics accounts and properties."""

    def _sync_call():
        summary_pager = create_admin_api_client().list_account_summaries()
        return [proto_to_dict(summary_page) for summary_page in summary_pager]

    return await asyncio.to_thread(_sync_call)


async def list_google_ads_links(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns a list of links to Google Ads accounts for a property.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.ListGoogleAdsLinksRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        links_pager = create_admin_api_client().list_google_ads_links(
            request=request
        )
        return [proto_to_dict(link_page) for link_page in links_pager]

    return await asyncio.to_thread(_sync_call)


async def get_property_details(property_id: int | str) -> Dict[str, Any]:
    """Returns details about a property.
    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.GetPropertyRequest(
        name=construct_property_rn(property_id)
    )

    def _sync_call():
        client = create_admin_api_client()
        return client.get_property(request=request)

    response = await asyncio.to_thread(_sync_call)
    return proto_to_dict(response)


async def list_properties(
    account_id: int | str, show_deleted: bool = False
) -> List[Dict[str, Any]]:
    """Returns the properties under a Google Analytics account.

    Returns full property objects, including display name, industry
    category, time zone, currency code, service level, and create time.
    Use this for deeper property discovery than `get_account_summaries`,
    which only returns summary information.

    Args:
        account_id: The Google Analytics account ID. Accepted formats are:
          - A number
          - A string consisting of 'accounts/' followed by a number
        show_deleted: Whether to include soft-deleted (i.e. "trashed")
          properties in the results. Defaults to False.
    """
    request = admin_v1beta.ListPropertiesRequest(
        filter=f"parent:{construct_account_rn(account_id)}",
        show_deleted=show_deleted,
    )

    def _sync_call():
        properties_pager = create_admin_api_client().list_properties(
            request=request
        )
        return [proto_to_dict(prop) for prop in properties_pager]

    return await asyncio.to_thread(_sync_call)


async def list_key_events(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns the key events configured for a property.

    Key events (formerly known as conversion events) are the events that a
    property has marked as most important, such as purchases or sign-ups.
    Reports use key events to calculate conversion-related metrics.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.ListKeyEventsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        key_events_pager = create_admin_api_client().list_key_events(
            request=request
        )
        return [proto_to_dict(key_event) for key_event in key_events_pager]

    return await asyncio.to_thread(_sync_call)


async def list_data_streams(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns the data streams configured for a property.

    Data streams are the sources that send data to a property, such as a
    web site, an Android app, or an iOS app. Each stream includes its
    platform-specific details, e.g. the measurement ID for a web stream.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.ListDataStreamsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        data_streams_pager = create_admin_api_client().list_data_streams(
            request=request
        )
        return [
            proto_to_dict(data_stream) for data_stream in data_streams_pager
        ]

    return await asyncio.to_thread(_sync_call)


async def list_property_annotations(
    property_id: int | str,
) -> List[Dict[str, Any]]:
    """Returns annotations for a property.

    Annotations are a feature that allows you to leave notes on GA4 for specific dates or periods.
    They are typically used to record service releases, marketing campaign launches or changes,
    and rapid traffic increases or decreases due to external factors.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1alpha.ListReportingDataAnnotationsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        annotations_pager = (
            create_admin_alpha_api_client().list_reporting_data_annotations(
                request=request
            )
        )
        return [
            proto_to_dict(annotation_page)
            for annotation_page in annotations_pager
        ]

    return await asyncio.to_thread(_sync_call)
