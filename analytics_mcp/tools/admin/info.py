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
import datetime
from typing import Any, Dict, List, Tuple

from analytics_mcp.tools.utils import (
    construct_property_rn,
    proto_to_dict,
)
from analytics_mcp.tools.client import (
    create_admin_api_client,
    create_admin_alpha_api_client,
)
from google.analytics import admin_v1beta, admin_v1alpha
from google.type import date_pb2

# Note: ReportingDataAnnotation.Color.ORANGE (7) is reserved by Google Analytics
# exclusively for system-generated annotations and cannot be used when creating
# annotations via the API.
_AnnotationColor = admin_v1alpha.ReportingDataAnnotation.Color
_VALID_ANNOTATION_COLORS = tuple(
    c.name
    for c in _AnnotationColor
    if c not in (_AnnotationColor.COLOR_UNSPECIFIED, _AnnotationColor.ORANGE)
)
_MAX_ANNOTATION_TITLE_LENGTH = 60
_MAX_ANNOTATION_DESCRIPTION_LENGTH = 150


def _parse_annotation_date(
    date_str: str,
) -> Tuple[datetime.date, date_pb2.Date]:
    """Parses a YYYY-MM-DD string into a datetime.date and date_pb2.Date."""
    if not isinstance(date_str, str) or not date_str.strip():
        raise ValueError(
            f"Invalid date: {date_str!r}. Expected a string in YYYY-MM-DD format."
        )
    try:
        parsed = datetime.date.fromisoformat(date_str.strip())
    except ValueError as exc:
        raise ValueError(
            f"Invalid date '{date_str}'. Expected YYYY-MM-DD format."
        ) from exc
    return parsed, date_pb2.Date(
        year=parsed.year, month=parsed.month, day=parsed.day
    )


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


async def list_property_annotations(
    property_id: int | str,
) -> List[Dict[str, Any]]:
    """Returns annotations for a property.

    Annotations are a feature that allows you to leave notes on Google Analytics for specific dates or periods.
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


async def create_property_annotation(
    property_id: int | str,
    title: str,
    start_date: str,
    color: str = "BLUE",
    description: str = None,
    end_date: str = None,
) -> Dict[str, Any]:
    """Creates a reporting data annotation for a property.

    Annotations allow you to leave notes on Google Analytics for specific dates
    or date ranges to record service releases, GTM container publishes,
    marketing campaign launches, or traffic anomalies.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
        title: Human-readable title for the annotation (maximum 60 characters).
        start_date: The date (or start date of a range) in YYYY-MM-DD format
          (inclusive, e.g. '2026-10-21').
        color: Color used for displaying the annotation. Valid values are:
          'PURPLE', 'BROWN', 'BLUE', 'GREEN', 'RED', 'CYAN' ('ORANGE' is
          reserved by Google Analytics for system-generated annotations).
          Defaults to 'BLUE'.
        description: Optional description or notes for the annotation (maximum
          150 characters).
        end_date: Optional end date in YYYY-MM-DD format (inclusive) when
          creating a date-range annotation. Must be greater than or equal to
          start_date. If omitted, a single-date annotation is created on
          start_date.
    """
    if not title or not title.strip():
        raise ValueError("title must be a non-empty string.")
    stripped_title = title.strip()
    if len(stripped_title) > _MAX_ANNOTATION_TITLE_LENGTH:
        raise ValueError(
            f"title must be at most {_MAX_ANNOTATION_TITLE_LENGTH} characters "
            f"(got {len(stripped_title)})."
        )

    if (
        description is not None
        and len(description) > _MAX_ANNOTATION_DESCRIPTION_LENGTH
    ):
        raise ValueError(
            f"description must be at most {_MAX_ANNOTATION_DESCRIPTION_LENGTH} "
            f"characters (got {len(description)})."
        )

    normalized_color = (color or "").strip().upper()
    if normalized_color not in _VALID_ANNOTATION_COLORS:
        valid_str = ", ".join(_VALID_ANNOTATION_COLORS)
        raise ValueError(
            f"Invalid color '{color}'. Valid colors are: {valid_str}."
        )

    parsed_start, proto_start = _parse_annotation_date(start_date)

    annotation = admin_v1alpha.ReportingDataAnnotation(
        title=stripped_title,
        color=getattr(
            admin_v1alpha.ReportingDataAnnotation.Color, normalized_color
        ),
    )

    if description is not None:
        annotation.description = description

    if end_date is not None and end_date.strip():
        parsed_end, proto_end = _parse_annotation_date(end_date)
        if parsed_end < parsed_start:
            raise ValueError(
                f"end_date ({end_date}) must be greater than or equal to "
                f"start_date ({start_date})."
            )
        annotation.annotation_date_range = (
            admin_v1alpha.ReportingDataAnnotation.DateRange(
                start_date=proto_start,
                end_date=proto_end,
            )
        )
    else:
        annotation.annotation_date = proto_start

    request = admin_v1alpha.CreateReportingDataAnnotationRequest(
        parent=construct_property_rn(property_id),
        reporting_data_annotation=annotation,
    )

    def _sync_call():
        return create_admin_alpha_api_client().create_reporting_data_annotation(
            request=request
        )

    response = await asyncio.to_thread(_sync_call)
    return proto_to_dict(response)
