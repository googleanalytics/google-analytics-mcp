#!/usr/bin/env python

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

"""Entry point for the Google Analytics MCP server."""

import os
import sys
import traceback

from analytics_mcp.coordinator import mcp

STDIO_TRANSPORT = "stdio"
HTTP_TRANSPORTS = {"http", "streamable-http"}
SUPPORTED_TRANSPORTS = {STDIO_TRANSPORT, *HTTP_TRANSPORTS}


def _configured_transport() -> str:
    """Return and validate the requested transport."""
    transport = os.getenv("ANALYTICS_MCP_TRANSPORT", STDIO_TRANSPORT)
    transport = transport.strip().lower()
    if transport not in SUPPORTED_TRANSPORTS:
        choices = ", ".join(sorted(SUPPORTED_TRANSPORTS))
        raise ValueError(
            "Unsupported ANALYTICS_MCP_TRANSPORT "
            f"{transport!r}; expected one of: {choices}"
        )
    return transport


def _configured_port() -> int:
    """Return and validate the HTTP listen port."""
    raw_port = os.getenv("PORT", "8080")
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError(
            f"PORT must be an integer, got {raw_port!r}"
        ) from error
    if not 1 <= port <= 65535:
        raise ValueError(f"PORT must be between 1 and 65535, got {port}")
    return port


def run_server() -> None:
    """Run stdio by default, or stateful Streamable HTTP when configured."""
    transport = _configured_transport()
    if transport == STDIO_TRANSPORT:
        mcp.run()
        return

    mcp.run(
        transport="streamable-http",
        host=os.getenv("HOST", "127.0.0.1"),
        port=_configured_port(),
        uvicorn_config={"access_log": False},
    )


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nGoogle Analytics MCP server stopped.", file=sys.stderr)
    except Exception:
        print(
            "Google Analytics MCP server encountered an error:", file=sys.stderr
        )
        traceback.print_exc()
        raise
