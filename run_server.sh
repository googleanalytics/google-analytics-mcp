#!/bin/bash

# Set the project root directory
PROJECT_ROOT="$(dirname "$0")"

# Export the config path
export GOOGLE_ANALYTICS_CONFIG_PATH="$PROJECT_ROOT/google-analytics-config (4).json"

# Add the project root to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Install dependencies if needed (only once)
if ! /opt/homebrew/bin/python3 -c "import mcp" 2>/dev/null; then
    echo "Installing dependencies..." >&2
    /opt/homebrew/bin/python3 -m pip install --user google-analytics-admin google-analytics-data google-auth mcp httpx
fi

# Run the server
exec /opt/homebrew/bin/python3 "$PROJECT_ROOT/analytics_mcp/server.py"