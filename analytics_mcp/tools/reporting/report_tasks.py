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

"""Tools for running report tasks using the Data API (Alpha).

The Data API builds report tasks asynchronously, and a report task is the only
report surface whose definition carries a `sampling_level`. Use these tools
when a report needs a larger sample, or no sampling at all, than the default
`run_report` request provides.
"""

import asyncio
import time
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
from analytics_mcp.tools.client import create_data_api_alpha_client
from google.analytics import data_v1alpha

# Interval between polls while waiting for a report task to become ACTIVE.
_POLL_INTERVAL_SECONDS = 2.0

# Bounds for the `timeout_seconds` argument.
_MIN_TIMEOUT_SECONDS = 1
_MAX_TIMEOUT_SECONDS = 300

# Accepted `sampling_level` values, keyed by lowercase name.
_SAMPLING_LEVELS = {
    "low": data_v1alpha.SamplingLevel.LOW,
    "medium": data_v1alpha.SamplingLevel.MEDIUM,
    "unsampled": data_v1alpha.SamplingLevel.UNSAMPLED,
}


def _sampling_level_hints() -> str:
    """Returns hints and examples for the `sampling_level` argument."""
    return """The `sampling_level` argument controls how much of the available
        data the report reads, trading accuracy for speed. Accepted values,
        case-insensitive:

        - `"LOW"`: sample the data, using the most recent events first.
        - `"MEDIUM"`: sample the data, using a larger sample than `"LOW"`.
        - `"UNSAMPLED"`: read every available event instead of sampling.

        Omit `sampling_level` to keep the API default for the property. A
        report that is too large to build unsampled can fail instead of
        returning sampled data, so prefer `"MEDIUM"` when the report covers a
        long date range or a large property."""


def _run_report_task_description() -> str:
    """Returns the description for the `run_report_task` tool."""
    return f"""
          {run_report_task.__doc__}

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

          ### Hints for `sampling_level`:

          {_sampling_level_hints()}

          ### Hints for `date_ranges`:
          {get_date_ranges_hints()}

          ### Hints for `dimension_filter`:
          {get_dimension_filter_hints()}

          ### Hints for `metric_filter`:
          {get_metric_filter_hints()}

          ### Hints for `order_bys`:
          {get_order_bys_hints()}

          """


def _parse_sampling_level(sampling_level: str) -> int:
    """Returns the SamplingLevel enum value for a level name.

    Args:
        sampling_level: One of 'LOW', 'MEDIUM' or 'UNSAMPLED', case-insensitive.

    Returns:
        The matching `data_v1alpha.SamplingLevel` enum value.

    Raises:
        ValueError: If the level name is not recognized.
    """
    level = (
        _SAMPLING_LEVELS.get(sampling_level.strip().lower())
        if isinstance(sampling_level, str)
        else None
    )
    if level is None:
        raise ValueError(
            f"Invalid sampling_level: {sampling_level}. "
            "Use 'LOW', 'MEDIUM' or 'UNSAMPLED'."
        )
    return level


def _report_task_state(report_task: Any) -> str:
    """Returns the state of a report task as an enum name, such as 'ACTIVE'."""
    return data_v1alpha.ReportTask.ReportMetadata.State(
        report_task.report_metadata.state
    ).name


def _build_report_definition(
    date_ranges: List[Dict[str, Any]],
    dimensions: List[str],
    metrics: List[str],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    order_bys: List[Dict[str, Any]] = None,
    limit: int = None,
    offset: int = None,
    currency_code: str = None,
    sampling_level: str = None,
) -> data_v1alpha.ReportTask.ReportDefinition:
    """Builds the ReportDefinition for a report task."""
    report_definition = data_v1alpha.ReportTask.ReportDefinition(
        dimensions=[
            data_v1alpha.Dimension(name=dimension) for dimension in dimensions
        ],
        metrics=[data_v1alpha.Metric(name=metric) for metric in metrics],
        date_ranges=[data_v1alpha.DateRange(dr) for dr in date_ranges],
    )

    if dimension_filter:
        report_definition.dimension_filter = data_v1alpha.FilterExpression(
            dimension_filter
        )

    if metric_filter:
        report_definition.metric_filter = data_v1alpha.FilterExpression(
            metric_filter
        )

    if order_bys:
        report_definition.order_bys = [
            data_v1alpha.OrderBy(order_by) for order_by in order_bys
        ]

    if limit:
        report_definition.limit = limit
    if offset:
        report_definition.offset = offset
    if currency_code:
        report_definition.currency_code = currency_code
    if sampling_level:
        report_definition.sampling_level = _parse_sampling_level(sampling_level)

    return report_definition


