"""The recorder is an observer: it must not alter a result, swallow an
exception, or let its own failure reach the caller."""

from datetime import timezone
from types import SimpleNamespace

import pytest

from analytics_mcp.usage_log.identity import Identity, IdentityLookupError
from analytics_mcp.usage_log.recorder import ToolCallRecorder
from analytics_mcp.usage_log.sink import ToolCall

IDENTITY = Identity(sub="1234", email="piotr@touchpoint.agency")
TOKEN = "ya29.token"


class FakeResolver:
    def __init__(self, identity: Identity | None = IDENTITY):
        self.identity = identity
        self.tokens: list[str] = []

    async def resolve(self, access_token: str) -> Identity | None:
        self.tokens.append(access_token)
        return self.identity


class FailingResolver:
    async def resolve(self, access_token: str) -> Identity | None:
        raise IdentityLookupError("userinfo lookup failed with HTTP 401")


class RecordingSink:
    def __init__(self):
        self.calls: list[ToolCall] = []

    async def write(self, call: ToolCall) -> None:
        self.calls.append(call)


class FailingSink:
    async def write(self, call: ToolCall) -> None:
        raise RuntimeError("database is down")


def _result(is_error: bool = False):
    return SimpleNamespace(is_error=is_error)


def _recorder(sink, identities=None) -> ToolCallRecorder:
    return ToolCallRecorder(
        server="google-analytics",
        sink=sink,
        identities=identities or FakeResolver(),
    )


async def test_successful_call_is_logged_as_ok():
    sink = RecordingSink()
    resolver = FakeResolver()
    result = _result()

    returned = await _recorder(sink, resolver).record(
        TOKEN, "run_report", {"property_id": 42}, lambda: _returns(result)
    )

    assert returned is result
    assert resolver.tokens == [TOKEN]
    [written] = sink.calls
    assert written.occurred_at.tzinfo is timezone.utc
    assert (
        written.server,
        written.tool,
        written.user_sub,
        written.user_email,
        written.account_id,
        written.status,
    ) == (
        "google-analytics",
        "run_report",
        "1234",
        "piotr@touchpoint.agency",
        "42",
        "ok",
    )


async def test_raising_tool_is_logged_as_error_and_reraised():
    sink = RecordingSink()
    failure = ValueError("upstream exploded")

    with pytest.raises(ValueError) as raised:
        await _recorder(sink).record(
            TOKEN, "run_report", {}, lambda: _raises(failure)
        )

    assert raised.value is failure
    assert [call.status for call in sink.calls] == ["error"]


async def test_error_result_is_logged_as_error_and_returned_unchanged():
    sink = RecordingSink()
    result = _result(is_error=True)

    returned = await _recorder(sink).record(
        TOKEN, "run_report", {}, lambda: _returns(result)
    )

    assert returned is result
    assert [call.status for call in sink.calls] == ["error"]


async def test_sink_failure_does_not_break_the_tool_call():
    result = _result()

    returned = await _recorder(FailingSink()).record(
        TOKEN, "run_report", {}, lambda: _returns(result)
    )

    assert returned is result


async def test_identity_lookup_failure_does_not_break_the_tool_call():
    sink = RecordingSink()
    result = _result()

    returned = await _recorder(sink, FailingResolver()).record(
        TOKEN, "run_report", {}, lambda: _returns(result)
    )

    assert returned is result
    assert sink.calls == []


async def test_missing_token_writes_nothing_but_still_serves_the_call():
    sink = RecordingSink()
    resolver = FakeResolver()
    result = _result()

    returned = await _recorder(sink, resolver).record(
        None, "run_report", {}, lambda: _returns(result)
    )

    assert returned is result
    assert resolver.tokens == []
    assert sink.calls == []


async def test_missing_sub_writes_nothing_but_still_serves_the_call():
    sink = RecordingSink()
    result = _result()

    returned = await _recorder(sink, FakeResolver(identity=None)).record(
        TOKEN, "run_report", {}, lambda: _returns(result)
    )

    assert returned is result
    assert sink.calls == []


async def test_unlisted_arguments_never_reach_the_row():
    sink = RecordingSink()
    arguments = {"dimensions": ["city"], "metrics": ["activeUsers"]}

    await _recorder(sink).record(
        TOKEN, "run_report", arguments, lambda: _returns(_result())
    )

    [written] = sink.calls
    assert written.account_id is None
    assert "activeUsers" not in repr(written)


async def _returns(value):
    return value


async def _raises(error):
    raise error
