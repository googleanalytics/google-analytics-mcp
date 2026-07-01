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

"""Tools for inspecting Data API quota usage."""

import asyncio
from typing import Any, Dict

from analytics_mcp.tools.utils import (
    construct_property_rn,
    proto_to_dict,
)
from analytics_mcp.tools.client import create_data_api_alpha_client
from google.analytics import data_v1alpha


async def get_property_quotas(property_id: int | str) -> Dict[str, Any]:
    """Returns the current Data API quota usage for a property.

    Shows consumed and remaining quota for core tokens (per day and per
    hour), realtime tokens, funnel tokens, concurrent requests, and
    server errors. Check this before running expensive report batches
    so you can back off instead of hitting quota errors.

    Note: this uses the alpha channel of the Data API, which may change
    without notice.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = data_v1alpha.GetPropertyQuotasSnapshotRequest(
        name=f"{construct_property_rn(property_id)}/propertyQuotasSnapshot"
    )

    def _sync_call():
        client = create_data_api_alpha_client()
        return client.get_property_quotas_snapshot(request=request)

    response = await asyncio.to_thread(_sync_call)

    return proto_to_dict(response)
