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

"""Tools for running batch reports using the Data API."""

import asyncio
from typing import Any, Dict, List

from analytics_mcp.tools.reporting.metadata import (
    get_date_ranges_hints,
    get_dimension_filter_hints,
    get_metric_filter_hints,
    get_order_bys_hints,
)
from analytics_mcp.tools.utils import (
    construct_property_rn,
    proto_to_dict,
)
from analytics_mcp.tools.client import create_data_api_client
from google.analytics import data_v1beta


def _batch_run_reports_description() -> str:
    """Returns the description for the `batch_run_reports` tool."""
    return f"""
          {batch_run_reports.__doc__}

          ## Hints for arguments

          Here are some hints that outline the expected format and
          requirements for arguments. Each object in the `requests`
          list uses the same argument formats as the `run_report` tool.

          ### Hints for `dimensions`

          The `dimensions` list must consist solely of either of the
          following:

          1.  Standard dimensions defined in the HTML table at
              https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema#dimensions.
              These dimensions are available to *every* property.
          2.  Custom dimensions for the `property_id`. Use the
              `get_custom_dimensions_and_metrics` tool to retrieve the
              list of custom dimensions for a property.

          ### Hints for `metrics`

          The `metrics` list must consist solely of either of the
          following:

          1.  Standard metrics defined in the HTML table at
              https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema#metrics.
              These metrics are available to *every* property.
          2.  Custom metrics for the `property_id`. Use the
              `get_custom_dimensions_and_metrics` tool to retrieve the
              list of custom metrics for a property.


          ### Hints for `date_ranges`:
          {get_date_ranges_hints()}

          ### Hints for `dimension_filter`:
          {get_dimension_filter_hints()}

          ### Hints for `metric_filter`:
          {get_metric_filter_hints()}

          ### Hints for `order_bys`:
          {get_order_bys_hints()}

          """


def _build_report_request(
    property_rn: str, report: Dict[str, Any]
) -> data_v1beta.RunReportRequest:
    """Builds a RunReportRequest proto from a report specification dict.

    Args:
        property_rn: The property resource name (e.g. "properties/12345").
        report: A dict with keys matching the `run_report` tool's
            parameters: `dimensions`, `metrics`, `date_ranges`, and
            optionally `dimension_filter`, `metric_filter`, `order_bys`,
            `limit`, `offset`, `currency_code`, `return_property_quota`.

    Returns:
        A RunReportRequest proto.
    """
    request = data_v1beta.RunReportRequest(
        property=property_rn,
        dimensions=[
            data_v1beta.Dimension(name=d) for d in report["dimensions"]
        ],
        metrics=[data_v1beta.Metric(name=m) for m in report["metrics"]],
        date_ranges=[data_v1beta.DateRange(dr) for dr in report["date_ranges"]],
        return_property_quota=report.get("return_property_quota", False),
    )

    dimension_filter = report.get("dimension_filter")
    if dimension_filter:
        request.dimension_filter = data_v1beta.FilterExpression(
            dimension_filter
        )

    metric_filter = report.get("metric_filter")
    if metric_filter:
        request.metric_filter = data_v1beta.FilterExpression(metric_filter)

    order_bys = report.get("order_bys")
    if order_bys:
        request.order_bys = [data_v1beta.OrderBy(ob) for ob in order_bys]

    limit = report.get("limit")
    if limit:
        request.limit = limit

    offset = report.get("offset")
    if offset:
        request.offset = offset

    currency_code = report.get("currency_code")
    if currency_code:
        request.currency_code = currency_code

    return request


async def batch_run_reports(
    property_id: int | str,
    requests: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Runs multiple Google Analytics Data API reports in a single request.

    Use this tool instead of calling `run_report` multiple times when you
    need data from several reports for the same property. This reduces
    latency by combining up to 5 reports into one API call.

    Each object in the `requests` list accepts the same arguments as the
    `run_report` tool.

    Note that the reference docs at
    https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta
    all use camelCase field names, but field names passed to this method
    should be in snake_case since the tool is using the protocol buffers
    (protobuf) format. The protocol buffers for the Data API are available
    at
    https://github.com/googleapis/googleapis/tree/master/google/analytics/data/v1beta.

    Args:
        property_id: The Google Analytics property ID. Accepted formats
          are:
          - A number
          - A string consisting of 'properties/' followed by a number
        requests: A list of 1 to 5 report request objects. Each object
          must contain the following required keys:
          - `dimensions`: A list of dimensions to include in the report.
          - `metrics`: A list of metrics to include in the report.
          - `date_ranges`: A list of date ranges
            (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/DateRange)
            to include in the report.

          Each object may also contain the following optional keys:
          - `dimension_filter`: A Data API FilterExpression
            (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/FilterExpression)
            to apply to the dimensions.
          - `metric_filter`: A Data API FilterExpression to apply to the
            metrics.
          - `order_bys`: A list of Data API OrderBy
            (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/OrderBy)
            objects.
          - `limit`: The maximum number of rows to return (max 250,000).
          - `offset`: The row count of the start row (0-indexed).
          - `currency_code`: An ISO4217 currency code (e.g. "USD").
          - `return_property_quota`: Whether to return property quota
            information in the response (default: false).
    """
    if not isinstance(requests, list):
        raise ValueError("requests must be a list.")
    if not requests:
        raise ValueError("requests must contain at least one report request.")
    if len(requests) > 5:
        raise ValueError(
            "requests must contain at most 5 report requests. "
            f"Got {len(requests)}."
        )

    for i, report in enumerate(requests):
        if not isinstance(report, dict):
            raise ValueError(f"Request {i + 1} must be a dictionary.")
        for key in ("dimensions", "metrics", "date_ranges"):
            if key not in report:
                raise ValueError(
                    f"Request {i + 1} is missing required key " f"'{key}'."
                )
            if not isinstance(report[key], list):
                raise ValueError(f"Request {i + 1} '{key}' must be a list.")

    property_rn = construct_property_rn(property_id)

    batch_request = data_v1beta.BatchRunReportsRequest(
        property=property_rn,
        requests=[_build_report_request(property_rn, r) for r in requests],
    )

    def _sync_call():
        return create_data_api_client().batch_run_reports(batch_request)

    response = await asyncio.to_thread(_sync_call)

    return proto_to_dict(response)
