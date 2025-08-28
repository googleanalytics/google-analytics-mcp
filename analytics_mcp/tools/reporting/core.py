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

from typing import Any, Dict, List, Optional

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
    create_data_api_alpha_client,
    proto_to_dict,
)
from google.analytics import data_v1beta, data_v1alpha


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


def _run_funnel_report_description() -> str:
    """Returns the description for the `run_funnel_report` tool."""
    return f"""
          {run_funnel_report.__doc__}

          ## Hints for arguments

          Here are some hints that outline the expected format and requirements
          for arguments.

          ### Hints for `funnel_steps`

          The `funnel_steps` list must contain at least 2 steps. Each step can be configured in two ways:

          1. **Simple Event-Based Steps**: For basic event filtering
             ```json
             {{
                 "name": "Step Name",
                 "event": "event_name"
             }}
             ```

          2. **Advanced Filter Expression Steps**: For complex filtering with multiple conditions
             ```json
             {{
                 "name": "Step Name",
                 "filter_expression": {{
                     "funnel_field_filter": {{
                         "field_name": "eventName",
                         "string_filter": {{
                             "match_type": "EXACT",
                             "value": "page_view"
                         }}
                     }}
                 }}
             }}
             ```

          For page path filtering, use:
          ```json
          {{
              "name": "Home Page View",
              "filter_expression": {{
                  "and_group": {{
                      "expressions": [
                          {{
                              "funnel_field_filter": {{
                                  "field_name": "eventName",
                                  "string_filter": {{"match_type": "EXACT", "value": "page_view"}}
                              }}
                          }},
                          {{
                              "funnel_field_filter": {{
                                  "field_name": "pagePath",
                                  "string_filter": {{"match_type": "EXACT", "value": "/"}}
                              }}
                          }}
                      ]
                  }}
              }}
          }}
          ```

          ### Hints for `date_ranges`:
          {get_date_ranges_hints()}

          ### Hints for `funnel_breakdown`

          The `funnel_breakdown` parameter allows you to segment funnel results by a dimension:
          ```json
          {{
              "breakdown_dimension": "deviceCategory"
          }}
          ```

          Common breakdown dimensions include:
          - `deviceCategory` - Desktop, Mobile, Tablet
          - `country` - User's country
          - `operatingSystem` - User's operating system
          - `browser` - User's browser

          ### Hints for `funnel_next_action`

          The `funnel_next_action` parameter analyzes what users do after completing or dropping off from the funnel:
          ```json
          {{
              "next_action_dimension": "eventName",
              "limit": 5
          }}
          ```

          Common next action dimensions include:
          - `eventName` - Next events users trigger
          - `pagePath` - Next pages users visit
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

async def run_funnel_report(
    property_id: int | str,
    funnel_steps: List[Dict[str, Any]],
    date_ranges: List[Dict[str, str]] = None,
    funnel_breakdown: Dict[str, str] = None,
    funnel_next_action: Dict[str, str] = None,
    segments: List[Dict[str, Any]] = None,
    return_property_quota: bool = False,
) -> Dict[str, Any]:
    """Run a Google Analytics Data API funnel report.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
        funnel_steps: A list of funnel steps. Each step should be a dictionary
          containing:
          - 'name': (str) Display name for the step
          - 'filter_expression': (Dict) Complete filter expression for the step
          OR for simple event-based steps:
          - 'name': (str) Display name for the step  
          - 'event': (str) Event name to filter on
          Example:
          [
              {
                  "name": "Page View",
                  "filter_expression": {
                      "funnel_field_filter": {
                          "field_name": "eventName",
                          "string_filter": {
                              "match_type": "EXACT",
                              "value": "page_view"
                          }
                      }
                  }
              },
              {
                  "name": "Sign Up",
                  "event": "sign_up"
              }
          ]
        date_ranges: A list of date ranges
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/DateRange)
          to include in the report.
        funnel_breakdown: Optional breakdown dimension to segment the funnel.
          This creates separate funnel results for each value of the dimension.
          Example: {"breakdown_dimension": "deviceCategory"}
        funnel_next_action: Optional next action analysis configuration.
          This analyzes what users do after completing or dropping off from the funnel.
          Example: {"next_action_dimension": "eventName", "limit": 5}
        segments: Optional list of segments to apply to the funnel.
        return_property_quota: Whether to return current property quota information.
        
    Returns:
        Dict containing the funnel report response with funnel results including:
        - funnel_table: Table showing progression through funnel steps
        - funnel_visualization: Data for visualizing the funnel
        - property_quota: (if requested) Current quota usage information
        
    Raises:
        ValueError: If funnel_steps is empty or contains invalid configurations
        Exception: If the API request fails
        
    Example:
        # Simple event-based funnel
        result = await run_funnel_report(
            property_id="123456789",
            funnel_steps=[
                {"name": "Landing Page", "event": "page_view"},
                {"name": "Add to Cart", "event": "add_to_cart"},
                {"name": "Purchase", "event": "purchase"}
            ]
        )
        
        # Advanced funnel with page path filtering
        result = await run_funnel_report(
            property_id="123456789",
            funnel_steps=[
                {
                    "name": "Home Page View",
                    "filter_expression": {
                        "and_group": {
                            "expressions": [
                                {
                                    "funnel_field_filter": {
                                        "field_name": "eventName",
                                        "string_filter": {"match_type": "EXACT", "value": "page_view"}
                                    }
                                },
                                {
                                    "funnel_field_filter": {
                                        "field_name": "pagePath",
                                        "string_filter": {"match_type": "EXACT", "value": "/"}
                                    }
                                }
                            ]
                        }
                    }
                },
                {"name": "Purchase", "event": "purchase"}
            ],
            funnel_breakdown={"breakdown_dimension": "deviceCategory"},
            date_ranges=[{"start_date": "7daysAgo", "end_date": "today"}]
        )
    """
    # Validate inputs
    if not funnel_steps:
        raise ValueError("funnel_steps cannot be empty")
    
    if len(funnel_steps) < 2:
        raise ValueError("funnel_steps must contain at least 2 steps")
    
    # Set default date range if not provided
    if not date_ranges:
        date_ranges = [{"start_date": "30daysAgo", "end_date": "today"}]
    
    # Validate and create funnel steps
    steps = []
    for i, step in enumerate(funnel_steps):
        if not isinstance(step, dict):
            raise ValueError(f"Step {i+1} must be a dictionary")
        
        step_name = step.get('name', f'Step {i+1}')
        
        # Build filter expression
        if 'filter_expression' in step:
            # Use provided filter expression
            filter_expr = data_v1alpha.FunnelFilterExpression(step['filter_expression'])
        elif 'event' in step:
            # Simple event-based filter
            filter_expr = data_v1alpha.FunnelFilterExpression(
                funnel_event_filter=data_v1alpha.FunnelEventFilter(
                    event_name=step['event']
                )
            )
        else:
            raise ValueError(
                f"Step {i+1} must contain either 'filter_expression' or 'event' key"
            )
        
        funnel_step = data_v1alpha.FunnelStep(
            name=step_name,
            filter_expression=filter_expr
        )
        steps.append(funnel_step)
    
    # Create the funnel configuration
    funnel_config = data_v1alpha.Funnel(steps=steps)

    # Create date ranges
    date_range_objects = []
    for dr in date_ranges:
        if not isinstance(dr, dict) or 'start_date' not in dr or 'end_date' not in dr:
            raise ValueError(
                "Each date range must be a dictionary with 'start_date' and 'end_date' keys"
            )
        date_range_objects.append(
            data_v1alpha.DateRange(start_date=dr['start_date'], end_date=dr['end_date'])
        )

    # Create the request
    request = data_v1alpha.RunFunnelReportRequest(
        property=construct_property_rn(property_id),
        funnel=funnel_config,
        date_ranges=date_range_objects,
        return_property_quota=return_property_quota
    )
    
    # Add breakdown if specified (this goes on the request, not the funnel)
    if funnel_breakdown and 'breakdown_dimension' in funnel_breakdown:
        request.funnel_breakdown = data_v1alpha.FunnelBreakdown(
            breakdown_dimension=data_v1alpha.Dimension(
                name=funnel_breakdown['breakdown_dimension']
            )
        )
    
    # Add next action if specified (this also goes on the request, not the funnel)
    if funnel_next_action and 'next_action_dimension' in funnel_next_action:
        next_action_config = data_v1alpha.FunnelNextAction(
            next_action_dimension=data_v1alpha.Dimension(
                name=funnel_next_action['next_action_dimension']
            )
        )
        if 'limit' in funnel_next_action:
            next_action_config.limit = funnel_next_action['limit']
        request.funnel_next_action = next_action_config
    
    # Add segments if provided
    if segments:
        request.segments = [data_v1alpha.Segment(segment) for segment in segments]
    
    # Execute the request with enhanced error handling
    try:
        client = create_data_api_alpha_client()
        response = await client.run_funnel_report(request=request)
        return proto_to_dict(response)
    except Exception as e:
        error_msg = str(e)
        if "INVALID_ARGUMENT" in error_msg:
            raise ValueError(f"Invalid funnel configuration: {error_msg}")
        elif "PERMISSION_DENIED" in error_msg:
            raise PermissionError(f"Permission denied accessing property: {error_msg}")
        elif "NOT_FOUND" in error_msg:
            raise ValueError(f"Property not found: {error_msg}")
        elif "QUOTA_EXCEEDED" in error_msg:
            raise RuntimeError(f"API quota exceeded: {error_msg}")
        else:
            raise Exception(f"Failed to run funnel report: {error_msg}")


# The `run_report` tool requires a more complex description that's generated at
# runtime. Uses the `add_tool` method instead of an annnotation since `add_tool`
# provides the flexibility needed to generate the description while also
# including the `run_report` method's docstring.
mcp.add_tool(
    run_report,
    title="Run a Google Analytics Data API report using the Data API",
    description=_run_report_description(),
)

mcp.add_tool(
    run_funnel_report,
    title="Run a Google Analytics Data API funnel report using the Data API",
    description=_run_funnel_report_description(),
)
