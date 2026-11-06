from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import httpx
from mcp import types as mcp_types

from .arguments import read_account_id
from .config import read_dsn
from .identity import IdentityResolver
from .sink import PostgresSink, Sink, ToolCall

logger = logging.getLogger(__name__)

USERINFO_TIMEOUT_SECONDS = 5.0


class ToolCallRecorder:
    """Runs a tool call and records who called which tool with what outcome.

    The recorder is an observer: it never alters a result, never swallows an
    exception raised by the call, and never lets its own failure reach the
    caller.
    """

    def __init__(
        self, server: str, sink: Sink, identities: IdentityResolver
    ) -> None:
        self._server = server
        self._sink = sink
        self._identities = identities

    @classmethod
    def from_env(cls, server: str) -> ToolCallRecorder:
        return cls(
            server=server,
            sink=PostgresSink(read_dsn()),
            identities=IdentityResolver(
                httpx.AsyncClient(timeout=USERINFO_TIMEOUT_SECONDS)
            ),
        )

    async def record(
        self,
        access_token: str | None,
        tool: str,
        arguments: dict[str, Any] | None,
        call: Callable[[], Awaitable[mcp_types.CallToolResult]],
    ) -> mcp_types.CallToolResult:
        occurred_at = datetime.now(timezone.utc)
        status = "error"
        try:
            result = await call()
            status = "error" if result.is_error else "ok"
            return result
        finally:
            await self._write(
                occurred_at, access_token, tool, arguments, status
            )

    async def _write(
        self,
        occurred_at: datetime,
        access_token: str | None,
        tool: str,
        arguments: dict[str, Any] | None,
        status: str,
    ) -> None:
        try:
            if access_token is None:
                logger.error(
                    "usage log skipped for %r: request carries no access token",
                    tool,
                )
                return
            identity = await self._identities.resolve(access_token)
            if identity is None:
                logger.error(
                    "usage log skipped for %r: userinfo carries no sub claim",
                    tool,
                )
                return
            if identity.email is None:
                logger.error(
                    "usage log has no email claim for sub %s", identity.sub
                )
            await self._sink.write(
                ToolCall(
                    occurred_at=occurred_at,
                    server=self._server,
                    tool=tool,
                    user_sub=identity.sub,
                    user_email=identity.email,
                    account_id=read_account_id(arguments),
                    status=status,
                )
            )
        except Exception:
            logger.error("usage log write failed", exc_info=True)
