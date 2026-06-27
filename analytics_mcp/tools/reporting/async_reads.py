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

"""Additional asynchronous read-only reporting tools for GA4 MCP."""

import asyncio
from typing import Any, Dict, List

from analytics_mcp.tools.client import (
    create_data_api_alpha_client,
    create_data_api_client,
)
from analytics_mcp.tools.utils import (
    construct_audience_export_rn,
    construct_audience_list_rn,
    construct_property_rn,
    construct_recurring_audience_list_rn,
    construct_report_task_rn,
    proto_to_dict,
)
from google.analytics import data_v1alpha, data_v1beta


async def list_audience_exports(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns audience exports for a property."""
    request = data_v1beta.ListAudienceExportsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_data_api_client().list_audience_exports(request=request)
        return [proto_to_dict(audience_export) for audience_export in pager]

    return await asyncio.to_thread(_sync_call)


async def get_audience_export(
    property_id: int | str,
    audience_export_id: int | str,
) -> Dict[str, Any]:
    """Returns one audience export for a property."""
    request = data_v1beta.GetAudienceExportRequest(
        name=construct_audience_export_rn(property_id, audience_export_id)
    )

    def _sync_call():
        return create_data_api_client().get_audience_export(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def list_audience_lists(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns audience lists for a property."""
    request = data_v1alpha.ListAudienceListsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_data_api_alpha_client().list_audience_lists(
            request=request
        )
        return [proto_to_dict(audience_list) for audience_list in pager]

    return await asyncio.to_thread(_sync_call)


async def get_audience_list(
    property_id: int | str,
    audience_list_id: int | str,
) -> Dict[str, Any]:
    """Returns one audience list for a property."""
    request = data_v1alpha.GetAudienceListRequest(
        name=construct_audience_list_rn(property_id, audience_list_id)
    )

    def _sync_call():
        return create_data_api_alpha_client().get_audience_list(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def list_recurring_audience_lists(
    property_id: int | str,
) -> List[Dict[str, Any]]:
    """Returns recurring audience lists for a property."""
    request = data_v1alpha.ListRecurringAudienceListsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_data_api_alpha_client().list_recurring_audience_lists(
            request=request
        )
        return [
            proto_to_dict(recurring_audience_list)
            for recurring_audience_list in pager
        ]

    return await asyncio.to_thread(_sync_call)


async def get_recurring_audience_list(
    property_id: int | str,
    recurring_audience_list_id: int | str,
) -> Dict[str, Any]:
    """Returns one recurring audience list for a property."""
    request = data_v1alpha.GetRecurringAudienceListRequest(
        name=construct_recurring_audience_list_rn(
            property_id, recurring_audience_list_id
        )
    )

    def _sync_call():
        return create_data_api_alpha_client().get_recurring_audience_list(
            request=request
        )

    return proto_to_dict(await asyncio.to_thread(_sync_call))


async def list_report_tasks(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns report tasks for a property."""
    request = data_v1alpha.ListReportTasksRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_data_api_alpha_client().list_report_tasks(request=request)
        return [proto_to_dict(report_task) for report_task in pager]

    return await asyncio.to_thread(_sync_call)


async def get_report_task(
    property_id: int | str,
    report_task_id: int | str,
) -> Dict[str, Any]:
    """Returns one report task for a property."""
    request = data_v1alpha.GetReportTaskRequest(
        name=construct_report_task_rn(property_id, report_task_id)
    )

    def _sync_call():
        return create_data_api_alpha_client().get_report_task(request=request)

    return proto_to_dict(await asyncio.to_thread(_sync_call))
