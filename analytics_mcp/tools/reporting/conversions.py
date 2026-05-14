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

"""Tools for running conversions reports using the Data API."""

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
from analytics_mcp.tools.client import create_data_api_alpha_client
from google.analytics import data_v1alpha


def _run_conversions_report_description() -> str:
    """Returns the description for the `run_conversions_report` tool."""
    return f"""
          {run_conversions_report.__doc__}

          ## Hints for arguments

          Here are some hints that outline the expected format and requirements
          for arguments.

          ### Hints for `dimensions`

          The `dimensions` list must consist solely of the following allowed standard dimensions:
          - campaignName
          - continent
          - country
          - defaultChannelGroup
          - deviceCategory
          - medium
          - platform
          - primaryChannelGroup
          - source
          - sourceMedium
          - sourcePlatform
          - subcontinent

          ### Hints for `metrics`

          The `metrics` list must consist solely of the following allowed standard metrics:
          - advertiserAdClicks
          - advertiserAdCost
          - advertiserAdCostPerAllConversionsByConversionDate
          - advertiserAdCostPerAllConversionsByInteractionDate
          - advertiserAdCostPerClick
          - advertiserAdImpressions
          - allConversionsByConversionDate
          - allConversionsByInteractionDate
          - returnOnAdSpendByConversionDate
          - returnOnAdSpendByInteractionDate
          - totalRevenueByConversionDate
          - totalRevenueByInteractionDate

          ### Hints for `conversion_spec`

          The `conversion_spec` argument is required for conversions reporting.
          You can pass an empty list for `conversion_actions` if you want all conversion events.
          Example:
          {{
              "conversion_actions": ["conversionActions/12345"], # Or [] for all actions
              "attribution_model": "DATA_DRIVEN"  # Or "LAST_CLICK"
          }}

          ### Hints for `date_ranges`:
          {get_date_ranges_hints()}

          ### Hints for `dimension_filter`:
          {get_dimension_filter_hints()}

          ### Hints for `metric_filter`:
          {get_metric_filter_hints()}

          ### Hints for `order_bys`:
          {get_order_bys_hints()}

          """


async def run_conversions_report(
    property_id: int | str,
    date_ranges: List[Dict[str, Any]],
    dimensions: List[str],
    metrics: List[str],
    conversion_spec: Dict[str, Any],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    order_bys: List[Dict[str, Any]] = None,
    limit: int = None,
    offset: int = None,
    currency_code: str = None,
    return_property_quota: bool = False,
) -> Dict[str, Any]:
    """Runs a Google Analytics Data API conversions report.

    USE THIS TOOL INSTEAD OF `run_report` WHEN:
    - You need to report specifically on conversions, ad performance, return on ad spend (ROAS), or attribution.
    - You need to query specific conversion metrics (e.g., advertiserAdCost, returnOnAdSpendByInteractionDate, allConversionsByConversionDate, etc.).
    - You need to apply a specific attribution model (e.g., DATA_DRIVEN or LAST_CLICK) to your data.
    - The user's query explicitly asks about conversions, ad clicks, ad costs, or campaigns related to conversions.

    See the conversions report guide at
    https://developers.google.com/analytics/devguides/reporting/data/v1/conversions-api-basics
    for details and examples.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
        date_ranges: A list of date ranges
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1alpha/DateRange)
          to include in the report.
        dimensions: A list of dimensions to include in the report.
        metrics: A list of metrics to include in the report.
        conversion_spec: The specification for conversions reporting.
          Should include 'conversion_actions' (list of resource names) and
          'attribution_model'.
        dimension_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1alpha/FilterExpression)
          to apply to the dimensions.
        metric_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1alpha/FilterExpression)
          to apply to the metrics.
        order_bys: A list of Data API OrderBy
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1alpha/OrderBy)
          objects to apply to the dimensions and metrics.
        limit: The maximum number of rows to return in each response. Value must
          be a positive integer <= 250,000.
        offset: The row count of the start row. The first row is counted as row 0.
        currency_code: The currency code to use for currency values.
        return_property_quota: Whether to return property quota in the response.
    """
    request = data_v1alpha.RunReportRequest(
        property=construct_property_rn(property_id),
        dimensions=[
            data_v1alpha.Dimension(name=dimension) for dimension in dimensions
        ],
        metrics=[data_v1alpha.Metric(name=metric) for metric in metrics],
        date_ranges=[data_v1alpha.DateRange(dr) for dr in date_ranges],
        conversion_spec=data_v1alpha.ConversionSpec(conversion_spec),
        return_property_quota=return_property_quota,
    )

    if dimension_filter:
        request.dimension_filter = data_v1alpha.FilterExpression(
            dimension_filter
        )

    if metric_filter:
        request.metric_filter = data_v1alpha.FilterExpression(metric_filter)

    if order_bys:
        request.order_bys = [
            data_v1alpha.OrderBy(order_by) for order_by in order_bys
        ]

    if limit:
        request.limit = limit
    if offset:
        request.offset = offset
    if currency_code:
        request.currency_code = currency_code

    def _sync_call():
        return create_data_api_alpha_client().run_report(request)

    response = await asyncio.to_thread(_sync_call)

    return proto_to_dict(response)
