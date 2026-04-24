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

"""Tool for checking dimension and metric compatibility."""

from typing import Any, Dict, List

from analytics_mcp.tools.utils import (
    construct_property_rn,
    create_data_api_client,
    proto_to_dict,
)
from google.analytics import data_v1beta


async def check_compatibility(
    property_id: int | str,
    dimensions: List[str] = None,
    metrics: List[str] = None,
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Checks compatibility of dimensions and metrics for a report.

    This method checks which dimensions and metrics can be added to a
    report request given the dimensions and metrics already present in
    the request. The compatibility check is useful for discovering
    which dimensions and metrics can be used together in a report
    before running the report.

    Note that the reference docs at
    https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/checkCompatibility
    all use camelCase field names, but field names passed to this
    method should be in snake_case since the tool is using the protocol
    buffers (protobuf) format.

    Args:
        property_id: The Google Analytics property ID. Accepted
          formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
        dimensions: A list of dimension names to check compatibility
          for. If omitted, checks compatibility for all dimensions.
        metrics: A list of metric names to check compatibility for. If
          omitted, checks compatibility for all metrics.
        dimension_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/FilterExpression)
          to apply to the dimensions.
        metric_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/FilterExpression)
          to apply to the metrics.
    """
    request = data_v1beta.CheckCompatibilityRequest(
        property=construct_property_rn(property_id),
    )

    if dimensions:
        request.dimensions = [
            data_v1beta.Dimension(name=dimension)
            for dimension in dimensions
        ]

    if metrics:
        request.metrics = [
            data_v1beta.Metric(name=metric) for metric in metrics
        ]

    if dimension_filter:
        request.dimension_filter = data_v1beta.FilterExpression(
            dimension_filter
        )

    if metric_filter:
        request.metric_filter = data_v1beta.FilterExpression(metric_filter)

    response = await create_data_api_client().check_compatibility(request)

    return proto_to_dict(response)
