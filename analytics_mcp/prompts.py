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

"""MCP prompts for common Google Analytics use cases.

Each prompt is exposed as a slash command in Gemini CLI and as a prompt in
Claude Desktop and other MCP clients. Prompts guide the model to call the
right sequence of tools and present results in a useful way.
"""

from mcp import types as mcp_types

# ---------------------------------------------------------------------------
# Prompt definitions
# ---------------------------------------------------------------------------

PROMPTS: list[mcp_types.Prompt] = [
    mcp_types.Prompt(
        name="traffic-summary",
        description=(
            "Summarize overall website traffic for a property over a date "
            "range. Reports sessions, users, new users, bounce rate, and "
            "average engagement time."
        ),
        arguments=[
            mcp_types.PromptArgument(
                name="property_id",
                description="The GA4 property ID (numeric or 'properties/NNN').",
                required=True,
            ),
            mcp_types.PromptArgument(
                name="date_range",
                description=(
                    "Date range to analyze. Examples: 'last 30 days', "
                    "'last 7 days', '2024-01-01 to 2024-01-31'."
                ),
                required=False,
            ),
        ],
    ),
    mcp_types.Prompt(
        name="top-pages",
        description=(
            "Show the top pages by sessions for a property. Reports page "
            "path, page title, sessions, and average engagement time per "
            "page."
        ),
        arguments=[
            mcp_types.PromptArgument(
                name="property_id",
                description="The GA4 property ID (numeric or 'properties/NNN').",
                required=True,
            ),
            mcp_types.PromptArgument(
                name="date_range",
                description=(
                    "Date range to analyze. Examples: 'last 30 days', "
                    "'last 7 days'."
                ),
                required=False,
            ),
            mcp_types.PromptArgument(
                name="limit",
                description="Number of pages to return. Defaults to 10.",
                required=False,
            ),
        ],
    ),
    mcp_types.Prompt(
        name="acquisition-overview",
        description=(
            "Break down traffic by source and medium to understand where "
            "visitors are coming from. Reports sessions, users, and "
            "conversions by session source / medium."
        ),
        arguments=[
            mcp_types.PromptArgument(
                name="property_id",
                description="The GA4 property ID (numeric or 'properties/NNN').",
                required=True,
            ),
            mcp_types.PromptArgument(
                name="date_range",
                description=(
                    "Date range to analyze. Examples: 'last 30 days', "
                    "'last 7 days'."
                ),
                required=False,
            ),
        ],
    ),
    mcp_types.Prompt(
        name="compare-periods",
        description=(
            "Compare key metrics between two time periods side by side. "
            "Useful for week-over-week, month-over-month, or year-over-year "
            "analysis. Reports sessions, users, conversions, and engagement "
            "rate for both periods with percentage change."
        ),
        arguments=[
            mcp_types.PromptArgument(
                name="property_id",
                description="The GA4 property ID (numeric or 'properties/NNN').",
                required=True,
            ),
            mcp_types.PromptArgument(
                name="current_period",
                description=(
                    "The current period to analyze. Examples: 'last 7 days', "
                    "'last 30 days', '2024-02-01 to 2024-02-29'."
                ),
                required=True,
            ),
            mcp_types.PromptArgument(
                name="previous_period",
                description=(
                    "The previous period to compare against. Examples: "
                    "'8-14 days ago', 'previous month', "
                    "'2024-01-01 to 2024-01-31'."
                ),
                required=True,
            ),
        ],
    ),
    mcp_types.Prompt(
        name="campaign-performance",
        description=(
            "Analyze paid and organic campaign performance using UTM "
            "parameters. Reports sessions, conversions, and engagement by "
            "campaign name and source / medium. Useful for evaluating Google "
            "Ads, LinkedIn, email, and other tracked campaigns."
        ),
        arguments=[
            mcp_types.PromptArgument(
                name="property_id",
                description="The GA4 property ID (numeric or 'properties/NNN').",
                required=True,
            ),
            mcp_types.PromptArgument(
                name="date_range",
                description=(
                    "Date range to analyze. Examples: 'last 30 days', "
                    "'last 7 days'."
                ),
                required=False,
            ),
        ],
    ),
    mcp_types.Prompt(
        name="realtime-overview",
        description=(
            "Show what is happening on the site right now. Reports active "
            "users in the last 30 minutes broken down by page, country, and "
            "device category."
        ),
        arguments=[
            mcp_types.PromptArgument(
                name="property_id",
                description="The GA4 property ID (numeric or 'properties/NNN').",
                required=True,
            ),
        ],
    ),
]

