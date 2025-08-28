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

"""Module declaring the singleton MCP instance.

The singleton allows other modules to register their tools with the same MCP
server using `@mcp.tool` annotations, thereby 'coordinating' the bootstrapping
of the server.
"""
import os
import sys
from mcp.server.fastmcp import FastMCP

# Global variable to store config path
_config_path = None

def set_config_path(config_path: str):
    """Set the global config path for the MCP server."""
    global _config_path
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    _config_path = config_path
    print(f"MCP server using config: {config_path}", file=sys.stderr)

def get_config_path() -> str:
    """Get the global config path for the MCP server."""
    if _config_path is None:
        raise RuntimeError("Config path not set. Call set_config_path() first.")
    return _config_path

# Creates the singleton.
mcp = FastMCP("Google Analytics Server")
