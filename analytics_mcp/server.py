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

import argparse
import asyncio
import sys
from typing import Sequence
import analytics_mcp.coordinator as coordinator
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.server
import traceback


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parses command-line arguments for the MCP server."""
    parser = argparse.ArgumentParser(
        description="Google Analytics MCP Server",
    )
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help=(
            "Enable tools that create or modify Google Analytics resources "
            "(requires https://www.googleapis.com/auth/analytics.edit scope)."
        ),
    )
    return parser.parse_args(argv)


async def run_server_async(allow_write: bool = False):
    """Runs the MCP server over standard I/O."""
    app = coordinator.create_server(allow_write=allow_write)
    print("Starting MCP Stdio Server:", app.name, file=sys.stderr)
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,  # Use the server name defined above
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    # Define server capabilities - consult MCP docs for options
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run_server(argv: Sequence[str] | None = None):
    """Synchronous wrapper to run the async MCP server."""
    args = parse_args(argv)
    asyncio.run(run_server_async(allow_write=args.allow_write))


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nMCP Server (stdio) stopped by user.", file=sys.stderr)
    except Exception:
        import traceback

        print("MCP Server (stdio) encountered an error:", file=sys.stderr)
        traceback.print_exc()
    finally:
        print("MCP Server (stdio) process exiting.", file=sys.stderr)