_PROMPT_MAP: dict[str, mcp_types.Prompt] = {p.name: p for p in PROMPTS}

# ---------------------------------------------------------------------------
# Prompt text builders
# ---------------------------------------------------------------------------

_DEFAULT_DATE_RANGE = "last 30 days"


def _resolve_date_range(date_range: str | None) -> str:
    return date_range or _DEFAULT_DATE_RANGE


def _build_traffic_summary(args: dict) -> mcp_types.GetPromptResult:
    property_id = args.get("property_id", "")
    date_range = _resolve_date_range(args.get("date_range"))
    return mcp_types.GetPromptResult(
        description="Summarize overall website traffic.",
        messages=[
            mcp_types.PromptMessage(
                role="user",
                content=mcp_types.TextContent(
                    type="text",
                    text=(
                        f"Summarize the overall website traffic for GA4 "
                        f"property {property_id} for {date_range}.\n\n"
                        f"Use the run_report tool to fetch:\n"
                        f"- Dimensions: none (aggregate only)\n"
                        f"- Metrics: sessions, totalUsers, newUsers, "
                        f"bounceRate, averageSessionDuration, "
                        f"engagementRate\n\n"
                        f"Present the results as a concise summary with "
                        f"plain-language interpretation of each metric."
                    ),
                ),
            )
        ],
    )


def _build_top_pages(args: dict) -> mcp_types.GetPromptResult:
    property_id = args.get("property_id", "")
    date_range = _resolve_date_range(args.get("date_range"))
    limit = args.get("limit", "10")
    return mcp_types.GetPromptResult(
        description="Show the top pages by sessions.",
        messages=[
            mcp_types.PromptMessage(
                role="user",
                content=mcp_types.TextContent(
                    type="text",
                    text=(
                        f"Show the top {limit} pages by sessions for GA4 "
                        f"property {property_id} for {date_range}.\n\n"
                        f"Use the run_report tool with:\n"
                        f"- Dimensions: pagePath, pageTitle\n"
                        f"- Metrics: sessions, screenPageViews, "
                        f"averageSessionDuration, bounceRate\n"
                        f"- Order by sessions descending\n"
                        f"- Limit: {limit}\n\n"
                        f"Present the results as a table. Call out any pages "
                        f"with notably high bounce rates or low engagement "
                        f"time that may need attention."
                    ),
                ),
            )
        ],
    )


def _build_acquisition_overview(args: dict) -> mcp_types.GetPromptResult:
    property_id = args.get("property_id", "")
    date_range = _resolve_date_range(args.get("date_range"))
    return mcp_types.GetPromptResult(
        description="Break down traffic by source and medium.",
        messages=[
            mcp_types.PromptMessage(
                role="user",
                content=mcp_types.TextContent(
                    type="text",
                    text=(
                        f"Provide a traffic acquisition overview for GA4 "
                        f"property {property_id} for {date_range}.\n\n"
                        f"Use the run_report tool with:\n"
                        f"- Dimensions: sessionSourceMedium\n"
                        f"- Metrics: sessions, totalUsers, conversions, "
                        f"engagementRate\n"
                        f"- Order by sessions descending\n"
                        f"- Limit: 20\n\n"
                        f"Group results by channel (organic, paid, email, "
                        f"direct, referral, social). Highlight the top "
                        f"performing channels and flag any that have "
                        f"unexpectedly low conversion rates."
                    ),
                ),
            )
        ],
    )


