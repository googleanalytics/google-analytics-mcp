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

"""Tools for managing Google Analytics property configuration.

The create_* tools are write operations. They are only registered when the
user opts in with ANALYTICS_MCP_ENABLE_WRITES (see coordinator.py) and they
only preview the change unless called with confirm=True.
"""

import asyncio
import re
from typing import Any, Callable, Dict, List

from analytics_mcp.tools.utils import (
    construct_property_rn,
    proto_to_dict,
)
from analytics_mcp.tools.client import create_admin_api_client
from google.analytics import admin_v1beta
from google.api_core import exceptions as gexc

_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_DISPLAY_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_ ]*$")
_SCOPES = ("EVENT", "USER", "ITEM")
_COUNTING_METHODS = ("ONCE_PER_EVENT", "ONCE_PER_SESSION")


def _dry_run(
    method: str, parent: str, body: Dict[str, Any], problems: List[str]
) -> Dict[str, Any]:
    """Returns a preview of a write. Makes no API call."""
    return {
        "dry_run": True,
        "would_call": method,
        "parent": parent,
        "body": body,
        "validation_problems": problems,
        "next_step": (
            "Fix validation_problems before confirming."
            if problems
            else "No change was made. Call again with confirm=true to apply."
        ),
    }


async def _run_write(
    sync_call: Callable[[], Any], result_key: str
) -> Dict[str, Any]:
    """Runs a create call and maps the expected API failures to results.

    An LLM needs a distinct, non-error result for "already exists" so that
    re-running a setup is treated as success. Unexpected errors are raised and
    handled by the coordinator.
    """
    try:
        response = await asyncio.to_thread(sync_call)
    except gexc.AlreadyExists as e:
        return {"status": "already_exists", "message": e.message}
    except gexc.PermissionDenied as e:
        if "scope" in e.message.lower():
            hint = (
                "Credentials lack the analytics.edit scope. Set "
                "ANALYTICS_MCP_ENABLE_WRITES=true and re-run "
                "`gcloud auth application-default login` with the edit "
                "scope (see README)."
            )
        else:
            hint = "The user needs the Editor role on this property."
        return {
            "status": "permission_denied",
            "message": e.message,
            "hint": hint,
        }
    except (
        gexc.InvalidArgument,
        gexc.FailedPrecondition,
        gexc.ResourceExhausted,
    ) as e:
        return {
            "status": "rejected",
            "code": type(e).__name__,
            "message": e.message,
            "hint": (
                "Check naming rules and per-property limits "
                "(standard: 50 event-scoped dimensions, 30 key events)."
            ),
        }
    return {"status": "created", result_key: proto_to_dict(response)}


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
    confirm: bool = False,
) -> Dict[str, Any]:
    """Creates a custom dimension on a property.

    WRITE OPERATION. Without confirm=true this only returns a preview of what
    would be created; nothing is changed. Show the preview to the user and ask
    before calling again with confirm=true.

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
          parameter_name. At most 82 characters; letters, digits, spaces and
          underscores, starting with a letter.
        scope: EVENT (default), USER or ITEM. Immutable after creation.
        description: Optional description, at most 150 characters.
        disallow_ads_personalization: Only valid for USER scope.
        confirm: Must be exactly true to create the custom dimension.
          Otherwise a preview is returned and no API call is made.
    """
    parent = construct_property_rn(property_id)
    body = {
        "parameter_name": parameter_name,
        "display_name": display_name or parameter_name,
        "scope": scope,
    }
    if description:
        body["description"] = description
    if disallow_ads_personalization:
        body["disallow_ads_personalization"] = True

    problems = []
    max_len = 24 if scope == "USER" else 40
    if not _NAME_RE.match(parameter_name) or len(parameter_name) > max_len:
        problems.append(
            f"parameter_name must be letters, digits and underscores, "
            f"start with a letter and be at most {max_len} characters."
        )
    if (
        not _DISPLAY_NAME_RE.match(body["display_name"])
        or len(body["display_name"]) > 82
    ):
        problems.append(
            "display_name must be letters, digits, spaces and underscores, "
            "start with a letter and be at most 82 characters."
        )
    if scope not in _SCOPES:
        problems.append(f"scope must be one of {', '.join(_SCOPES)}.")
    if description and len(description) > 150:
        problems.append("description must be at most 150 characters.")
    if disallow_ads_personalization and scope != "USER":
        problems.append(
            "disallow_ads_personalization is only valid for USER scope."
        )

    # Checked before any client is created, so no credentials are loaded and
    # no network call happens on the preview path.
    if confirm is not True or problems:
        return _dry_run(
            "properties.customDimensions.create", parent, body, problems
        )

    request = admin_v1beta.CreateCustomDimensionRequest(
        parent=parent, custom_dimension=admin_v1beta.CustomDimension(body)
    )
    return await _run_write(
        lambda: create_admin_api_client().create_custom_dimension(
            request=request
        ),
        "custom_dimension",
    )


async def create_key_event(
    property_id: int | str,
    event_name: str,
    counting_method: str = "ONCE_PER_EVENT",
    default_value: float = None,
    default_currency_code: str = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Marks an event as a key event (formerly conversion) on a property.

    WRITE OPERATION. Without confirm=true this only returns a preview of what
    would be created; nothing is changed. Show the preview to the user and ask
    before calling again with confirm=true.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
        event_name: The event to mark as a key event, for example
          referral_click. Immutable after creation. The event does not need to
          have been collected yet.
        counting_method: ONCE_PER_EVENT (default) or ONCE_PER_SESSION.
        default_value: Optional value used when the event has no 'value'
          parameter. Must be given together with default_currency_code.
        default_currency_code: ISO 4217 currency code, for example EUR. Must be
          given together with default_value.
        confirm: Must be exactly true to create the key event. Otherwise a
          preview is returned and no API call is made.
    """
    parent = construct_property_rn(property_id)
    body = {"event_name": event_name, "counting_method": counting_method}
    if default_value is not None or default_currency_code:
        body["default_value"] = {
            "numeric_value": default_value,
            "currency_code": default_currency_code,
        }

    problems = []
    if not _NAME_RE.match(event_name) or len(event_name) > 40:
        problems.append(
            "event_name must be letters, digits and underscores, start with "
            "a letter and be at most 40 characters."
        )
    if counting_method not in _COUNTING_METHODS:
        problems.append(
            f"counting_method must be one of {', '.join(_COUNTING_METHODS)}."
        )
    if (default_value is None) != (not default_currency_code):
        problems.append(
            "default_value and default_currency_code must be given together."
        )

    if confirm is not True or problems:
        return _dry_run("properties.keyEvents.create", parent, body, problems)

    request = admin_v1beta.CreateKeyEventRequest(
        parent=parent, key_event=admin_v1beta.KeyEvent(body)
    )
    return await _run_write(
        lambda: create_admin_api_client().create_key_event(request=request),
        "key_event",
    )