def _wait_for_report_task(
    client: Any, report_task: Any, timeout_seconds: int
) -> Any:
    """Polls a report task until it is ACTIVE.

    Args:
        client: The Data API (Alpha) client.
        report_task: The ReportTask returned when it was created.
        timeout_seconds: Seconds to wait before giving up.

    Returns:
        The ReportTask once it is ACTIVE.

    Raises:
        RuntimeError: If the report task fails while being created.
        TimeoutError: If the report task is still CREATING after the timeout.
    """
    name = report_task.name
    deadline = time.monotonic() + timeout_seconds
    while _report_task_state(report_task) == "CREATING":
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Report task {name} is still CREATING after "
                f"{timeout_seconds} seconds. It stays queryable for 72 hours; "
                "increase timeout_seconds or retry later."
            )
        time.sleep(_POLL_INTERVAL_SECONDS)
        report_task = client.get_report_task(name=name)

    state = _report_task_state(report_task)
    if state == "FAILED":
        error_message = report_task.report_metadata.error_message
        raise RuntimeError(
            f"Report task {name} failed: {error_message or 'unknown error'}"
        )
    return report_task


async def run_report_task(
    property_id: int | str,
    date_ranges: List[Dict[str, Any]],
    dimensions: List[str],
    metrics: List[str],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    order_bys: List[Dict[str, Any]] = None,
    limit: int = None,
    offset: int = None,
    currency_code: str = None,
    sampling_level: str = None,
    timeout_seconds: int = 120,
) -> Dict[str, Any]:
    """Runs a Google Analytics Data API report task.

    A report task is the Data API report surface that accepts a
    `sampling_level`, so use this tool instead of `run_report` when a report
    needs a larger sample or an unsampled result. The report is built
    asynchronously; this tool waits for it and returns its rows.

    Note that the reference docs at
    https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1alpha
    all use camelCase field names, but field names passed to this method should
    be in snake_case since the tool is using the protocol buffers (protobuf)
    format.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
        date_ranges: A list of date ranges
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1alpha/DateRange)
          to include in the report.
        dimensions: A list of dimensions to include in the report.
        metrics: A list of metrics to include in the report.
        dimension_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1alpha/FilterExpression)
          to apply to the dimensions.  Don't use this for filtering metrics. Use
          metric_filter instead.
        metric_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1alpha/FilterExpression)
          to apply to the metrics.  Don't use this for filtering dimensions. Use
          dimension_filter instead.
        order_bys: A list of Data API OrderBy
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1alpha/OrderBy)
          objects to apply to the dimensions and metrics.
        limit: The maximum number of rows the report task holds. If
          unspecified, 10,000 rows are returned. The API returns a maximum of
          250,000 rows per report task.
        offset: The row count of the report task's first row in Google
          Analytics storage. The first row is counted as row 0.
        currency_code: The currency code to use for currency values. Must be in
          ISO4217 format, such as "AED", "USD", "JPY". If the field is empty,
          the report uses the property's default currency.
        sampling_level: How much data the report reads: 'LOW', 'MEDIUM' or
          'UNSAMPLED'. Omit the argument to keep the API default for the
          property.
        timeout_seconds: How long to wait for the report task to finish
          building, from 1 to 300 seconds. Defaults to 120.

    Returns:
        Dict containing the report task's `report_metadata`, including its
        state and row counts, and its `rows`.

    Raises:
        ValueError: If an argument is invalid, including `sampling_level` and
          `timeout_seconds`.
        RuntimeError: If the report task fails while being built.
        TimeoutError: If the report task is still building after the timeout.
    """
    if not _MIN_TIMEOUT_SECONDS <= timeout_seconds <= _MAX_TIMEOUT_SECONDS:
        raise ValueError(
            "timeout_seconds must be between "
            f"{_MIN_TIMEOUT_SECONDS} and {_MAX_TIMEOUT_SECONDS} seconds"
        )

    report_definition = _build_report_definition(
        date_ranges=date_ranges,
        dimensions=dimensions,
        metrics=metrics,
        dimension_filter=dimension_filter,
        metric_filter=metric_filter,
        order_bys=order_bys,
        limit=limit,
        offset=offset,
        currency_code=currency_code,
        sampling_level=sampling_level,
    )
    request = data_v1alpha.CreateReportTaskRequest(
        parent=construct_property_rn(property_id),
        report_task=data_v1alpha.ReportTask(
            report_definition=report_definition
        ),
    )

    def _sync_call():
        client = create_data_api_alpha_client()
        # The create call returns a long-running operation whose result is the
        # newly created report task.
        report_task = client.create_report_task(request).result()
        report_task = _wait_for_report_task(
            client, report_task, timeout_seconds=timeout_seconds
        )
        response = client.query_report_task(name=report_task.name)
        return report_task, response

    report_task, response = await asyncio.to_thread(_sync_call)

    result = proto_to_dict(report_task)
    result["rows"] = proto_to_dict(response).get("rows", [])
    return result
