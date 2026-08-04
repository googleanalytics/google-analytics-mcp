from __future__ import annotations

from typing import Any

ACCOUNT_ID_KEYS = ("customer_id", "merchant_id", "property_id")


def read_account_id(arguments: dict[str, Any] | None) -> str | None:
    for key in ACCOUNT_ID_KEYS:
        value = (arguments or {}).get(key)
        if value is not None:
            return str(value)
    return None
