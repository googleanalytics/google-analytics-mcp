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

"""Tools for managing Google Analytics property configuration.

The create_* tools are write operations. They are only registered when the
user opts in with the --allow-write flag (see coordinator.py).
"""

import asyncio
import re
from typing import Any, Dict, List

from analytics_mcp.tools.utils import (
    construct_property_rn,
    proto_to_dict,
)
from analytics_mcp.tools.client import create_admin_api_client
from google.analytics import admin_v1beta

_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_VALID_SCOPES = ("EVENT", "USER", "ITEM")
_VALID_COUNTING_METHODS = ("ONCE_PER_EVENT", "ONCE_PER_SESSION")
_MAX_PARAMETER_NAME_LENGTH = 40
_MAX_USER_PARAMETER_NAME_LENGTH = 24
_MAX_EVENT_NAME_LENGTH = 40
_MAX_DISPLAY_NAME_LENGTH = 82
_MAX_DESCRIPTION_LENGTH = 150


async def list_key_events(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns the key events (formerly conversions) defined on a property.

    Each key event has its event name, counting method, default value, and
    whether it is custom and deletable. Use this for key event definitions;
    use run_conversions_report for key event numbers.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.ListKeyEventsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        key_events_pager = create_admin_api_client().list_key_events(
            request=request
        )
        return [proto_to_dict(key_event) for key_event in key_events_pager]

    return await asyncio.to_thread(_sync_call)


async def create_custom_dimension(
    property_id: int | str,
    parameter_name: str,
    display_name: str = None,
    scope: str = "EVENT",
    description: str = None,
    disallow_ads_personalization: bool = False,
) -> Dict[str, Any]:
    """Creates a custom dimension on a property.

    Requires the Editor role on the property.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
        parameter_name: The event parameter name (EVENT scope), user property
          name (USER scope) or items-array parameter name (ITEM scope). Letters,
          digits and underscores, starting with a letter; at most 40
          characters (24 for USER scope). Immutable after creation. Example:
          plan_tier.
        display_name: The name shown in the Google Analytics UI. Defaults to
          parameter_name. At most 82 characters.
        scope: Valid values are 'EVENT', 'USER' and 'ITEM'. Defaults to
          'EVENT'. Immutable after creation.
        description: Optional description (maximum 150 characters).
        disallow_ads_personalization: Only valid for USER scope.
    """
    normalized_scope = (scope or "").strip().upper()
    if normalized_scope not in _VALID_SCOPES:
        valid_str = ", ".join(_VALID_SCOPES)
        raise ValueError(
            f"Invalid scope '{scope}'. Valid scopes are: {valid_str}."
        )

    max_len = (
        _MAX_USER_PARAMETER_NAME_LENGTH
        if normalized_scope == "USER"
        else _MAX_PARAMETER_NAME_LENGTH
    )
    if not _NAME_RE.match(parameter_name) or len(parameter_name) > max_len:
        raise ValueError(
            "parameter_name must be letters, digits and underscores, start "
            f"with a letter and be at most {max_len} characters."
        )

    if display_name is None:
        display_name = parameter_name
    elif not display_name.strip():
        raise ValueError("display_name must be a non-empty string.")
    if len(display_name) > _MAX_DISPLAY_NAME_LENGTH:
        raise ValueError(
            f"display_name must be at most {_MAX_DISPLAY_NAME_LENGTH} "
            f"characters (got {len(display_name)})."
        )

    if description is not None and len(description) > _MAX_DESCRIPTION_LENGTH:
        raise ValueError(
            f"description must be at most {_MAX_DESCRIPTION_LENGTH} "
            f"characters (got {len(description)})."
        )

    if disallow_ads_personalization and normalized_scope != "USER":
        raise ValueError(
            "disallow_ads_personalization is only valid for USER scope."
        )

    custom_dimension = admin_v1beta.CustomDimension(
        parameter_name=parameter_name,
        display_name=display_name,
        scope=getattr(
            admin_v1beta.CustomDimension.DimensionScope, normalized_scope
        ),
        disallow_ads_personalization=disallow_ads_personalization,
    )
    if description is not None:
        custom_dimension.description = description

    request = admin_v1beta.CreateCustomDimensionRequest(
        parent=construct_property_rn(property_id),
        custom_dimension=custom_dimension,
    )

    def _sync_call():
        return create_admin_api_client().create_custom_dimension(
            request=request
        )

    response = await asyncio.to_thread(_sync_call)
    return proto_to_dict(response)


async def create_key_event(
    property_id: int | str,
    event_name: str,
    counting_method: str = "ONCE_PER_EVENT",
    default_value: float = None,
    default_currency_code: str = None,
) -> Dict[str, Any]:
    """Marks an event as a key event (formerly conversion) on a property.

    Requires the Marketer or Editor role on the property.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
        event_name: The event to mark as a key event, for example
          referral_click. Immutable after creation. The event does not need to
          have been collected yet.
        counting_method: Valid values are 'ONCE_PER_EVENT' and
          'ONCE_PER_SESSION'. Defaults to 'ONCE_PER_EVENT'.
        default_value: Optional value used when the event has no 'value'
          parameter. Must be given together with default_currency_code.
        default_currency_code: ISO 4217 currency code, for example EUR. Must be
          given together with default_value.
    """
    if (
        not _NAME_RE.match(event_name)
        or len(event_name) > _MAX_EVENT_NAME_LENGTH
    ):
        raise ValueError(
            "event_name must be letters, digits and underscores, start with "
            f"a letter and be at most {_MAX_EVENT_NAME_LENGTH} characters."
        )

    normalized_method = (counting_method or "").strip().upper()
    if normalized_method not in _VALID_COUNTING_METHODS:
        valid_str = ", ".join(_VALID_COUNTING_METHODS)
        raise ValueError(
            f"Invalid counting_method '{counting_method}'. Valid counting "
            f"methods are: {valid_str}."
        )

    if (default_value is None) != (not default_currency_code):
        raise ValueError(
            "default_value and default_currency_code must be given together."
        )

    key_event = admin_v1beta.KeyEvent(
        event_name=event_name,
        counting_method=getattr(
            admin_v1beta.KeyEvent.CountingMethod, normalized_method
        ),
    )
    if default_value is not None:
        key_event.default_value = admin_v1beta.KeyEvent.DefaultValue(
            numeric_value=default_value, currency_code=default_currency_code
        )

    request = admin_v1beta.CreateKeyEventRequest(
        parent=construct_property_rn(property_id), key_event=key_event
    )

    def _sync_call():
        return create_admin_api_client().create_key_event(request=request)

    response = await asyncio.to_thread(_sync_call)
    return proto_to_dict(response)
