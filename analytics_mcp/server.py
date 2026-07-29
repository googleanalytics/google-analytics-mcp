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

"""Entry point for the Google Analytics MCP server.

Supports two transports:

* **STDIO** (default) — interop with local MCP clients over process pipes.
* **Streamable HTTP** — remote deployment; serves the MCP protocol on an
  HTTP endpoint (``POST /mcp``). Pass ``--http`` or set the environment
  variable ``ANALYTICS_MCP_TRANSPORT=http`` to enable it.

When using the HTTP transport, callers must include the
``x-ga-refresh-token`` header on every request carrying a valid Google OAuth
refresh token for the authorized user. The server builds per-request
``authorized_user`` credentials from
``GOOGLE_ANALYTICS_CLIENT_ID``/``GOOGLE_ANALYTICS_CLIENT_SECRET`` (required
environment variables) and the header value.
"""

import argparse
import asyncio
import os
import sys
import traceback
from dotenv import load_dotenv

import analytics_mcp.coordinator as coordinator
import mcp.server
import mcp.server.stdio
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions

# ---- Transport selection -------------------------------------------------

_TRANSPORT_STDIO = "stdio"
_TRANSPORT_HTTP = "http"
_VALID_TRANSPORTS = (_TRANSPORT_STDIO, _TRANSPORT_HTTP)

load_dotenv()

def _resolve_transport(cli_http_flag: bool) -> str:
    """Pick a transport based on CLI flag then env var. Defaults to stdio."""
    if cli_http_flag:
        return _TRANSPORT_HTTP
    env = os.getenv("ANALYTICS_MCP_TRANSPORT", _TRANSPORT_STDIO).lower()
    if env not in _VALID_TRANSPORTS:
        print(
            f"Warning: unknown ANALYTICS_MCP_TRANSPORT value {env!r}; "
            f"falling back to '{_TRANSPORT_STDIO}'.",
            file=sys.stderr,
        )
        return _TRANSPORT_STDIO
    return env


# ---- STDIO transport ------------------------------------------------------


async def run_server_async():
    """Runs the MCP server over standard I/O."""
    print("Starting MCP Stdio Server:", coordinator.app.name, file=sys.stderr)
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await coordinator.app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=coordinator.app.name,
                server_version="1.0.0",
                capabilities=coordinator.app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run_server():
    """Synchronous wrapper to run the async MCP server (stdio by default).

    If ``ANALYTICS_MCP_TRANSPORT=http`` or ``--http`` was passed on the
    command line, this delegates to :func:`run_http_server` instead.
    """
    parser = argparse.ArgumentParser(
        description="Google Analytics MCP Server.",
        add_help=True,
    )
    parser.add_argument(
        "--http",
        action="store_true",
        default=False,
        help="Run the streamable HTTP transport (serves /mcp).",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("ANALYTICS_MCP_HTTP_HOST", "127.0.0.1"),
        help="Bind host for HTTP transport (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("ANALYTICS_MCP_HTTP_PORT", "8000")),
        help="Bind port for HTTP transport (default: 8000).",
    )
    parser.add_argument(
        "--path",
        default=os.getenv("ANALYTICS_MCP_HTTP_PATH", "/mcp"),
        help="URL path for the MCP HTTP endpoint (default: /mcp).",
    )
    args, _unknown = parser.parse_known_args()

    transport = _resolve_transport(args.http)
    if transport == _TRANSPORT_HTTP:
        run_http_server(host=args.host, port=args.port, path=args.path)
    else:
        asyncio.run(run_server_async())


# ---- Streamable HTTP transport -------------------------------------------


async def run_http_server_async(
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp",
) -> None:
    """Run the MCP server using the streamable HTTP transport.

    Args:
        host: Interface address to bind to.
        port: TCP port to bind to.
        path: URL path that serves the MCP protocol (``POST`` + SSE).
    """
    try:
        import uvicorn  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - install hint
        raise ModuleNotFoundError(
            "The 'uvicorn' package is required for the HTTP transport. "
            'Install it with: pip install "analytics-mcp[http]"'
        ) from exc

    # Validate required env vars early for a clear error on startup.
    missing: list[str] = []
    if not os.getenv("GOOGLE_ANALYTICS_CLIENT_ID"):
        missing.append("GOOGLE_ANALYTICS_CLIENT_ID")
    if not os.getenv("GOOGLE_ANALYTICS_CLIENT_SECRET"):
        missing.append("GOOGLE_ANALYTICS_CLIENT_SECRET")
    if missing:
        print(
            "HTTP transport requires the following environment variables to "
            "build authorized_user credentials from the x-ga-refresh-token "
            "header: " + ", ".join(missing),
            file=sys.stderr,
        )

    starlette_app = coordinator.app.streamable_http_app(
        streamable_http_path=path,
        host=host,
    )

    url = f"http://{host}:{port}{path}"
    print(
        f"Starting MCP Streamable HTTP Server: {coordinator.app.name} "
        f"on {url}",
        file=sys.stderr,
    )
    config = uvicorn.Config(
        starlette_app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


def run_http_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp",
) -> None:
    """Synchronous wrapper around :func:`run_http_server_async`."""
    asyncio.run(run_http_server_async(host=host, port=port, path=path))


# ---- __main__ dispatcher --------------------------------------------------

if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print(
            "\nMCP Server stopped by user (keyboard interrupt).",
            file=sys.stderr,
        )
    except Exception:
        print("MCP Server encountered an error:", file=sys.stderr)
        traceback.print_exc()
    finally:
        print("MCP Server process exiting.", file=sys.stderr)
