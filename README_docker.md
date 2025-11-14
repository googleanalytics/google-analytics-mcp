# Google Analytics MCP Server - Docker Setup

This guide explains how to run the Google Analytics MCP server using Docker with the required environment variables.

## Quick Start with Docker

### 1. Build the Docker Image

```bash
docker build -t analytics-mcp .
```

### 2. Set Up Environment Variables
You can provide env variables either via a `.env` file or directly to the docker container.
Example env variables:
```bash
# Log level for the MCP server
FASTMCP_LOG_LEVEL="INFO"

# Transport protocol for the MCP server
FASTMCP_TRANSPORT="streamable-http"  # can be also stdio or sse (legacy)

# OAuth issuer URL (your authentication server)
FASTMCP_AUTH__ISSUER_URL="http://127.0.0.1:9000"

# Resource server URL where the MCP server will be available
# current server URL + /mcp for streamable-http transport
FASTMCP_AUTH__RESOURCE_SERVER_URL="http://127.0.0.1:8000/mcp"

# Required OAuth scopes for Google Analytics access
FASTMCP_AUTH__REQUIRED_SCOPES='["https://www.googleapis.com/auth/analytics.readonly"]'
```

### 3. Run the Container

```bash
docker run --env-file .env -p 8000:8000 analytics-mcp
```

Or run with environment variables directly:

```bash
docker run \
  -e FASTMCP_LOG_LEVEL="INFO" \
  -e FASTMCP_TRANSPORT="streamable-http" \
  -e FASTMCP_AUTH__ISSUER_URL="http://127.0.0.1:9000" \
  -e FASTMCP_AUTH__RESOURCE_SERVER_URL="http://127.0.0.1:8000/mcp" \
  -e FASTMCP_AUTH__REQUIRED_SCOPES='["https://www.googleapis.com/auth/analytics.readonly"]' \
  -p 8000:8000 \
  analytics-mcp
```
