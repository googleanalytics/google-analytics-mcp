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

Runs over streamable HTTP when OAuth client credentials are configured (the
per-user login flow); otherwise falls back to stdio for local development.
"""

import logging
import os

from analytics_mcp.coordinator import app

_LOGGERS_THAT_PRINT_ACCESS_TOKENS = ("httpx", "httpx2")


def run_server() -> None:
    """Runs the MCP server, choosing transport based on OAuth configuration."""
    for logger_name in _LOGGERS_THAT_PRINT_ACCESS_TOKENS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    client_id = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_SECRET")

    if client_id and client_secret:
        app.run(
            transport="streamable-http",
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "8000")),
        )
    else:
        app.run()


if __name__ == "__main__":
    run_server()
