from __future__ import annotations

import os

DSN_ENV_VAR = "MCP_USAGE_DSN"


def read_dsn() -> str:
    dsn = os.environ.get(DSN_ENV_VAR, "").strip()
    if not dsn:
        raise RuntimeError(
            f"{DSN_ENV_VAR} is unset or empty — usage logging cannot start. "
            f"Expected a Postgres DSN including sslmode=require."
        )
    return dsn
