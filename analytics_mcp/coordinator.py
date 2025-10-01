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
import logging
from typing import Optional
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Global variable to store config path
_config_path: Optional[str] = None


def set_config_path(config_path: str):
    """Set the global config path for the MCP server.

    Args:
        config_path: Path to OAuth config file

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    global _config_path

    # Validate file exists and is readable
    with open(config_path, 'r') as f:
        f.read(1)  # Try to read at least 1 byte

    _config_path = config_path
    logger.info(f"MCP server using config: {config_path}")


def get_config_path() -> Optional[str]:
    """Get the global config path for the MCP server.

    Returns:
        Config file path or None if not set
    """
    return _config_path


# Creates the singleton.
mcp = FastMCP("Google Analytics Server")
