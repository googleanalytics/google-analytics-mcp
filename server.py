#!/usr/bin/env python

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

from typing import Any, Dict, List

from google.analytics import admin_v1beta, data_v1beta
from google.api_core.gapic_v1.client_info import ClientInfo
from mcp.server.fastmcp import FastMCP
import google.auth
import proto

mcp = FastMCP("Google Analytics Server")

# NOTE: Gemini doesn't recognize MCP resources or prompts, so all items are
# defined as tools.

# Data API tools for standard reports (run_report)


# Client information that adds a custom user agent to all API requests.
_CLIENT_INFO = ClientInfo(user_agent="analytics-mcp/0.0.1")

# Read-only scope for Analytics Admin API and Analytics Data API.
_READ_ONLY_ANALYTICS_SCOPE = (
    "https://www.googleapis.com/auth/analytics.readonly"
)

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


def _create_admin_api_client():
    """Returns a properly configured Google Analytics Admin API client.

    Uses Application Default Credentials with read-only scope.
    """
    (credentials, _) = google.auth.default(scopes=[_READ_ONLY_ANALYTICS_SCOPE])
    client = admin_v1beta.AnalyticsAdminServiceClient(
        client_info=_CLIENT_INFO, credentials=credentials
    )
    return client


def _create_data_api_client():
    """Returns a properly configured Google Analytics Data API client.

    Uses Application Default Credentials with read-only scope.
    """
    (credentials, _) = google.auth.default(scopes=[_READ_ONLY_ANALYTICS_SCOPE])
    client = data_v1beta.BetaAnalyticsDataClient(
        client_info=_CLIENT_INFO, credentials=credentials
    )
    return client


def _proto_to_dict(obj: proto.Message) -> Dict[str, Any]:
    """Converts a proto message to a dictionary."""
    return type(obj).to_dict(
        obj, use_integers_for_enums=False, preserving_proto_field_name=True
    )


def _proto_to_json(obj: proto.Message) -> str:
    """Converts a proto message to a JSON string."""
    return type(obj).to_json(obj, indent=None, preserving_proto_field_name=True)


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
    title="Retrieves Core Reporting Dimensions for a specific property, including its custom dimensions"
)
def get_dimensions(property_id: str) -> Dict[str, Any]:
    """Returns a list of core reporting dimensions for a property.

    Custom dimensions have `custom_definition: True`.
    """
    if property_id is None:
        raise ValueError("Must supply a property ID")
    if property_id.startswith("properties/"):
        property_id = property_id.split("/")[-1]
    metadata = _create_data_api_client().get_metadata(
        name=f"properties/{property_id}/metadata"
    )
    # Creates a new Metadata object that only contains the dimensions.
    metadata = data_v1beta.Metadata(
        name=metadata.name, dimensions=metadata.dimensions
    )
    return _proto_to_dict(metadata)


@mcp.tool(
    title="Retrieves Core Reporting Metrics for a specific property, including its custom dimensions"
)
def get_metrics(property_id: str) -> Dict[str, Any]:
    """Returns a list of core reporting metrics for a property.

    Custom metrics have `custom_definition: True`.
    """
    metadata = _create_data_api_client().get_metadata(
        name=f"properties/{property_id}/metadata"
    )
    # Creates a new Metadata object that only contains the metrics.
    metadata = data_v1beta.Metadata(
        name=metadata.name, metrics=metadata.metrics
    )
    return _proto_to_dict(metadata)


@mcp.tool(title="Gets details about a property")
def get_property_details(property_id: str) -> Dict[str, Any]:
    """Returns details about a property.
    Args:
        property_id: The ID of the property.
    """
    client = admin_v1beta.AnalyticsAdminServiceClient()
    property_resource_name = f"properties/{property_id}"
    request = admin_v1beta.GetPropertyRequest(name=property_resource_name)
    response = client.get_property(request=request)
    return _proto_to_dict(response)


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

        [ {_proto_to_json(range_jan)} ]

      2. A relative date range using 'yesterday' and 'today':
        [ {_proto_to_json(range_last_2_days)} ]

      3. A relative date range using 'NdaysAgo' and 'today':
        [ {_proto_to_json(range_prev_30_days)}]

      4. Multiple date ranges:
        [ {_proto_to_json(range_jan)}, {_proto_to_json(range_feb)} ]
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
        {_proto_to_json(event_count_gt_10_filter)}

      2. A NOT filter:
        {_proto_to_json(not_filter)}

      3. An empty value filter:
        {_proto_to_json(empty_filter)}

      4. An AND group filter:
        {_proto_to_json(and_filter)}

      5. An OR group filter:
        {_proto_to_json(or_filter)}

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
        {_proto_to_json(begins_with)}

      2. A NOT filter:
        {_proto_to_json(not_filter)}

      3. An empty value filter:
        {_proto_to_json(empty_filter)}

      4. An AND group filter:
        {_proto_to_json(and_filter)}

      5. An OR group filter:
        {_proto_to_json(or_filter)}

    """
        + _FILTER_NOTES
    )


@mcp.tool(title="Run a Google Analytics report using the Data API")
def run_report(
    property_id: str,
    date_ranges: List[Dict[str, str]],
    dimensions: List[str],
    metrics: List[str],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    limit: int = None,
    offset: int = None,
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
        limit: The maximum number of rows to return in each response. Value must
          be a positive integer <= 250,000. Used to paginate through large
          reports, following the guide at
          https://developers.google.com/analytics/devguides/reporting/data/v1/basics#pagination.
        offset: The row count of the start row. The first row is counted as row
          0. Used to paginate through large
          reports, following the guide at
          https://developers.google.com/analytics/devguides/reporting/data/v1/basics#pagination.
    """
    request = data_v1beta.RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            data_v1beta.Dimension(name=dimension) for dimension in dimensions
        ],
        metrics=[data_v1beta.Metric(name=metric) for metric in metrics],
        date_ranges=[data_v1beta.DateRange(dr) for dr in date_ranges],
    )

    if dimension_filter:
        request.dimension_filter = data_v1beta.FilterExpression(
            dimension_filter
        )

    if metric_filter:
        request.metric_filter = data_v1beta.FilterExpression(metric_filter)

    if limit:
        request.limit = limit
    if offset:
        request.offset = offset

    response = _create_data_api_client().run_report(request)

    return _proto_to_dict(response)


