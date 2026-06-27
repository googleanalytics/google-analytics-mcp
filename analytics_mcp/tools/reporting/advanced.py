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

"""Additional read-only reporting and metadata tools for GA4 MCP."""

import asyncio
from typing import Any, Dict, List

from analytics_mcp.tools.client import (
    create_data_api_alpha_client,
    create_data_api_client,
)
from analytics_mcp.tools.utils import (
    construct_property_quotas_snapshot_rn,
    construct_property_rn,
    proto_to_dict,
)
from google.analytics import data_v1alpha, data_v1beta


async def get_property_metadata(property_id: int | str) -> Dict[str, Any]:
    """Returns full property metadata, including all dimensions and metrics."""

    def _sync_call():
        return create_data_api_client().get_metadata(
            request=data_v1beta.GetMetadataRequest(
                name=f"{construct_property_rn(property_id)}/metadata"
            )
        )

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def run_pivot_report(
    property_id: int | str,
    date_ranges: List[Dict[str, Any]],
    dimensions: List[str],
    metrics: List[str],
    pivots: List[Dict[str, Any]],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    currency_code: str = None,
    keep_empty_rows: bool = False,
    return_property_quota: bool = False,
) -> Dict[str, Any]:
    """Runs a Google Analytics Data API pivot report."""
    request = data_v1beta.RunPivotReportRequest(
        property=construct_property_rn(property_id),
        dimensions=[data_v1beta.Dimension(name=dimension) for dimension in dimensions],
        metrics=[data_v1beta.Metric(name=metric) for metric in metrics],
        date_ranges=[data_v1beta.DateRange(dr) for dr in date_ranges],
        pivots=[data_v1beta.Pivot(pivot) for pivot in pivots],
        keep_empty_rows=keep_empty_rows,
        return_property_quota=return_property_quota,
    )
    if dimension_filter:
        request.dimension_filter = data_v1beta.FilterExpression(
            dimension_filter
        )
    if metric_filter:
        request.metric_filter = data_v1beta.FilterExpression(metric_filter)
    if currency_code:
        request.currency_code = currency_code

    def _sync_call():
        return create_data_api_client().run_pivot_report(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def check_report_compatibility(
    property_id: int | str,
    dimensions: List[str],
    metrics: List[str],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    compatibility_filter: str = None,
) -> Dict[str, Any]:
    """Checks whether dimensions and metrics are compatible in one report."""
    request = data_v1beta.CheckCompatibilityRequest(
        property=construct_property_rn(property_id),
        dimensions=[data_v1beta.Dimension(name=dimension) for dimension in dimensions],
        metrics=[data_v1beta.Metric(name=metric) for metric in metrics],
    )
    if dimension_filter:
        request.dimension_filter = data_v1beta.FilterExpression(
            dimension_filter
        )
    if metric_filter:
        request.metric_filter = data_v1beta.FilterExpression(metric_filter)
    if compatibility_filter:
        request.compatibility_filter = compatibility_filter

    def _sync_call():
        return create_data_api_client().check_compatibility(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def get_property_quotas_snapshot(
    property_id: int | str,
) -> Dict[str, Any]:
    """Returns the property's quota snapshot from the Alpha Data API."""
    request = data_v1alpha.GetPropertyQuotasSnapshotRequest(
        name=construct_property_quotas_snapshot_rn(property_id)
    )

    def _sync_call():
        return create_data_api_alpha_client().get_property_quotas_snapshot(
            request=request
        )

    return proto_to_dict(await asyncio.to_thread(_sync_call))
