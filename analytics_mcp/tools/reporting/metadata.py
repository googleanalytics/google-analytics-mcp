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

"""Metadata to provide context and hints for reporting tools."""

from typing import Any, Dict, List

from analytics_mcp.coordinator import mcp
from analytics_mcp.tools.utils import (
    construct_property_rn,
    create_data_api_client,
    proto_to_dict,
    proto_to_json,
)
from google.analytics import data_v1beta


def get_date_ranges_hints():
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


def get_metric_filter_hints():
    """Returns hints and samples for metric_filter arguments."""
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


def get_dimension_filter_hints():
    """Returns hints and samples for dimension_filter arguments."""
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


def get_order_bys_hints():
    """Returns hints and examples for order_bys arguments."""
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


@mcp.tool(
    title="Retrieves the custom Core Reporting dimensions and metrics for a specific property"
)
async def get_custom_dimensions_and_metrics(
    property_id: int | str,
) -> Dict[str, List[Dict[str, Any]]]:
    """Returns the property's custom dimensions and metrics.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number

    """
    metadata = await create_data_api_client().get_metadata(
        name=f"{construct_property_rn(property_id)}/metadata"
    )
    custom_metrics = [
        proto_to_dict(metric)
        for metric in metadata.metrics
        if metric.custom_definition
    ]
    custom_dimensions = [
        proto_to_dict(dimension)
        for dimension in metadata.dimensions
        if dimension.custom_definition
    ]
    return {
        "custom_dimensions": custom_dimensions,
        "custom_metrics": custom_metrics,
    }
