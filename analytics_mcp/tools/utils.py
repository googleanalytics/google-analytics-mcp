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

"""Common utilities used by the MCP server."""

from typing import Any, Dict

import proto


def _construct_numeric_resource_name(
    value: int | str,
    prefix: str,
    description: str,
) -> str:
    """Returns a normalized resource name for numeric GA resources."""
    resource_num = None
    if isinstance(value, int):
        resource_num = value
    elif isinstance(value, str):
        value = value.strip()
        if value.isdigit():
            resource_num = int(value)
        elif value.startswith(f"{prefix}/"):
            numeric_part = value.split("/")[-1]
            if numeric_part.isdigit():
                resource_num = int(numeric_part)
    if resource_num is None:
        raise ValueError(
            (
                f"Invalid {description}: {value}. "
                f"A valid value is either a number or a string starting with "
                f"'{prefix}/' and followed by a number."
            )
        )
    return f"{prefix}/{resource_num}"


def construct_property_rn(property_value: int | str) -> str:
    """Returns a property resource name in the format required by APIs."""
    return _construct_numeric_resource_name(
        property_value, "properties", "property ID"
    )


def construct_account_rn(account_value: int | str) -> str:
    """Returns an account resource name in the format required by APIs."""
    return _construct_numeric_resource_name(
        account_value, "accounts", "account ID"
    )


def construct_data_stream_rn(
    property_value: int | str, data_stream_value: int | str
) -> str:
    """Returns a data stream resource name."""
    property_rn = construct_property_rn(property_value)
    if isinstance(data_stream_value, int):
        return f"{property_rn}/dataStreams/{data_stream_value}"
    if isinstance(data_stream_value, str):
        data_stream_value = data_stream_value.strip()
        if data_stream_value.startswith(f"{property_rn}/dataStreams/"):
            return data_stream_value
        if data_stream_value.startswith("properties/") and "/dataStreams/" in data_stream_value:
            return data_stream_value
        if data_stream_value.isdigit():
            return f"{property_rn}/dataStreams/{data_stream_value}"
    raise ValueError(
        (
            f"Invalid data stream ID: {data_stream_value}. "
            "A valid value is either a number or a full data stream resource name."
        )
    )


def construct_property_child_rn(
    property_value: int | str,
    collection: str,
    child_value: int | str,
    description: str,
    *,
    allow_non_numeric: bool = False,
) -> str:
    """Returns a resource name for one property-scoped child resource."""
    property_rn = construct_property_rn(property_value)
    collection_prefix = f"{property_rn}/{collection}/"
    if isinstance(child_value, int):
        return f"{collection_prefix}{child_value}"
    if isinstance(child_value, str):
        child_value = child_value.strip()
        if child_value.startswith(collection_prefix):
            return child_value
        if child_value.startswith("properties/") and f"/{collection}/" in child_value:
            return child_value
        if child_value.isdigit() or (allow_non_numeric and child_value):
            return f"{collection_prefix}{child_value}"
    raise ValueError(
        (
            f"Invalid {description}: {child_value}. "
            "A valid value is either a resource ID or a full resource name."
        )
    )


def construct_key_event_rn(
    property_value: int | str, key_event_value: int | str
) -> str:
    """Returns a key event resource name."""
    property_rn = construct_property_rn(property_value)
    if isinstance(key_event_value, int):
        return f"{property_rn}/keyEvents/{key_event_value}"
    if isinstance(key_event_value, str):
        key_event_value = key_event_value.strip()
        if key_event_value.startswith(f"{property_rn}/keyEvents/"):
            return key_event_value
        if key_event_value.startswith("properties/") and "/keyEvents/" in key_event_value:
            return key_event_value
        if key_event_value:
            return f"{property_rn}/keyEvents/{key_event_value}"
    raise ValueError(
        (
            f"Invalid key event ID: {key_event_value}. "
            "A valid value is a non-empty ID or a full key event resource name."
        )
    )


def construct_conversion_event_rn(
    property_value: int | str, conversion_event_value: int | str
) -> str:
    """Returns a conversion event resource name."""
    return construct_property_child_rn(
        property_value,
        "conversionEvents",
        conversion_event_value,
        "conversion event ID",
    )


def construct_custom_dimension_rn(
    property_value: int | str, custom_dimension_value: int | str
) -> str:
    """Returns a custom dimension resource name."""
    return construct_property_child_rn(
        property_value,
        "customDimensions",
        custom_dimension_value,
        "custom dimension ID",
    )


def construct_custom_metric_rn(
    property_value: int | str, custom_metric_value: int | str
) -> str:
    """Returns a custom metric resource name."""
    return construct_property_child_rn(
        property_value,
        "customMetrics",
        custom_metric_value,
        "custom metric ID",
    )


def construct_audience_export_rn(
    property_value: int | str, audience_export_value: int | str
) -> str:
    """Returns an audience export resource name."""
    return construct_property_child_rn(
        property_value,
        "audienceExports",
        audience_export_value,
        "audience export ID",
        allow_non_numeric=True,
    )


def construct_audience_list_rn(
    property_value: int | str, audience_list_value: int | str
) -> str:
    """Returns an audience list resource name."""
    return construct_property_child_rn(
        property_value,
        "audienceLists",
        audience_list_value,
        "audience list ID",
        allow_non_numeric=True,
    )


def construct_recurring_audience_list_rn(
    property_value: int | str, recurring_audience_list_value: int | str
) -> str:
    """Returns a recurring audience list resource name."""
    return construct_property_child_rn(
        property_value,
        "recurringAudienceLists",
        recurring_audience_list_value,
        "recurring audience list ID",
        allow_non_numeric=True,
    )


def construct_report_task_rn(
    property_value: int | str, report_task_value: int | str
) -> str:
    """Returns a report task resource name."""
    return construct_property_child_rn(
        property_value,
        "reportTasks",
        report_task_value,
        "report task ID",
        allow_non_numeric=True,
    )


def construct_data_retention_settings_rn(property_value: int | str) -> str:
    """Returns a data retention settings resource name."""
    return f"{construct_property_rn(property_value)}/dataRetentionSettings"


def construct_data_sharing_settings_rn(account_value: int | str) -> str:
    """Returns a data sharing settings resource name."""
    return f"{construct_account_rn(account_value)}/dataSharingSettings"


def construct_property_quotas_snapshot_rn(property_value: int | str) -> str:
    """Returns a property quota snapshot resource name."""
    return f"{construct_property_rn(property_value)}/propertyQuotasSnapshot"


def proto_to_dict(obj: proto.Message) -> Dict[str, Any]:
    """Converts a proto message to a dictionary."""
    return type(obj).to_dict(
        obj, use_integers_for_enums=False, preserving_proto_field_name=True
    )


def proto_to_json(obj: proto.Message) -> str:
    """Converts a proto message to a JSON string."""
    return type(obj).to_json(obj, indent=None, preserving_proto_field_name=True)
