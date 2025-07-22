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
from analytics_mcp.tools.utils import (
    create_data_api_client,
    proto_to_dict,
    proto_to_json,
)
from google.analytics import data_v1beta

# Common notes to consider when applying dimension and metric filters.
_FILTER_NOTES = """
  Notes:
    The API applies the `dimension_filter` and `metric_filter`
    independently. As a result, some complex combinations of dimension and
    metric filters are not possible in a single report request.

    For example, you can't create a `dimension_filter` and `metric_filter`
    combination for the following condition:

    (
      (eventName = "page_view" AND eventCount > 100)
      OR
      (eventName = "join_group" AND eventCount < 50)
    )

    This isn't possible because there's no way to apply the condition
    "eventCount > 100" only to the data with eventName of "page_view", and
    the condition "eventCount < 50" only to the data with eventName of
    "join_group".

    More generally, you can't define a `dimension_filter` and `metric_filter`
    for:

    (
      ((dimension condition D1) AND (metric condition M1))
      OR
      ((dimension condition D2) AND (metric condition M2))
    )

    If you have complex conditions like this, either:

    a)  Run a single report that applies a subset of the conditions that
        the API supports as well as the data needed to perform filtering of the
        API response on the client side. For example, for the condition:
        (
          (eventName = "page_view" AND eventCount > 100)
          OR
          (eventName = "join_group" AND eventCount < 50)
        )
        You could run a report that filters only on:
        eventName one of "page_view" or "join_group"
        and include the eventCount metric, then filter the API response on the
        client side to apply the different metric filters for the different
        events.

    or

    b)  Run a separate report for each combination of dimension condition and
        metric condition. For the example above, you'd run one report for the
        combination of (D1 AND M1), and another report for the combination of
        (D2 AND M2).

    Try to run fewer reports (option a) if possible. However, if running
    fewer reports results in excessive quota usage for the API, use option
    b. More information on quota usage is at
    https://developers.google.com/analytics/blog/2023/data-api-quota-management.
  """


@mcp.tool(
    title="Retrieves Core Reporting Dimensions for a specific property, including its custom dimensions"
)
async def get_dimensions(property_id: str) -> Dict[str, Any]:
    """Returns a list of core reporting dimensions for a property.

    Custom dimensions have `custom_definition: True`.
    """
    if property_id is None:
        raise ValueError("Must supply a property ID")
    if property_id.startswith("properties/"):
        property_id = property_id.split("/")[-1]
    metadata = await create_data_api_client().get_metadata(
        name=f"properties/{property_id}/metadata"
    )
    # Creates a new Metadata object that only contains the dimensions.
    metadata = data_v1beta.Metadata(
        name=metadata.name, dimensions=metadata.dimensions
    )
    return proto_to_dict(metadata)


@mcp.tool(
    title="Retrieves Core Reporting Metrics for a specific property, including its custom dimensions"
)
async def get_metrics(property_id: str) -> Dict[str, Any]:
    """Returns a list of core reporting metrics for a property.

    Custom metrics have `custom_definition: True`.
    """
    metadata = await create_data_api_client().get_metadata(
        name=f"properties/{property_id}/metadata"
    )
    # Creates a new Metadata object that only contains the metrics.
    metadata = data_v1beta.Metadata(
        name=metadata.name, metrics=metadata.metrics
    )
    return proto_to_dict(metadata)


@mcp.tool(title="Retrieves the list of standard dimensions")
def get_standard_dimensions() -> str:
    """Returns a list of standard dimensions."""
    return f"""Standard dimensions defined in the HTML table at
    https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema#dimensions
    These dimensions are available to *every* property"""


@mcp.tool(title="Retrieves the list of standard metrics")
def get_standard_metrics() -> str:
    """Returns a list of standard metrics."""
    return f"""Standard metrics defined in the HTML table at
      https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema#metrics
      These metrics are available to *every* property"""


@mcp.tool(
    title="Provides hints about the expected values for the date_ranges argument for the run_report tool"
)
def run_report_date_ranges_hints():
    range_jan = data_v1beta.DateRange(
        start_date="2025-01-01", end_date="2025-01-31", name="Jan2025"
    )
    range_feb = data_v1beta.DateRange(
        start_date="2025-02-01", end_date="2025-02-28", name="Feb2025"
    )
    range_last_2_days = data_v1beta.DateRange(
        start_date="yesterday", end_date="today", name="YesterdayAndToday"
    )
    range_prev_30_days = data_v1beta.DateRange(
        start_date="30daysAgo", end_date="yesterday", name="Previous30Days"
    )

    return f"""Example date_range arguments:
      1. A single date range:

        [ {proto_to_json(range_jan)} ]

      2. A relative date range using 'yesterday' and 'today':
        [ {proto_to_json(range_last_2_days)} ]

      3. A relative date range using 'NdaysAgo' and 'today':
        [ {proto_to_json(range_prev_30_days)}]

      4. Multiple date ranges:
        [ {proto_to_json(range_jan)}, {proto_to_json(range_feb)} ]
    """


