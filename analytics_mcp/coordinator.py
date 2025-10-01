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
    try:
        # Test if we can actually read the file (not just check if it exists)
        with open(config_path, 'r') as f:
            f.read(1)  # Try to read at least 1 byte
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except PermissionError as e:
        print(f"Permission denied accessing config file: {config_path}", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("SOLUTION: Move your config file to an accessible location:", file=sys.stderr)
        print(f"  cp '{config_path}' '/Users/{os.environ.get('USER', 'your-username')}/projects/google-analytics-mcp/'", file=sys.stderr)
        print("Then run the MCP server with the new path:", file=sys.stderr)
        print(f"  python run_mcp_server.py '/Users/{os.environ.get('USER', 'your-username')}/projects/google-analytics-mcp/{os.path.basename(config_path)}'", file=sys.stderr)
        print("", file=sys.stderr)
        print("Alternatively, grant your Terminal app access to the Desktop folder:", file=sys.stderr)
        print("  System Settings → Privacy & Security → Files and Folders → Terminal → Enable Desktop", file=sys.stderr)
        raise PermissionError(f"Cannot access config file: {config_path}")
    except Exception as e:
        error_msg = str(e).lower()
        if "operation not permitted" in error_msg or "permission denied" in error_msg:
            print(f"Permission error accessing config file: {config_path}", file=sys.stderr)
            print(f"Error: {e}", file=sys.stderr)
            print("", file=sys.stderr)
            print("SOLUTION: Move your config file to an accessible location:", file=sys.stderr)
            print(f"  cp '{config_path}' '/Users/{os.environ.get('USER', 'your-username')}/projects/google-analytics-mcp/'", file=sys.stderr)
            print("Then run the MCP server with the new path:", file=sys.stderr)
            print(f"  python run_mcp_server.py '/Users/{os.environ.get('USER', 'your-username')}/projects/google-analytics-mcp/{os.path.basename(config_path)}'", file=sys.stderr)
            print("", file=sys.stderr)
            print("Alternatively, grant your Terminal app access to the Desktop folder:", file=sys.stderr)
            print("  System Settings → Privacy & Security → Files and Folders → Terminal → Enable Desktop", file=sys.stderr)
            raise PermissionError(f"Cannot access config file: {config_path}")
        else:
            raise e

    _config_path = config_path
    print(f"MCP server using config: {config_path}", file=sys.stderr)

def get_config_path() -> str:
    """Get the global config path for the MCP server."""
    if _config_path is None:
        raise RuntimeError("Config path not set. Call set_config_path() first.")
    return _config_path

# Creates the singleton.
mcp = FastMCP("Google Analytics Server")
