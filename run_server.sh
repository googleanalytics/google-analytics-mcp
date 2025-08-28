#!/bin/bash

# Set the project root directory
PROJECT_ROOT="$(dirname "$0")"

# Check if config path is provided as argument
if [ $# -eq 0 ]; then
    echo "Error: Config file path is required" >&2
    echo "Usage: $0 <config_path>" >&2
    exit 1
fi

CONFIG_PATH="$1"

# Check if config file exists
if [ ! -f "$CONFIG_PATH" ]; then
    echo "Error: Config file not found: $CONFIG_PATH" >&2
    exit 1
fi

# Add the project root to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Install dependencies if needed (only once)
if ! /opt/homebrew/bin/python3 -c "import mcp" 2>/dev/null; then
    echo "Installing dependencies..." >&2
    /opt/homebrew/bin/python3 -m pip install --user google-analytics-admin google-analytics-data google-auth mcp httpx
fi

echo "Starting MCP server with config: $CONFIG_PATH" >&2

# Run the server with config path
exec /opt/homebrew/bin/python3 "$PROJECT_ROOT/run_mcp_server.py" "$CONFIG_PATH"