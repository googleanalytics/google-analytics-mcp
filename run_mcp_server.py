#!/usr/bin/env python3
"""Wrapper to run the MCP server with proper environment."""

import sys
import os

# Set up paths
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    # Import and run the server with explicit config path
    from analytics_mcp.server import run_server
    
    # Config path is required as command line argument
    if len(sys.argv) < 2:
        print(f"Error: Config file path is required", file=sys.stderr)
        print(f"Usage: {sys.argv[0]} <config_path>", file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    if not os.path.exists(config_path):
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        print(f"Usage: {sys.argv[0]} <config_path>", file=sys.stderr)
        sys.exit(1)
    
    print(f"Starting MCP server with config: {config_path}", file=sys.stderr)
    run_server(config_path)
    
except Exception as e:
    print(f"Server crashed with error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)