@mcp.tool(
    title=(
        "Provides hints about the expected values for the metric_filter "
        "argument for the run_report and run_realtime_report tools"
    )
)
def run_report_metric_filter_hints():
    """Returns examples of valid metric_filter arguments for the run_report and run_realtime_report tools."""
    event_count_gt_10_filter = data_v1beta.FilterExpression(
        filter=data_v1beta.Filter(
            field_name="eventCount",
            numeric_filter=data_v1beta.Filter.NumericFilter(
                operation=data_v1beta.Filter.NumericFilter.Operation.GREATER_THAN,
                value=data_v1beta.NumericValue(int64_value=10),
            ),
        )
    )
    not_filter = data_v1beta.FilterExpression(
        not_expression=event_count_gt_10_filter
    )
    empty_filter = data_v1beta.FilterExpression(
        filter=data_v1beta.Filter(
            field_name="purchaseRevenue",
            empty_filter=data_v1beta.Filter.EmptyFilter(),
        )
    )
    revenue_between_filter = data_v1beta.FilterExpression(
        filter=data_v1beta.Filter(
            field_name="purchaseRevenue",
            between_filter=data_v1beta.Filter.BetweenFilter(
                from_value=data_v1beta.NumericValue(double_value=10.0),
                to_value=data_v1beta.NumericValue(double_value=25.0),
            ),
        )
    )
    and_filter = data_v1beta.FilterExpression(
        and_group=data_v1beta.FilterExpressionList(
            expressions=[event_count_gt_10_filter, revenue_between_filter]
        )
    )
    or_filter = data_v1beta.FilterExpression(
        or_group=data_v1beta.FilterExpressionList(
            expressions=[event_count_gt_10_filter, revenue_between_filter]
        )
    )
    return (
        f"""Example metric_filter arguments:
      1. A simple filter:
        {proto_to_json(event_count_gt_10_filter)}

      2. A NOT filter:
        {proto_to_json(not_filter)}

      3. An empty value filter:
        {proto_to_json(empty_filter)}

      4. An AND group filter:
        {proto_to_json(and_filter)}

      5. An OR group filter:
        {proto_to_json(or_filter)}

    """
        + _FILTER_NOTES
    )


@mcp.tool(
    title=(
        "Provides hints about the expected values for the dimension_filter "
        "argument for the run_report and run_realtime_report tools"
    )
)
def run_report_dimension_filter_hints():
    """Returns examples of valid dimension_filter arguments for the run_report and run_realtime_report tools."""
    begins_with = data_v1beta.FilterExpression(
        filter=data_v1beta.Filter(
            field_name="eventName",
            string_filter=data_v1beta.Filter.StringFilter(
                match_type=data_v1beta.Filter.StringFilter.MatchType.BEGINS_WITH,
                value="add",
            ),
        )
    )
    not_filter = data_v1beta.FilterExpression(not_expression=begins_with)
    empty_filter = data_v1beta.FilterExpression(
        filter=data_v1beta.Filter(
            field_name="source", empty_filter=data_v1beta.Filter.EmptyFilter()
        )
    )
    source_medium_filter = data_v1beta.FilterExpression(
        filter=data_v1beta.Filter(
            field_name="sourceMedium",
            string_filter=data_v1beta.Filter.StringFilter(
                match_type=data_v1beta.Filter.StringFilter.MatchType.EXACT,
                value="google / cpc",
            ),
        )
    )
    event_list_filter = data_v1beta.FilterExpression(
        filter=data_v1beta.Filter(
            field_name="eventName",
            in_list_filter=data_v1beta.Filter.InListFilter(
                case_sensitive=True,
                values=["first_visit", "purchase", "add_to_cart"],
            ),
        )
    )
    and_filter = data_v1beta.FilterExpression(
        and_group=data_v1beta.FilterExpressionList(
            expressions=[source_medium_filter, event_list_filter]
        )
    )
    or_filter = data_v1beta.FilterExpression(
        or_group=data_v1beta.FilterExpressionList(
            expressions=[source_medium_filter, event_list_filter]
        )
    )
    return (
        f"""Example dimension_filter arguments:
      1. A simple filter:
        {proto_to_json(begins_with)}

      2. A NOT filter:
        {proto_to_json(not_filter)}

      3. An empty value filter:
        {proto_to_json(empty_filter)}

      4. An AND group filter:
        {proto_to_json(and_filter)}

      5. An OR group filter:
        {proto_to_json(or_filter)}

    """
        + _FILTER_NOTES
    )


