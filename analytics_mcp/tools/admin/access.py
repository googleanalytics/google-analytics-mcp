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

"""Tools for running data access reports using the Admin API."""

import asyncio
from typing import Any, Dict, List

from analytics_mcp.tools.utils import (
    construct_account_rn,
    construct_property_rn,
    proto_to_dict,
)
from analytics_mcp.tools.client import create_admin_api_client
from google.analytics import admin_v1beta


def _construct_access_report_entity(entity: int | str) -> str:
    """Returns the entity resource name for an access report request.

    Accepts a property (number or 'properties/N') or an account
    ('accounts/N').
    """
    if isinstance(entity, str) and entity.strip().startswith("accounts/"):
        return construct_account_rn(entity)
    return construct_property_rn(entity)


async def run_access_report(
    entity: int | str,
    date_ranges: List[Dict[str, str]],
    dimensions: List[str],
    metrics: List[str],
    limit: int = None,
    offset: int = None,
    return_entity_quota: bool = False,
) -> Dict[str, Any]:
    """Runs a data access report showing who accessed Analytics data.

    Each row describes data access events, e.g. which user accessed
    which property, when, from where, and how many data requests were
    made. Useful for compliance and security auditing.

    Access reports use their own dimension and metric names, documented
    at
    https://developers.google.com/analytics/devguides/config/admin/v1/access-api-schema.
    Common dimensions include `userEmail`, `epochTimeMicros`,
    `accessMechanism`, and `reportType`. Common metrics include
    `accessCount`.

    Args:
        entity: The entity to report on. Accepted formats are:
          - A number (treated as a property ID)
          - A string consisting of 'properties/' followed by a number
          - A string consisting of 'accounts/' followed by a number,
            which reports on all properties under the account
        date_ranges: A list of date range dicts, each with `start_date`
          and `end_date` keys. Dates are in `YYYY-MM-DD` format, or the
          relative forms `today`, `yesterday`, and `NdaysAgo`.
        dimensions: A list of access report dimension names.
        metrics: A list of access report metric names.
        limit: The maximum number of rows to return (max 100,000).
        offset: The row count of the start row (0-indexed).
        return_entity_quota: Whether to include the current state of
          this property's access report quota in the response.
    """
    request = admin_v1beta.RunAccessReportRequest(
        entity=_construct_access_report_entity(entity),
        date_ranges=[admin_v1beta.AccessDateRange(dr) for dr in date_ranges],
        dimensions=[
            admin_v1beta.AccessDimension(dimension_name=d) for d in dimensions
        ],
        metrics=[admin_v1beta.AccessMetric(metric_name=m) for m in metrics],
        return_entity_quota=return_entity_quota,
    )

    if limit:
        request.limit = limit

    if offset:
        request.offset = offset

    def _sync_call():
        return create_admin_api_client().run_access_report(request=request)

    response = await asyncio.to_thread(_sync_call)

    return proto_to_dict(response)