def _build_compare_periods(args: dict) -> mcp_types.GetPromptResult:
    property_id = args.get("property_id", "")
    current_period = args.get("current_period", "last 7 days")
    previous_period = args.get("previous_period", "8-14 days ago")
    return mcp_types.GetPromptResult(
        description="Compare key metrics between two time periods.",
        messages=[
            mcp_types.PromptMessage(
                role="user",
                content=mcp_types.TextContent(
                    type="text",
                    text=(
                        f"Compare website performance for GA4 property "
                        f"{property_id} between two periods:\n"
                        f"- Current period: {current_period}\n"
                        f"- Previous period: {previous_period}\n\n"
                        f"Use the run_report tool with two date_ranges in a "
                        f"single request:\n"
                        f"- Dimensions: none (aggregate totals)\n"
                        f"- Metrics: sessions, totalUsers, newUsers, "
                        f"conversions, engagementRate, "
                        f"averageSessionDuration\n\n"
                        f"Present the results as a comparison table showing "
                        f"both period values and the percentage change. "
                        f"Highlight metrics with significant changes "
                        f"(>10%) and provide a brief narrative summary."
                    ),
                ),
            )
        ],
    )


def _build_campaign_performance(args: dict) -> mcp_types.GetPromptResult:
    property_id = args.get("property_id", "")
    date_range = _resolve_date_range(args.get("date_range"))
    return mcp_types.GetPromptResult(
        description="Analyze campaign performance by UTM parameters.",
        messages=[
            mcp_types.PromptMessage(
                role="user",
                content=mcp_types.TextContent(
                    type="text",
                    text=(
                        f"Analyze campaign performance for GA4 property "
                        f"{property_id} for {date_range}.\n\n"
                        f"Use the run_report tool with:\n"
                        f"- Dimensions: sessionCampaignName, "
                        f"sessionSourceMedium\n"
                        f"- Metrics: sessions, totalUsers, conversions, "
                        f"engagementRate, averageSessionDuration\n"
                        f"- Order by sessions descending\n"
                        f"- Limit: 25\n\n"
                        f"Filter out rows where sessionCampaignName is "
                        f"'(not set)' or '(direct)'. Present results as a "
                        f"table ranked by conversions. Call out the top 3 "
                        f"campaigns and any campaigns with a high session "
                        f"count but low conversions."
                    ),
                ),
            )
        ],
    )


def _build_realtime_overview(args: dict) -> mcp_types.GetPromptResult:
    property_id = args.get("property_id", "")
    return mcp_types.GetPromptResult(
        description="Show real-time active users by page, country, and device.",
        messages=[
            mcp_types.PromptMessage(
                role="user",
                content=mcp_types.TextContent(
                    type="text",
                    text=(
                        f"Show a real-time overview for GA4 property "
                        f"{property_id}.\n\n"
                        f"Make three run_realtime_report calls:\n\n"
                        f"1. Active users by page:\n"
                        f"   - Dimensions: unifiedPagePathScreen\n"
                        f"   - Metrics: activeUsers\n"
                        f"   - Limit: 10\n\n"
                        f"2. Active users by country:\n"
                        f"   - Dimensions: country\n"
                        f"   - Metrics: activeUsers\n"
                        f"   - Limit: 10\n\n"
                        f"3. Active users by device category:\n"
                        f"   - Dimensions: deviceCategory\n"
                        f"   - Metrics: activeUsers\n"
                        f"   - Limit: 5\n\n"
                        f"Present all three as a real-time dashboard summary "
                        f"with the total active user count prominently "
                        f"displayed at the top."
                    ),
                ),
            )
        ],
    )


_BUILDERS = {
    "traffic-summary": _build_traffic_summary,
    "top-pages": _build_top_pages,
    "acquisition-overview": _build_acquisition_overview,
    "compare-periods": _build_compare_periods,
    "campaign-performance": _build_campaign_performance,
    "realtime-overview": _build_realtime_overview,
}


# ---------------------------------------------------------------------------
# Public API called by coordinator
# ---------------------------------------------------------------------------


def list_prompts() -> list[mcp_types.Prompt]:
    """Returns all available MCP prompts."""
    return PROMPTS


def get_prompt(
    name: str, arguments: dict | None
) -> mcp_types.GetPromptResult:
    """Returns the prompt result for the given prompt name and arguments.

    Args:
        name: The name of the prompt.
        arguments: Optional dict of argument name → value provided by the user.

    Returns:
        A GetPromptResult containing the rendered prompt messages.

    Raises:
        ValueError: If the prompt name is not recognized.
    """
    if name not in _BUILDERS:
        raise ValueError(
            f"Unknown prompt: '{name}'. "
            f"Available prompts: {list(_BUILDERS.keys())}"
        )
    return _BUILDERS[name](arguments or {})
