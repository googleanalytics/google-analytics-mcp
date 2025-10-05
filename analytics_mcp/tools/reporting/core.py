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

"""Tools for running core reports using the Data API."""

from typing import Any, Dict, List

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
from google.analytics import data_v1beta


def _run_report_description() -> str:
    """Returns the description for the `run_report` tool."""
    return f"""
          {run_report.__doc__}

          ## Hints for arguments

          Here are some hints that outline the expected format and requirements
          for arguments.

          ### Hints for `dimensions`

          The `dimensions` list must consist solely of either of the following:

          1.  Standard dimensions defined in the HTML table at
              https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema#dimensions.
              These dimensions are available to *every* property.
          2.  Custom dimensions for the `property_id`. Use the
              `get_custom_dimensions_and_metrics` tool to retrieve the list of
              custom dimensions for a property.

          ### Hints for `metrics`

          The `metrics` list must consist solely of either of the following:

          1.  Standard metrics defined in the HTML table at
              https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema#metrics.
              These metrics are available to *every* property.
          2.  Custom metrics for the `property_id`. Use the
              `get_custom_dimensions_and_metrics` tool to retrieve the list of
              custom metrics for a property.


          ### Hints for `date_ranges`:
          {get_date_ranges_hints()}

          ### Hints for `dimension_filter`:
          {get_dimension_filter_hints()}

          ### Hints for `metric_filter`:
          {get_metric_filter_hints()}

          ### Hints for `order_bys`:
          {get_order_bys_hints()}

          """


async def run_report(
    property_id: int | str,
    date_ranges: List[Dict[str, str]],
    dimensions: List[str],
    metrics: List[str],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    order_bys: List[Dict[str, Any]] = None,
    limit: int = None,
    offset: int = None,
    currency_code: str = None,
    return_property_quota: bool = False,
) -> Dict[str, Any]:
    """Runs a Google Analytics Data API report.

    Note that the reference docs at
    https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta
    all use camelCase field names, but field names passed to this method should
    be in snake_case since the tool is using the protocol buffers (protobuf)
    format. The protocol buffers for the Data API are available at
    https://github.com/googleapis/googleapis/tree/master/google/analytics/data/v1beta.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
        date_ranges: A list of date ranges
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/DateRange)
          to include in the report.
        dimensions: A list of dimensions to include in the report.
        metrics: A list of metrics to include in the report.
        dimension_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/FilterExpression)
          to apply to the dimensions.  Don't use this for filtering metrics. Use
          metric_filter instead. The `field_name` in a `dimension_filter` must
          be a dimension, as defined in the `get_standard_dimensions` and
          `get_dimensions` tools.
        metric_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/FilterExpression)
          to apply to the metrics.  Don't use this for filtering dimensions. Use
          dimension_filter instead. The `field_name` in a `metric_filter` must
          be a metric, as defined in the `get_standard_metrics` and
          `get_metrics` tools.
        order_bys: A list of Data API OrderBy
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/OrderBy)
          objects to apply to the dimensions and metrics.
        limit: The maximum number of rows to return in each response. Value must
          be a positive integer <= 250,000. Used to paginate through large
          reports, following the guide at
          https://developers.google.com/analytics/devguides/reporting/data/v1/basics#pagination.
        offset: The row count of the start row. The first row is counted as row
          0. Used to paginate through large
          reports, following the guide at
          https://developers.google.com/analytics/devguides/reporting/data/v1/basics#pagination.
        currency_code: The currency code to use for currency values. Must be in
          ISO4217 format, such as "AED", "USD", "JPY". If the field is empty, the
          report uses the property's default currency.
        return_property_quota: Whether to return property quota in the response.
    """
    request = data_v1beta.RunReportRequest(
        property=construct_property_rn(property_id),
        dimensions=[
            data_v1beta.Dimension(name=dimension) for dimension in dimensions
        ],
        metrics=[data_v1beta.Metric(name=metric) for metric in metrics],
        date_ranges=[data_v1beta.DateRange(dr) for dr in date_ranges],
        return_property_quota=return_property_quota,
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
    if offset:
        request.offset = offset
    if currency_code:
        request.currency_code = currency_code

    response = await create_data_api_client().run_report(request)

    return proto_to_dict(response)


# The `run_report` tool requires a more complex description that's generated at
# runtime. Uses the `add_tool` method instead of an annnotation since `add_tool`
# provides the flexibility needed to generate the description while also
# including the `run_report` method's docstring.
mcp.add_tool(
    run_report,
    title="Run a Google Analytics Data API report using the Data API",
    description=_run_report_description(),
)
