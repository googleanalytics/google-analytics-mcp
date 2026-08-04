from __future__ import annotations

import logging

from fastmcp.server.middleware import Middleware

from .arguments import read_account_id
from .config import read_dsn
from .identity import read_identity
from .sink import PostgresSink, Sink, ToolCall

logger = logging.getLogger(__name__)


class UsageLogMiddleware(Middleware):
    def __init__(self, server: str, sink: Sink) -> None:
        self._server = server
        self._sink = sink

    @classmethod
    def from_env(cls, server: str) -> UsageLogMiddleware:
        return cls(server=server, sink=PostgresSink(read_dsn()))

    async def on_call_tool(self, context, call_next):
        status = "error"
        try:
            result = await call_next(context)
            status = "ok" if not result.is_error else "error"
            return result
        finally:
            await self._record(context, status)

    async def _record(self, context, status: str) -> None:
        try:
            identity = read_identity()
            if identity is None:
                logger.error(
                    "usage log skipped for %r: access token carries no sub claim",
                    context.message.name,
                )
                return
            if identity.email is None:
                logger.error("usage log has no email claim for sub %s", identity.sub)
            await self._sink.write(
                ToolCall(
                    occurred_at=context.timestamp,
                    server=self._server,
                    tool=context.message.name,
                    user_sub=identity.sub,
                    user_email=identity.email,
                    account_id=read_account_id(context.message.arguments),
                    status=status,
                )
            )
        except Exception:
            logger.error("usage log write failed", exc_info=True)
