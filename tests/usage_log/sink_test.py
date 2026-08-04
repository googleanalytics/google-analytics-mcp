"""Covers runbook test 4 against a real Postgres (phase-2-middleware.md 2.11).
Skipped without MCP_USAGE_TEST_DSN, because the database is a backing service
the developer provides, not something this repo runs."""

import os
import uuid
from datetime import datetime, timezone

import psycopg
import pytest

from analytics_mcp.usage_log.sink import PostgresSink, ToolCall

TEST_DSN = os.environ.get("MCP_USAGE_TEST_DSN", "")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="MCP_USAGE_TEST_DSN is not set")


def _call(server: str, **overrides) -> ToolCall:
    fields = {
        "occurred_at": datetime.now(timezone.utc),
        "server": server,
        "tool": "list_products",
        "user_sub": "1234567890",
        "user_email": "piotr@touchpoint.agency",
        "account_id": "42",
        "status": "ok",
        **overrides,
    }
    return ToolCall(**fields)


@pytest.fixture
def marker() -> str:
    return f"test-{uuid.uuid4()}"


@pytest.fixture
def cleanup(marker):
    yield
    with psycopg.connect(TEST_DSN) as conn:
        conn.execute("DELETE FROM tool_call WHERE server = %s", (marker,))


async def test_writes_every_field(marker, cleanup):
    sink = PostgresSink(TEST_DSN)
    call = _call(marker)
    await sink.write(call)
    await sink.close()

    with psycopg.connect(TEST_DSN) as conn:
        row = conn.execute(
            "SELECT occurred_at, server, tool, user_sub, user_email, account_id, status"
            " FROM tool_call WHERE server = %s",
            (marker,),
        ).fetchone()

    assert row == (
        call.occurred_at,
        marker,
        "list_products",
        "1234567890",
        "piotr@touchpoint.agency",
        "42",
        "ok",
    )


async def test_writes_nullable_fields_as_null(marker, cleanup):
    sink = PostgresSink(TEST_DSN)
    await sink.write(_call(marker, user_email=None, account_id=None))
    await sink.close()

    with psycopg.connect(TEST_DSN) as conn:
        row = conn.execute(
            "SELECT user_email, account_id FROM tool_call WHERE server = %s",
            (marker,),
        ).fetchone()

    assert row == (None, None)


async def test_unreachable_database_raises_within_the_timeout():
    sink = PostgresSink("postgresql://nobody@127.0.0.1:1/nothing?connect_timeout=1")
    with pytest.raises(Exception):
        await sink.write(_call("unreachable"))
    await sink.close()
