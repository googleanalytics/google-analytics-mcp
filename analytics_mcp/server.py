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

import sys
import os
import argparse

# Add parent directory to path to make analytics_mcp importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics_mcp.coordinator import mcp, set_config_path

# The following imports are necessary to register the tools with the `mcp`
# object, even though they are not directly used in this file.
# The `# noqa: F401` comment tells the linter to ignore the "unused import"
# warning.
from analytics_mcp.tools.admin import info  # noqa: F401
from analytics_mcp.tools.reporting import realtime  # noqa: F401
from analytics_mcp.tools.reporting import core  # noqa: F401


def run_server(config_path: str = None) -> None:
    """Runs the server.

    Args:
        config_path: Path to the Google Analytics configuration file.
    
    Serves as the entrypoint for the 'runmcp' command.
    """
    if config_path:
        set_config_path(config_path)
    mcp.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Analytics MCP Server")
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to Google Analytics configuration file",
        default=os.environ.get('GOOGLE_ANALYTICS_CONFIG_PATH')
    )
    
    args = parser.parse_args()
    
    if not args.config:
        print("Error: Config file path required. Use --config or set GOOGLE_ANALYTICS_CONFIG_PATH", file=sys.stderr)
        sys.exit(1)
    
    try:
        run_server(args.config)
    except Exception as e:
        print(f"Server failed to start: {e}", file=sys.stderr)
        sys.exit(1)
