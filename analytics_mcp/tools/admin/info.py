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

from typing import Any, Dict, List, Optional

from analytics_mcp.tools.utils import (
    construct_property_rn,
    create_admin_api_client,
    create_admin_alpha_api_client,
    proto_to_dict,
)
from google.analytics import admin_v1beta, admin_v1alpha

# Fields stripped from account summaries to reduce token count.
_ACCOUNT_STRIP_FIELDS = {"name"}
_PROPERTY_STRIP_FIELDS = {"name", "parent", "property_type"}


def _strip_account_summary(account: Dict[str, Any]) -> Dict[str, Any]:
    """Remove redundant fields from an account summary and its properties."""
    cleaned = {k: v for k, v in account.items() if k not in _ACCOUNT_STRIP_FIELDS}
    if "property_summaries" in cleaned:
        cleaned["property_summaries"] = [
            {k: v for k, v in prop.items() if k not in _PROPERTY_STRIP_FIELDS}
            for prop in cleaned["property_summaries"]
        ]
    return cleaned


async def get_account_summaries(
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieves the user's Google Analytics accounts and properties.

    Returns a compact representation with redundant fields (name, parent,
    property_type) stripped to reduce token usage. Each account keeps its
    ``account`` resource-name and ``display_name``; each property keeps its
    ``property`` resource-name and ``display_name``.

    Args:
        query: Optional case-insensitive search string. When provided, only
            accounts or properties whose display name contains the query are
            returned. An account is included if its own display name matches
            **or** any of its properties match; non-matching properties on an
            otherwise-matching account are still filtered out.
    """

    # Uses an async list comprehension so the pager returned by
    # list_account_summaries retrieves all pages.
    summary_pager = await create_admin_api_client().list_account_summaries()
    all_pages = [
        proto_to_dict(summary_page) async for summary_page in summary_pager
    ]

    # Strip redundant fields.
    all_pages = [_strip_account_summary(s) for s in all_pages]

    # Apply optional display-name filter.
    if query:
        q = query.lower()
        filtered = []
        for account in all_pages:
            acct_match = q in account.get("display_name", "").lower()
            matching_props = [
                p
                for p in account.get("property_summaries", [])
                if q in p.get("display_name", "").lower()
            ]
            if acct_match or matching_props:
                account = dict(account)
                if not acct_match:
                    # Only include properties that matched.
                    account["property_summaries"] = matching_props
                filtered.append(account)
        all_pages = filtered

    return all_pages


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
    # Uses an async list comprehension so the pager returned by
    # list_google_ads_links retrieves all pages.
    links_pager = await create_admin_api_client().list_google_ads_links(
        request=request
    )
    all_pages = [proto_to_dict(link_page) async for link_page in links_pager]
    return all_pages


async def get_property_details(property_id: int | str) -> Dict[str, Any]:
    """Returns details about a property.
    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    client = create_admin_api_client()
    request = admin_v1beta.GetPropertyRequest(
        name=construct_property_rn(property_id)
    )
    response = await client.get_property(request=request)
    return proto_to_dict(response)


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
    annotations_pager = (
        await create_admin_alpha_api_client().list_reporting_data_annotations(
            request=request
        )
    )
    all_pages = [
        proto_to_dict(annotation_page)
        async for annotation_page in annotations_pager
    ]
    return all_pages
