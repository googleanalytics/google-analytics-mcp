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

import analytics_mcp.coordinator as coordinator


def run_server() -> None:
    """Runs the MCP server.

    Uses streamable-http transport with OAuth when ANALYTICS_MCP_OAUTH_CLIENT_ID
    and ANALYTICS_MCP_OAUTH_CLIENT_SECRET are set (Cloud Run / remote mode).
    Falls back to stdio transport for local subprocess use.
    """
    _client_id = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_ID")
    _client_secret = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_SECRET")
    port = int(os.environ.get("PORT", "8080"))

    if _client_id and _client_secret:
        print(
            f"Starting MCP HTTP Server on port {port} (OAuth mode)",
            file=sys.stderr,
        )
        coordinator.mcp.run(
            transport="streamable-http", port=port, host="0.0.0.0"
        )
    else:
        print("Starting MCP Stdio Server", file=sys.stderr)
        coordinator.mcp.run()


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nMCP Server stopped by user.", file=sys.stderr)
    except Exception:
        print("MCP Server encountered an error:", file=sys.stderr)
        traceback.print_exc()
    finally:
        print("MCP Server process exiting.", file=sys.stderr)
