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

"""Deployable entry point supporting both stdio and streamable-http transport."""

import os
import tempfile
from analytics_mcp.coordinator_fastmcp import mcp


def _setup_credentials() -> None:
    """If GOOGLE_SA_KEY_JSON is set, write it to a temp file and point
    GOOGLE_APPLICATION_CREDENTIALS at it. This allows passing the service
    account key as a raw JSON string (e.g. from AWS Secrets Manager)."""
    sa_json = os.environ.get("GOOGLE_SA_KEY_JSON")
    if sa_json and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        fd, path = tempfile.mkstemp(suffix=".json", prefix="sa-key-")
        with os.fdopen(fd, "w") as f:
            f.write(sa_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path


_SENSITIVE_ENV_VARS = [
    "GOOGLE_SA_KEY_JSON",
    "ANALYTICS_MCP_OAUTH_CLIENT_SECRET",
]


def _clear_secrets() -> None:
    """Remove sensitive env vars after they have been consumed.
    Prevents leakage via /proc/*/environ, debug logs, or error traces."""
    for key in _SENSITIVE_ENV_VARS:
        os.environ.pop(key, None)


def run_server() -> None:
    """Starts the MCP server.

    Transport selection:
      - If ANALYTICS_MCP_OAUTH_CLIENT_ID is set, runs as streamable-http
        on the configured port (default 8080).
      - Otherwise, runs as stdio for local use.
    """
    _setup_credentials()
    _clear_secrets()

    client_id = os.environ.get("ANALYTICS_MCP_OAUTH_CLIENT_ID")
    port = int(os.environ.get("PORT", "8080"))

    if client_id:
        mcp.run(transport="streamable-http", port=port, host="0.0.0.0")
    else:
        mcp.run()


if __name__ == "__main__":
    run_server()
