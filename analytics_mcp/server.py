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
import os
import sys
import traceback
from typing import Sequence
from urllib.parse import urlparse

import analytics_mcp.coordinator as coordinator
from analytics_mcp.oauth import GoogleOAuthProvider, build_oauth_components
import mcp.server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.server.transport_security import TransportSecuritySettings
import uvicorn


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
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help=(
            "Transport protocol to use: 'stdio' (default, uses local ADC) or "
            "'http' (Streamable HTTP for multi-tenant deployments, requires "
            "per-request OAuth Bearer tokens)."
        ),
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind when --transport=http (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT") or "8000"),
        help=(
            "Port to bind when --transport=http "
            "(default: PORT env var or 8000)."
        ),
    )
    parser.add_argument(
        "--stateless-http",
        action="store_true",
        help="Enable stateless Streamable HTTP mode when --transport=http.",
    )
    parser.add_argument(
        "--oauth",
        action="store_true",
        help=(
            "Enable the built-in MCP OAuth 2.1 Authorization Server proxying "
            "Google OAuth 2.0 when --transport=http (requires "
            "GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)."
        ),
    )
    parser.add_argument(
        "--issuer-url",
        default=None,
        help=(
            "Public issuer base URL when --oauth is enabled (defaults to "
            "ANALYTICS_MCP_ISSUER_URL or http://<host>:<port>)."
        ),
    )
    return parser.parse_args(argv)


def build_http_app(args: argparse.Namespace):
    """Builds the Starlette ASGI app for multi-tenant Streamable HTTP mode."""
    app = coordinator.create_server(
        allow_write=args.allow_write,
        require_request_credentials=True,
    )

    auth_settings = None
    token_verifier = None
    oauth_provider = None
    custom_routes = None
    transport_security = None

    explicit_issuer_url = (
        args.issuer_url or os.environ.get("ANALYTICS_MCP_ISSUER_URL") or ""
    ).strip()

    if args.oauth:
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            raise ValueError(
                "--oauth requires GOOGLE_OAUTH_CLIENT_ID and "
                "GOOGLE_OAUTH_CLIENT_SECRET environment variables to be set."
            )
        default_host = (
            "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
        )
        issuer_url = explicit_issuer_url or f"http://{default_host}:{args.port}"
        oauth_provider = GoogleOAuthProvider(
            google_client_id=client_id,
            google_client_secret=client_secret,
            issuer_url=issuer_url,
            allow_write=args.allow_write,
        )
        auth_settings, token_verifier, custom_routes = build_oauth_components(
            oauth_provider
        )

    if explicit_issuer_url and args.host in ("127.0.0.1", "localhost", "::1"):
        parsed_issuer = urlparse(explicit_issuer_url)
        if parsed_issuer.netloc:
            transport_security = TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=[
                    "127.0.0.1:*",
                    "localhost:*",
                    "[::1]:*",
                    parsed_issuer.netloc,
                ],
                allowed_origins=[
                    "http://127.0.0.1:*",
                    "http://localhost:*",
                    "http://[::1]:*",
                    f"{parsed_issuer.scheme}://{parsed_issuer.netloc}",
                ],
            )

    return app.streamable_http_app(
        host=args.host,
        stateless_http=args.stateless_http,
        transport_security=transport_security,
        auth=auth_settings,
        token_verifier=token_verifier,
        auth_server_provider=oauth_provider,
        custom_starlette_routes=custom_routes,
    )


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
    """Synchronous wrapper to run the MCP server."""
    args = parse_args(argv)
    if args.transport == "http":
        http_app = build_http_app(args)
        print(
            f"Starting MCP Streamable HTTP Server on http://{args.host}:{args.port}/mcp",
            file=sys.stderr,
        )
        uvicorn.run(http_app, host=args.host, port=args.port)
    else:
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
