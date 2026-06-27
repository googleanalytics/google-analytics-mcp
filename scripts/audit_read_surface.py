#!/usr/bin/env python

"""Audits SDK read methods against the exposed MCP tool surface."""

from __future__ import annotations

import json
from pathlib import Path

import analytics_mcp.coordinator as coordinator
from google.analytics import admin_v1beta, data_v1alpha, data_v1beta


READ_PREFIXES = ("get_", "list_", "run_", "check_")
IGNORED_TRANSPORT_METHODS = {
    "get_mtls_endpoint_and_cert_source",
    "get_transport_class",
}
INTENTIONALLY_OMITTED = {
    "get_measurement_protocol_secret": "secret_material",
    "list_measurement_protocol_secrets": "secret_material",
    "get_property": "covered_by_get_property_details",
    "get_metadata": "covered_by_get_property_metadata",
}
SDK_TO_MCP_NAME_ALIASES = {
    "list_account_summaries": "get_account_summaries",
    "check_compatibility": "check_report_compatibility",
}


def _sdk_read_methods() -> dict[str, list[str]]:
    classes = {
        "admin_v1beta.AnalyticsAdminServiceClient": (
            admin_v1beta.AnalyticsAdminServiceClient
        ),
        "data_v1beta.BetaAnalyticsDataClient": data_v1beta.BetaAnalyticsDataClient,
        "data_v1alpha.AlphaAnalyticsDataClient": (
            data_v1alpha.AlphaAnalyticsDataClient
        ),
    }
    inventory: dict[str, list[str]] = {}
    for label, cls in classes.items():
        methods = []
        for name in sorted(dir(cls)):
            if name.startswith(READ_PREFIXES) and name not in IGNORED_TRANSPORT_METHODS:
                attr = getattr(cls, name)
                if callable(attr):
                    methods.append(name)
        inventory[label] = methods
    return inventory


def build_audit() -> dict:
    sdk_inventory = _sdk_read_methods()
    sdk_method_set = {
        method for methods in sdk_inventory.values() for method in methods
    }
    exposed_tools = sorted(tool.name for tool in coordinator.mcp_tools)
    exposed_tool_set = set(exposed_tools)
    covered_sdk_methods = {
        method
        for method in sdk_method_set
        if method in exposed_tool_set
        or SDK_TO_MCP_NAME_ALIASES.get(method) in exposed_tool_set
    }

    missing_from_mcp = sorted(
        method
        for method in sdk_method_set
        if method not in covered_sdk_methods
        and method not in INTENTIONALLY_OMITTED
    )
    intentionally_omitted = {
        method: INTENTIONALLY_OMITTED[method]
        for method in sorted(INTENTIONALLY_OMITTED)
        if method in sdk_method_set
    }

    return {
        "sdk_read_methods_by_client": sdk_inventory,
        "exposed_mcp_tools": exposed_tools,
        "intentionally_omitted": intentionally_omitted,
        "sdk_to_mcp_name_aliases": SDK_TO_MCP_NAME_ALIASES,
        "missing_from_mcp": missing_from_mcp,
        "summary": {
            "sdk_read_method_count": len(sdk_method_set),
            "exposed_tool_count": len(exposed_tools),
            "intentionally_omitted_count": len(intentionally_omitted),
            "unexplained_missing_count": len(missing_from_mcp),
        },
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_audit()
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
