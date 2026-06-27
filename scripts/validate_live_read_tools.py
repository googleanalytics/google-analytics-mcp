#!/usr/bin/env python

"""Live validation for the read-only Google Analytics MCP tool surface.

This script is intentionally scoped to read-only tools. It does not create,
update, delete, or mutate Google Analytics resources.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

from analytics_mcp.tools.admin.info import (
    get_account_summaries,
    get_property_details,
    list_google_ads_links,
    list_property_annotations,
)
from analytics_mcp.tools.admin.discovery import (
    get_account,
    get_conversion_event,
    get_custom_dimension,
    get_custom_metric,
    get_data_retention_settings,
    get_data_sharing_settings,
    get_data_stream,
    get_key_event,
    list_accounts,
    list_conversion_events,
    list_custom_dimensions,
    list_custom_metrics,
    list_data_streams,
    list_firebase_links,
    list_key_events,
    list_properties,
    run_access_report,
)
from analytics_mcp.tools.reporting.advanced import (
    check_report_compatibility,
    get_property_metadata,
    get_property_quotas_snapshot,
    run_pivot_report,
)
from analytics_mcp.tools.reporting.async_reads import (
    get_audience_export,
    get_audience_list,
    get_recurring_audience_list,
    get_report_task,
    list_audience_exports,
    list_audience_lists,
    list_recurring_audience_lists,
    list_report_tasks,
)
from analytics_mcp.tools.reporting.conversions import run_conversions_report
from analytics_mcp.tools.reporting.core import run_report
from analytics_mcp.tools.reporting.funnel import run_funnel_report
from analytics_mcp.tools.reporting.metadata import get_custom_dimensions_and_metrics
from analytics_mcp.tools.reporting.realtime import run_realtime_report
from google.api_core.exceptions import PermissionDenied


def _summary(name: str, payload: Any) -> dict[str, Any]:
    if name in {
        "get_account_summaries",
        "list_accounts",
        "list_google_ads_links",
        "list_properties",
        "list_data_streams",
        "list_property_annotations",
        "list_firebase_links",
        "list_key_events",
        "list_conversion_events",
        "list_custom_dimensions",
        "list_custom_metrics",
        "list_audience_exports",
        "list_audience_lists",
        "list_recurring_audience_lists",
        "list_report_tasks",
    }:
        return {"count": len(payload)}
    if name == "get_property_details":
        return {
            "name": payload.get("name"),
            "display_name": payload.get("display_name"),
            "currency_code": payload.get("currency_code"),
            "time_zone": payload.get("time_zone"),
        }
    if name == "get_custom_dimensions_and_metrics":
        return {
            "custom_dimensions": len(payload.get("custom_dimensions", [])),
            "custom_metrics": len(payload.get("custom_metrics", [])),
        }
    return {
        "keys": list(payload.keys())[:10],
        "row_count": payload.get("row_count"),
        "kind": type(payload).__name__,
    }


def _default_date_window() -> tuple[str, str]:
    """Returns a small recent window suitable for live validation."""
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)
    return start_date.isoformat(), end_date.isoformat()


async def validate(
    property_id: int | str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    raw_payloads: dict[str, Any] = {}

    async def capture(name: str, coro, *, allow_permission_denied: bool = False):
        try:
            value = await coro
            raw_payloads[name] = value
            results[name] = {"ok": True, "summary": _summary(name, value)}
        except PermissionDenied as exc:
            if allow_permission_denied:
                results[name] = {
                    "ok": True,
                    "access_status": "permission_denied",
                    "summary": {"error": str(exc)},
                }
            else:
                results[name] = {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
        except Exception as exc:  # pragma: no cover - integration behavior
            results[name] = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def mark_no_resource(name: str, source_list_name: str) -> None:
        results[name] = {
            "ok": True,
            "access_status": "no_resource",
            "summary": {
                "reason": f"{source_list_name} returned 0 rows",
            },
        }

    await capture("get_account_summaries", get_account_summaries())
    await capture("list_accounts", list_accounts())
    await capture("get_property_details", get_property_details(property_id))
    property_details = raw_payloads.get("get_property_details", {})
    property_parent = property_details.get("parent") or property_details.get(
        "account"
    )
    account_id = None
    if isinstance(property_parent, str) and property_parent.startswith(
        "accounts/"
    ):
        account_id = property_parent.split("/")[-1]
    await capture("list_google_ads_links", list_google_ads_links(property_id))
    await capture(
        "list_property_annotations", list_property_annotations(property_id)
    )
    await capture(
        "get_custom_dimensions_and_metrics",
        get_custom_dimensions_and_metrics(property_id),
    )
    if account_id is None:
        accounts = raw_payloads.get("list_accounts", [])
        if accounts:
            first_account_name = accounts[0].get("name")
            if isinstance(first_account_name, str) and first_account_name.startswith(
                "accounts/"
            ):
                account_id = first_account_name.split("/")[-1]
    if account_id is not None:
        await capture("list_properties", list_properties(account_id=account_id))
        await capture(
            "get_data_sharing_settings",
            get_data_sharing_settings(account_id),
        )
    else:
        results["list_properties"] = {
            "ok": False,
            "error": "Could not derive an accessible account ID for validation.",
        }
        results["get_data_sharing_settings"] = {
            "ok": False,
            "error": "Could not derive an accessible account ID for validation.",
        }
    await capture("list_data_streams", list_data_streams(property_id))
    await capture(
        "get_data_retention_settings",
        get_data_retention_settings(property_id),
    )
    await capture("list_firebase_links", list_firebase_links(property_id))
    await capture("list_key_events", list_key_events(property_id))
    await capture("list_conversion_events", list_conversion_events(property_id))
    await capture("list_custom_dimensions", list_custom_dimensions(property_id))
    await capture("list_custom_metrics", list_custom_metrics(property_id))
    await capture("get_property_metadata", get_property_metadata(property_id))
    accounts = raw_payloads.get("list_accounts", [])
    if accounts:
        await capture("get_account", get_account(accounts[0]["name"]))
    else:
        mark_no_resource("get_account", "list_accounts")
    data_streams = raw_payloads.get("list_data_streams", [])
    if data_streams:
        await capture(
            "get_data_stream",
            get_data_stream(property_id, data_streams[0]["name"]),
        )
    else:
        mark_no_resource("get_data_stream", "list_data_streams")
    key_events = raw_payloads.get("list_key_events", [])
    if key_events:
        await capture(
            "get_key_event",
            get_key_event(property_id, key_events[0]["name"]),
        )
    else:
        mark_no_resource("get_key_event", "list_key_events")
    conversion_events = raw_payloads.get("list_conversion_events", [])
    if conversion_events:
        await capture(
            "get_conversion_event",
            get_conversion_event(property_id, conversion_events[0]["name"]),
        )
    else:
        mark_no_resource("get_conversion_event", "list_conversion_events")
    custom_dimensions = raw_payloads.get("list_custom_dimensions", [])
    if custom_dimensions:
        await capture(
            "get_custom_dimension",
            get_custom_dimension(property_id, custom_dimensions[0]["name"]),
        )
    else:
        mark_no_resource("get_custom_dimension", "list_custom_dimensions")
    custom_metrics = raw_payloads.get("list_custom_metrics", [])
    if custom_metrics:
        await capture(
            "get_custom_metric",
            get_custom_metric(property_id, custom_metrics[0]["name"]),
        )
    else:
        mark_no_resource("get_custom_metric", "list_custom_metrics")
    await capture(
        "run_report",
        run_report(
            property_id=property_id,
            date_ranges=[{"start_date": start_date, "end_date": end_date}],
            dimensions=["date", "sessionDefaultChannelGroup"],
            metrics=["sessions", "totalUsers"],
            limit=20,
            return_property_quota=True,
        ),
    )
    await capture(
        "run_pivot_report",
        run_pivot_report(
            property_id=property_id,
            date_ranges=[{"start_date": start_date, "end_date": end_date}],
            dimensions=["sessionDefaultChannelGroup"],
            metrics=["sessions"],
            pivots=[
                {
                    "field_names": ["sessionDefaultChannelGroup"],
                    "limit": 5,
                }
            ],
            return_property_quota=True,
        ),
    )
    await capture(
        "check_report_compatibility",
        check_report_compatibility(
            property_id=property_id,
            dimensions=["sessionDefaultChannelGroup"],
            metrics=["sessions"],
        ),
    )
    await capture(
        "run_realtime_report",
        run_realtime_report(
            property_id=property_id,
            dimensions=["deviceCategory"],
            metrics=["activeUsers"],
            limit=10,
            return_property_quota=True,
        ),
    )
    await capture(
        "run_funnel_report",
        run_funnel_report(
            property_id=property_id,
            funnel_steps=[
                {"name": "Page view", "event": "page_view"},
                {"name": "Add to cart", "event": "add_to_cart"},
                {"name": "Purchase", "event": "purchase"},
            ],
            date_ranges=[{"start_date": start_date, "end_date": end_date}],
            return_property_quota=True,
        ),
    )
    await capture(
        "run_access_report",
        run_access_report(
            property_id=property_id,
            dimensions=[{"dimension_name": "country"}],
            metrics=[{"metric_name": "accessCount"}],
            date_ranges=[{"start_date": start_date, "end_date": end_date}],
            limit=5,
        ),
        allow_permission_denied=True,
    )
    await capture(
        "get_property_quotas_snapshot",
        get_property_quotas_snapshot(property_id),
    )
    await capture(
        "run_conversions_report",
        run_conversions_report(
            property_id=property_id,
            date_ranges=[{"start_date": start_date, "end_date": end_date}],
            dimensions=["sourceMedium"],
            metrics=[
                "allConversionsByConversionDate",
                "totalRevenueByConversionDate",
            ],
            conversion_spec={
                "conversion_actions": [],
                "attribution_model": "LAST_CLICK",
            },
            limit=10,
            return_property_quota=True,
        ),
    )
    await capture("list_audience_exports", list_audience_exports(property_id))
    audience_exports = raw_payloads.get("list_audience_exports", [])
    if audience_exports:
        await capture(
            "get_audience_export",
            get_audience_export(property_id, audience_exports[0]["name"]),
        )
    else:
        mark_no_resource("get_audience_export", "list_audience_exports")
    await capture("list_audience_lists", list_audience_lists(property_id))
    audience_lists = raw_payloads.get("list_audience_lists", [])
    if audience_lists:
        await capture(
            "get_audience_list",
            get_audience_list(property_id, audience_lists[0]["name"]),
        )
    else:
        mark_no_resource("get_audience_list", "list_audience_lists")
    await capture(
        "list_recurring_audience_lists",
        list_recurring_audience_lists(property_id),
    )
    recurring_audience_lists = raw_payloads.get(
        "list_recurring_audience_lists", []
    )
    if recurring_audience_lists:
        await capture(
            "get_recurring_audience_list",
            get_recurring_audience_list(
                property_id, recurring_audience_lists[0]["name"]
            ),
        )
    else:
        mark_no_resource(
            "get_recurring_audience_list",
            "list_recurring_audience_lists",
        )
    await capture("list_report_tasks", list_report_tasks(property_id))
    report_tasks = raw_payloads.get("list_report_tasks", [])
    if report_tasks:
        await capture(
            "get_report_task",
            get_report_task(property_id, report_tasks[0]["name"]),
        )
    else:
        mark_no_resource("get_report_task", "list_report_tasks")

    return results


def main() -> None:
    default_start_date, default_end_date = _default_date_window()
    parser = argparse.ArgumentParser()
    parser.add_argument("--property-id", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--start-date", default=default_start_date)
    parser.add_argument("--end-date", default=default_end_date)
    args = parser.parse_args()

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results = asyncio.run(
        validate(
            property_id=args.property_id,
            start_date=args.start_date,
            end_date=args.end_date,
        )
    )
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