@mcp.tool(
    title=(
        "Provide hints about the expected values for the order_bys argument for the run_report and run_realtime_report tools"
    )
)
def run_report_order_bys_hints():
    """Returns examples of valid order_bys arguments for the run_report and run_realtime_report tools."""
    dimension_alphanumeric_ascending = data_v1beta.OrderBy(
        dimension=data_v1beta.OrderBy.DimensionOrderBy(
            dimension_name="eventName",
            order_type=data_v1beta.OrderBy.DimensionOrderBy.OrderType.ALPHANUMERIC,
        ),
        desc=False,
    )
    dimension_alphanumeric_no_case_descending = data_v1beta.OrderBy(
        dimension=data_v1beta.OrderBy.DimensionOrderBy(
            dimension_name="campaignName",
            order_type=data_v1beta.OrderBy.DimensionOrderBy.OrderType.CASE_INSENSITIVE_ALPHANUMERIC,
        ),
        desc=True,
    )
    dimension_numeric_ascending = data_v1beta.OrderBy(
        dimension=data_v1beta.OrderBy.DimensionOrderBy(
            dimension_name="audienceId",
            order_type=data_v1beta.OrderBy.DimensionOrderBy.OrderType.NUMERIC,
        ),
        desc=False,
    )
    metric_ascending = data_v1beta.OrderBy(
        metric=data_v1beta.OrderBy.MetricOrderBy(
            metric_name="eventCount",
        ),
        desc=False,
    )
    metric_descending = data_v1beta.OrderBy(
        metric=data_v1beta.OrderBy.MetricOrderBy(
            metric_name="eventValue",
        ),
        desc=True,
    )

    return f"""Example order_bys arguments:

    1.  Order by ascending 'eventName':
        [ {proto_to_json(dimension_alphanumeric_ascending)} ]

    2.  Order by descending 'eventName', ignoring case:
        [ {proto_to_json(dimension_alphanumeric_no_case_descending)} ]

    3.  Order by ascending 'audienceId':
        [ {proto_to_json(dimension_numeric_ascending)} ]

    4.  Order by descending 'eventCount':
        [ {proto_to_json(metric_descending)} ]

    5.  Order by ascending 'eventCount':
        [ {proto_to_json(metric_ascending)} ]

    6.  Combination of dimension and metric order bys:
        [
          {proto_to_json(dimension_alphanumeric_ascending)},
          {proto_to_json(metric_descending)},
        ]

    7.  Order by multiple dimensions and metrics:
        [
          {proto_to_json(dimension_alphanumeric_ascending)},
          {proto_to_json(dimension_numeric_ascending)},
          {proto_to_json(metric_descending)},
        ]

    The dimensions and metrics in order_bys must also be present in the report
    request's "dimensions" and "metrics" arguments, respectively.
    """


@mcp.tool(title="Run a Google Analytics report using the Data API")
async def run_report(
    property_id: str,
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
        property_id: The Google Analytics property ID.
        date_ranges: A list of date ranges
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/DateRange)
          to include in the report.
          For more information about the expected format of this argument, see
          the `run_report_date_ranges_hints` tool.
        dimensions: A list of dimensions to include in the report.
        metrics: A list of metrics to include in the report.
        dimension_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/FilterExpression)
          to apply to the dimensions.  Don't use this for filtering metrics. Use
          metric_filter instead. The `field_name` in a `dimension_filter` must
          be a dimension, as defined in the `get_standard_dimensions` and
          `get_dimensions` tools.
          For more information about the expected format of this argument, see
          the `run_report_dimension_filter_hints` tool.
        metric_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/FilterExpression)
          to apply to the metrics.  Don't use this for filtering dimensions. Use
          dimension_filter instead. The `field_name` in a `metric_filter` must
          be a metric, as defined in the `get_standard_metrics` and
          `get_metrics` tools.
          For more information about the expected format of this argument, see
          the `run_report_metric_filter_hints` tool.
        order_bys: A list of Data API OrderBy
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/OrderBy)
          objects to apply to the dimensions and metrics.
          For more information about the expected format of this argument, see
          the `run_report_order_bys_hints` tool.
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
        property=f"properties/{property_id}",
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
