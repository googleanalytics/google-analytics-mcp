from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from psycopg_pool import AsyncConnectionPool

INSERT_SQL = """
INSERT INTO tool_call
  (occurred_at, server, tool, user_sub, user_email, account_id, status)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

WRITE_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True)
class ToolCall:
    occurred_at: datetime
    server: str
    tool: str
    user_sub: str
    user_email: str | None
    account_id: str | None
    status: str


class Sink(Protocol):
    async def write(self, call: ToolCall) -> None: ...


class PostgresSink:
    def __init__(self, dsn: str, max_size: int = 3) -> None:
        self._pool = AsyncConnectionPool(dsn, min_size=1, max_size=max_size, open=False)
        self._opened = False
        self._open_lock = asyncio.Lock()

    async def write(self, call: ToolCall) -> None:
        await asyncio.wait_for(self._write(call), timeout=WRITE_TIMEOUT_SECONDS)

    async def _write(self, call: ToolCall) -> None:
        await self._ensure_open()
        async with self._pool.connection() as conn:
            await conn.execute(
                INSERT_SQL,
                (
                    call.occurred_at,
                    call.server,
                    call.tool,
                    call.user_sub,
                    call.user_email,
                    call.account_id,
                    call.status,
                ),
            )

    async def _ensure_open(self) -> None:
        if self._opened:
            return
        async with self._open_lock:
            if not self._opened:
                await self._pool.open()
                self._opened = True

    async def close(self) -> None:
        if self._opened:
            await self._pool.close()
            self._opened = False
