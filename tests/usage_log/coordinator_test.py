from types import SimpleNamespace

import pytest

from analytics_mcp import coordinator
from analytics_mcp.tools import client
from mcp import types as mcp_types


class RecordingRecorder:
    def __init__(self):
        self.calls = []

    async def record(self, access_token, tool, arguments, call):
        result = await call()
        self.calls.append((access_token, tool, arguments, result.is_error))
        return result


@pytest.fixture(autouse=True)
def reset_client_policy():
    yield
    client.set_allow_write(False)
    client.set_require_request_credentials(False)


def _call_handler(recorder):
    server = coordinator.create_server(
        require_request_credentials=True, recorder=recorder
    )
    return server.get_request_handler("tools/call").handler


def _ctx(token: str):
    headers = {"authorization": f"Bearer {token}"}
    return SimpleNamespace(request=SimpleNamespace(headers=headers))


async def test_every_tool_call_passes_through_the_recorder():
    recorder = RecordingRecorder()
    params = mcp_types.CallToolRequestParams(
        name="no_such_tool", arguments={"property_id": "123"}
    )

    result = await _call_handler(recorder)(_ctx("tenant-token"), params)

    assert result.is_error
    assert recorder.calls == [
        ("tenant-token", "no_such_tool", {"property_id": "123"}, True)
    ]


async def test_server_without_recorder_still_serves():
    params = mcp_types.CallToolRequestParams(name="no_such_tool", arguments={})

    result = await _call_handler(None)(_ctx("tenant-token"), params)

    assert result.is_error
    assert "not implemented" in result.content[0].text
