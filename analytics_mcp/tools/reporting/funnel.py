from typing import Any, Dict, List

from analytics_mcp.coordinator import mcp
from analytics_mcp.tools.reporting.metadata import (
    get_date_ranges_hints,
    get_funnel_steps_hints,
)
from analytics_mcp.tools.utils import (
    construct_property_rn,
    create_data_api_alpha_client,
    proto_to_dict,
)
from google.analytics import data_v1alpha


def _run_funnel_report_description() -> str:
    """Returns the description for the `run_funnel_report` tool."""
    return f"""
        {run_funnel_report.__doc__}

        ## Hints for arguments

        Here are some hints that outline the expected format and requirements
        for arguments.
          
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
    
        ### Hints for `date_ranges`:
        {get_date_ranges_hints()}
        
        ### Hints for `funnel_steps`
        {get_funnel_steps_hints()}
          
        """


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

    See the funnel report guide at
    https://developers.google.com/analytics/devguides/reporting/data/v1/funnels
    for details and examples.

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


    """

    steps = []
    for i, step in enumerate(funnel_steps):
        if not isinstance(step, dict):
            raise ValueError(f"Step {i+1} must be a dictionary")

        step_name = step.get("name", f"Step {i+1}")

        if "filter_expression" in step:
            filter_expr = data_v1alpha.FunnelFilterExpression(
                step["filter_expression"]
            )
        elif "event" in step:
            filter_expr = data_v1alpha.FunnelFilterExpression(
                funnel_event_filter=data_v1alpha.FunnelEventFilter(
                    event_name=step["event"]
                )
            )
        else:
            raise ValueError(
                f"Step {i+1} must contain either 'filter_expression' or 'event' key"
            )

        funnel_step = data_v1alpha.FunnelStep(
            name=step_name, filter_expression=filter_expr
        )
        steps.append(funnel_step)

    request = data_v1alpha.RunFunnelReportRequest(
        property=construct_property_rn(property_id),
        funnel=data_v1alpha.Funnel(steps=steps),
        date_ranges=[data_v1alpha.DateRange(dr) for dr in date_ranges],
        return_property_quota=return_property_quota,
    )

    if funnel_breakdown and "breakdown_dimension" in funnel_breakdown:
        request.funnel_breakdown = data_v1alpha.FunnelBreakdown(
            breakdown_dimension=data_v1alpha.Dimension(
                name=funnel_breakdown["breakdown_dimension"]
            )
        )

    if funnel_next_action and "next_action_dimension" in funnel_next_action:
        next_action_config = data_v1alpha.FunnelNextAction(
            next_action_dimension=data_v1alpha.Dimension(
                name=funnel_next_action["next_action_dimension"]
            )
        )
        if "limit" in funnel_next_action:
            next_action_config.limit = funnel_next_action["limit"]
        request.funnel_next_action = next_action_config

    if segments:
        request.segments = [
            data_v1alpha.Segment(segment) for segment in segments
        ]

    response = await create_data_api_alpha_client().run_funnel_report(request)
    return proto_to_dict(response)


mcp.add_tool(
    run_funnel_report,
    title="Run a Google Analytics Data API funnel report using the Data API",
    description=_run_funnel_report_description(),
)