# Data API tools for realtime reports (run_report)


@mcp.tool(title="Retrieves the list of realtime reporting dimensions")
def get_realtime_dimensions() -> str:
    """Returns a list of realtime dimensions."""
    return f"""Realtime dimensions defined in the HTML table at
    https://developers.google.com/analytics/devguides/reporting/data/v1/realtime-api-schema#dimensions
    These dimensions are available to *every* property"""


@mcp.tool(title="Retrieves the list of realtime metrics")
def get_realtime_metrics() -> str:
    """Returns a list of realtime metrics."""
    return f"""realtime metrics defined in the HTML table at
      https://developers.google.com/analytics/devguides/reporting/data/v1/realtime-api-schema#metrics
      These metrics are available to *every* property"""


@mcp.tool(title="Run a Google Analytics realtime report using the Data API")
def run_realtime_report(
    property_id: str,
    dimensions: List[str],
    metrics: List[str],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    limit: int = None,
    offset: int = None,
) -> Dict[str, Any]:
    """Runs a Google Analytics Data API realtime report.

    See
    https://developers.google.com/analytics/devguides/reporting/data/v1/realtime-basics
    for more information.

    Args:
        property_id: The Google Analytics property ID.
        dimensions: A list of dimensions to include in the report. Dimensions must be realtime dimensions.
        metrics: A list of metrics to include in the report. Metrics must be realtime metrics.
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
        limit: The maximum number of rows to return in each response. Value must
          be a positive integer <= 250,000. Used to paginate through large
          reports, following the guide at
          https://developers.google.com/analytics/devguides/reporting/data/v1/basics#pagination.
        offset: The row count of the start row. The first row is counted as row
          0. Used to paginate through large
          reports, following the guide at
          https://developers.google.com/analytics/devguides/reporting/data/v1/basics#pagination.
    """
    if property_id.startswith("properties/"):
        property_id = property_id.split("/")[-1]

    request = data_v1beta.RunRealtimeReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            data_v1beta.Dimension(name=dimension) for dimension in dimensions
        ],
        metrics=[data_v1beta.Metric(name=metric) for metric in metrics],
    )

    if dimension_filter:
        request.dimension_filter = data_v1beta.FilterExpression(
            dimension_filter
        )

    if metric_filter:
        request.metric_filter = data_v1beta.FilterExpression(metric_filter)

    if limit:
        request.limit = limit
    if offset:
        request.offset = offset

    response = _create_data_api_client().run_realtime_report(request)
    return _proto_to_dict(response)


# Admin API tools


@mcp.tool()
def get_account_summaries() -> List[Dict[str, Any]]:
    """Retrieves information about the user's Google Analytics accounts and properties."""

    # Uses a List comprehension so the pager returned by list_account_summaries
    # retrieves all pages.
    summary_pager = _create_admin_api_client().list_account_summaries()
    all_pages = [_proto_to_dict(summary_page) for summary_page in summary_pager]
    return all_pages


@mcp.tool(title="List links to Google Ads accounts")
def list_google_ads_links(property_id: str) -> List[Dict[str, Any]]:
    """Returns a list of links to Google Ads accounts for a property.

    Args:
        property_id: The ID of the property.
    """
    property_resource_name = f"properties/{property_id}"
    request = admin_v1beta.ListGoogleAdsLinksRequest(
        parent=property_resource_name
    )
    # Uses a List comprehension so the pager returned by list_google_ads_links
    # retrieves all pages.
    links_pager = _create_admin_api_client().list_google_ads_links(
        request=request
    )
    all_pages = [_proto_to_dict(link_page) for link_page in links_pager]
    return all_pages


if __name__ == "__main__":
    mcp.run()
