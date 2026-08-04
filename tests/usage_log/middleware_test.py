"""Covers runbook tests 1-3 (phase-2-middleware.md 2.11).
The middleware is an observer: it must not alter a result, swallow an
exception, or let its own failure reach the caller."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import analytics_mcp.usage_log.identity as identity_module
from analytics_mcp.usage_log.middleware import UsageLogMiddleware
from analytics_mcp.usage_log.sink import ToolCall

TIMESTAMP = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


class FakeToken:
    claims = {"sub": "1234", "email": "piotr@touchpoint.agency"}


class RecordingSink:
    def __init__(self):
        self.calls: list[ToolCall] = []

    async def write(self, call: ToolCall) -> None:
        self.calls.append(call)


class FailingSink:
    async def write(self, call: ToolCall) -> None:
        raise RuntimeError("database is down")


class FakeResult:
    def __init__(self, is_error: bool = False):
        self.is_error = is_error


@pytest.fixture(autouse=True)
def authenticated(monkeypatch):
    monkeypatch.setattr(identity_module, "get_access_token", lambda: FakeToken())


def _context(tool: str = "list_products", arguments: dict | None = None):
    return SimpleNamespace(
        timestamp=TIMESTAMP,
        message=SimpleNamespace(name=tool, arguments=arguments or {"merchant_id": 42}),
    )


async def test_successful_call_is_logged_as_ok():
    sink = RecordingSink()
    middleware = UsageLogMiddleware(server="google-merchant", sink=sink)
    result = FakeResult()

    returned = await middleware.on_call_tool(_context(), lambda ctx: _returns(result))

    assert returned is result
    assert sink.calls == [
        ToolCall(
            occurred_at=TIMESTAMP,
            server="google-merchant",
            tool="list_products",
            user_sub="1234",
            user_email="piotr@touchpoint.agency",
            account_id="42",
            status="ok",
        )
    ]


async def test_raising_tool_is_logged_as_error_and_reraised():
    sink = RecordingSink()
    middleware = UsageLogMiddleware(server="google-merchant", sink=sink)
    failure = ValueError("upstream exploded")

    with pytest.raises(ValueError) as raised:
        await middleware.on_call_tool(_context(), lambda ctx: _raises(failure))

    assert raised.value is failure
    assert [call.status for call in sink.calls] == ["error"]


async def test_error_result_is_logged_as_error_and_returned_unchanged():
    sink = RecordingSink()
    middleware = UsageLogMiddleware(server="google-merchant", sink=sink)
    result = FakeResult(is_error=True)

    returned = await middleware.on_call_tool(_context(), lambda ctx: _returns(result))

    assert returned is result
    assert [call.status for call in sink.calls] == ["error"]


async def test_sink_failure_does_not_break_the_tool_call():
    middleware = UsageLogMiddleware(server="google-merchant", sink=FailingSink())
    result = FakeResult()

    returned = await middleware.on_call_tool(_context(), lambda ctx: _returns(result))

    assert returned is result


async def test_missing_sub_writes_nothing_but_still_serves_the_call(monkeypatch):
    monkeypatch.setattr(identity_module, "get_access_token", lambda: None)
    sink = RecordingSink()
    middleware = UsageLogMiddleware(server="google-merchant", sink=sink)
    result = FakeResult()

    returned = await middleware.on_call_tool(_context(), lambda ctx: _returns(result))

    assert returned is result
    assert sink.calls == []


async def test_unlisted_arguments_never_reach_the_row():
    sink = RecordingSink()
    middleware = UsageLogMiddleware(server="google-ads", sink=sink)
    context = _context(arguments={"query": "SELECT campaign.name FROM campaign"})

    await middleware.on_call_tool(context, lambda ctx: _returns(FakeResult()))

    written = sink.calls[0]
    assert written.account_id is None
    assert "campaign" not in repr(written)


async def _returns(value):
    return value


async def _raises(error):
    raise error
