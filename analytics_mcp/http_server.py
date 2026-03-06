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

"""HTTP/SSE entry point for the Google Analytics MCP server.

Run this module instead of server.py when deploying to Render or any
HTTP host. The MCP protocol is served over SSE at /sse (server→client)
and POST /messages/ (client→server). Plain HTTP utility endpoints at
/health and /tools are also available.

Usage:
    python -m analytics_mcp.http_server

Environment variables:
    GOOGLE_APPLICATION_CREDENTIALS_JSON  Service-account JSON *content*
                                         (used on Render instead of a file)
    GOOGLE_APPLICATION_CREDENTIALS       Path to a service-account JSON file
                                         (standard ADC, useful locally)
    PORT                                 Port to listen on (default: 8000)
"""

import json
import os
import sys
import tempfile

import uvicorn
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

import analytics_mcp.coordinator as coordinator
from analytics_mcp.coordinator import mcp_tools


# ---------------------------------------------------------------------------
# Credentials bootstrap
# ---------------------------------------------------------------------------

def _setup_google_credentials() -> None:
    """Bootstrap Google credentials before any GA client is created.

    Priority:
    1. GOOGLE_APPLICATION_CREDENTIALS_JSON  – JSON *string* (Render / CI)
    2. GOOGLE_APPLICATION_CREDENTIALS       – file path  (local dev)
    3. Neither set → warn; google.auth.default() will fail on first GA call.
    """
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()

    if creds_json:
        try:
            parsed = json.loads(creds_json)
        except json.JSONDecodeError as exc:
            print(
                f"[http_server] ERROR: GOOGLE_APPLICATION_CREDENTIALS_JSON "
                f"is not valid JSON: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Write to a temp file that persists for the lifetime of the process
        # so that google.auth.default() can discover it via the env var.
        fd, path = tempfile.mkstemp(suffix=".json", prefix="ga_creds_")
        with os.fdopen(fd, "w") as fh:
            json.dump(parsed, fh)

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
        account = parsed.get("client_email") or parsed.get("type", "unknown")
        print(f"[http_server] Google credentials loaded from env var (account: {account})")
        return

    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print(
            f"[http_server] Using credential file: "
            f"{os.environ['GOOGLE_APPLICATION_CREDENTIALS']}"
        )
        return

    print(
        "[http_server] WARNING: No Google credentials configured. "
        "Set GOOGLE_APPLICATION_CREDENTIALS_JSON (Render) or "
        "GOOGLE_APPLICATION_CREDENTIALS (local dev). "
        "GA tool calls will fail until credentials are provided.",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Utility HTTP endpoints (no MCP handshake required)
# ---------------------------------------------------------------------------

async def health_endpoint(request: Request) -> JSONResponse:
    """GET /health — liveness probe for Render / load-balancers."""
    return JSONResponse(
        {
            "status": "ok",
            "server": coordinator.app.name,
            "version": "1.0.0",
        }
    )


async def tools_endpoint(request: Request) -> JSONResponse:
    """GET /tools — list all registered MCP tools (no credentials needed)."""
    tools_list = [
        {
            "name": t.name,
            "description": (t.description or "")[:300],
        }
        for t in mcp_tools
    ]
    return JSONResponse({"tools": tools_list, "count": len(tools_list)})


# ---------------------------------------------------------------------------
# MCP SSE transport
# ---------------------------------------------------------------------------

def create_app() -> Starlette:
    """Build and return the Starlette ASGI application."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> Response:
        """SSE endpoint: long-lived server→client event stream."""
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await coordinator.app.run(
                streams[0],
                streams[1],
                InitializationOptions(
                    server_name=coordinator.app.name,
                    server_version="1.0.0",
                    capabilities=coordinator.app.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
        return Response()

    return Starlette(
        routes=[
            Route("/health", endpoint=health_endpoint, methods=["GET"]),
            Route("/tools", endpoint=tools_endpoint, methods=["GET"]),
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    _setup_google_credentials()
    port = int(os.environ.get("PORT", "8000"))
    print(f"[http_server] Starting Google Analytics MCP on port {port}")
    uvicorn.run(create_app(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
