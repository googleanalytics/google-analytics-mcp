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

"""Tools for running realtime reports using the Data API."""

from typing import Any, Dict, List

from google.analytics import data_v1beta

from analytics_mcp.coordinator import mcp
from analytics_mcp.tools.reporting.metadata import (
    get_date_ranges_hints,
    get_dimension_filter_hints,
    get_metric_filter_hints,
    get_order_bys_hints,
)
from analytics_mcp.tools.utils import (
    construct_property_rn,
    create_data_api_client,
    proto_to_dict,
)


def _run_realtime_report_description() -> str:
    """Returns the description for the `run_realtime_report` tool."""
    return f"""
          {run_realtime_report.__doc__}

          ## Hints for arguments

          Here are some hints that outline the expected format and requirements
          for arguments.

          ### Hints for `dimensions`

          The `dimensions` list must consist solely of either of the following:

          1.  Realtime standard dimensions defined in the HTML table at
              https://developers.google.com/analytics/devguides/
              reporting/data/v1/realtime-api-schema#dimensions.
              These dimensions are available to *every* property.
          2.  User-scoped custom dimensions for the `property_id`. Use
              the `get_custom_dimensions_and_metrics` tool to retrieve
              the list of custom dimensions for a property, and look for
              the custom dimensions with an `apiName` that begins with
              "customUser:".

          ### Hints for `metrics`

          The `metrics` list must consist solely of the Realtime
          standard metrics defined in the HTML table at
          https://developers.google.com/analytics/devguides/
          reporting/data/v1/realtime-api-schema#metrics.
          These metrics are available to *every* property.

          Realtime reports can't use custom metrics.

          ### Hints for `date_ranges`:
          {get_date_ranges_hints()}

          ### Hints for `dimension_filter`:
          {get_dimension_filter_hints()}

          ### Hints for `metric_filter`:
          {get_metric_filter_hints()}

          ### Hints for `order_bys`:
          {get_order_bys_hints()}

"""


async def run_realtime_report(
    property_id: str,
    dimensions: List[str],
    metrics: List[str],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    order_bys: List[Dict[str, Any]] = None,
    limit: int = 100,
    return_property_quota: bool = False,
) -> Dict[str, Any]:
    """Runs a Google Analytics Data API realtime report.

    See
    https://developers.google.com/analytics/devguides/reporting/data/
    v1/realtime-basics
    for more information.

    Args:
        property_id: The Google Analytics property ID as a string
          (e.g., "213025502"). Get property IDs from
          get_account_summaries().
        dimensions: A list of dimensions to include in the report.
          Dimensions must be realtime dimensions.
        metrics: A list of metrics to include in the report. Metrics
          must be realtime metrics.
        dimension_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/
          reporting/data/v1/rest/v1beta/FilterExpression)
          to apply to the dimensions.  Don't use this for filtering
          metrics. Use metric_filter instead. The `field_name` in a
          `dimension_filter` must be a dimension, as defined in the
          `get_standard_dimensions` and `get_dimensions` tools.
          For more information about the expected format of this
          argument, see the `run_report_dimension_filter_hints` tool.
        metric_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/
          reporting/data/v1/rest/v1beta/FilterExpression)
          to apply to the metrics.  Don't use this for filtering
          dimensions. Use dimension_filter instead. The `field_name`
          in a `metric_filter` must be a metric, as defined in the
          `get_standard_metrics` and `get_metrics` tools.
          For more information about the expected format of this
          argument, see the `run_report_metric_filter_hints` tool.
        order_bys: A list of Data API OrderBy
          (https://developers.google.com/analytics/devguides/
          reporting/data/v1/rest/v1beta/OrderBy)
          objects to apply to the dimensions and metrics.
          For more information about the expected format of this
          argument, see the `run_report_order_bys_hints` tool.
        limit: The maximum number of rows to return. Value must be a
          positive integer <= 100,000. Default is 100. If unspecified
          by the API, it returns up to 10,000 rows.
        return_property_quota: Whether to return realtime property
          quota in the response.
    """
    # Always request quota to check if we're approaching limits
    request = data_v1beta.RunRealtimeReportRequest(
        property=construct_property_rn(property_id),
        dimensions=[
            data_v1beta.Dimension(name=dimension) for dimension in dimensions
        ],
        metrics=[data_v1beta.Metric(name=metric) for metric in metrics],
        return_property_quota=True,
    )

    if dimension_filter:
        request.dimension_filter = data_v1beta.FilterExpression(
            dimension_filter
        )

    if metric_filter:
        request.metric_filter = data_v1beta.FilterExpression(metric_filter)

    if order_bys:
        request.order_bys = [
            data_v1beta.OrderBy(order_by) for order_by in order_bys
        ]

    if limit:
        request.limit = limit

    response = await create_data_api_client().run_realtime_report(request)
    
    # Compact format - eliminate repetition
    result = {
        "row_count": response.row_count,
        "dimension_headers": [h.name for h in response.dimension_headers],
        "metric_headers": [h.name for h in response.metric_headers],
        "rows": [
            {
                "dimensions": [dv.value for dv in row.dimension_values],
                "metrics": [mv.value for mv in row.metric_values]
            }
            for row in response.rows
        ] if response.rows else []
    }
    
    # Include totals/maximums/minimums only if they have data
    if response.totals:
        result["totals"] = [
            proto_to_dict(total) for total in response.totals
        ]
    if response.maximums:
        result["maximums"] = [
            proto_to_dict(maximum) for maximum in response.maximums
        ]
    if response.minimums:
        result["minimums"] = [
            proto_to_dict(minimum) for minimum in response.minimums
        ]

    # Check quota usage and include if >90% used or explicitly requested
    if response.property_quota:
        quota_dict = proto_to_dict(response.property_quota)
        quota_warning = None

        # Check if any quota metric is >90% used
        for quota_name, quota_info in quota_dict.items():
            if (
                isinstance(quota_info, dict)
                and "consumed" in quota_info
                and "remaining" in quota_info
            ):
                consumed = quota_info.get("consumed", 0)
                remaining = quota_info.get("remaining", 0)
                total = consumed + remaining
                if total > 0 and (consumed / total) > 0.9:
                    quota_warning = (
                        f"WARNING: {quota_name} is at "
                        f"{(consumed / total * 100):.1f}% "
                        f"({consumed}/{total}). "
                        f"Approaching quota limit."
                    )
                    break
        
        # Include quota if explicitly requested or if usage >90%
        if return_property_quota or quota_warning:
            result["quota"] = quota_dict
            if quota_warning:
                result["quota_warning"] = quota_warning
    
    return result


# The `run_realtime_report` tool requires a more complex description
# that's generated at runtime. Uses the `add_tool` method instead of an
# annnotation since `add_tool` provides the flexibility needed to
# generate the description while also including the
# `run_realtime_report` method's docstring.
mcp.add_tool(
    run_realtime_report,
    title="Run a Google Analytics realtime report using the Data API",
    description=_run_realtime_report_description(),
)
