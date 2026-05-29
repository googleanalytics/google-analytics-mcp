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
from analytics_mcp.coordinator import mcp


def run_server() -> None:
    _CLIENT_ID = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_ID")
    _CLIENT_SECRET = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_SECRET")
    port = int(os.environ.get("PORT", "8080"))

    if _CLIENT_ID and _CLIENT_SECRET:
        mcp.run(transport="streamable-http", port=port, host="0.0.0.0")
    else:
        mcp.run()


if __name__ == "__main__":
    run_server()
