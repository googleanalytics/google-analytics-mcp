# Ovative Changes — Google Analytics MCP

> **Upstream repo:** https://github.com/googleanalytics/google-analytics-mcp  
> **Last synced with upstream:** v0.6.0 (commit `1099661`)  
> **Purpose of changes:** Enable deployment to Google Cloud Run with per-user OAuth authentication, removing the requirement for developers to install and configure the MCP locally.

---

## What changed and why

### 1. `pyproject.toml`
**What:** Replaced `google-adk` with `fastmcp`.  
**Why:** The Google Agent Development Kit only supported stdio transport (local installs). FastMCP supports both stdio and HTTP transports, and provides a built-in Google OAuth proxy — required for Cloud Run deployment.

```diff
- google-adk>=1.29.0
+ fastmcp>=3.2.0
```

---

### 2. `analytics_mcp/coordinator.py`
**What:** Complete rewrite. Replaced low-level `mcp.server.lowlevel.Server` + ADK `FunctionTool` with FastMCP.  
**Why:** The original coordinator had no auth layer and no HTTP support. FastMCP's `GoogleProvider` handles the full OAuth proxy flow out of the box.

Key additions:
- `GoogleProvider` OAuth — reads `ANALYTICS_MCP_OAUTH_CLIENT_ID`, `ANALYTICS_MCP_OAUTH_CLIENT_SECRET`, `ANALYTICS_MCP_BASE_URL` from environment
- When env vars are present → OAuth-protected HTTP server (Cloud Run mode)
- When env vars are absent → plain FastMCP instance (local stdio mode)
- Tool registration uses `mcp.tool(description=...)(fn)` pattern (compatible with FastMCP ≥ 3.3.x which removed the `description` argument from `add_tool()`)

---

### 3. `analytics_mcp/server.py`
**What:** Replaced hardcoded `asyncio` + `mcp.server.stdio` runner with FastMCP's transport-aware `mcp.run()`.  
**Why:** The original server always started in stdio mode. The new version checks for OAuth env vars and selects the transport automatically:
- `ANALYTICS_MCP_OAUTH_CLIENT_ID` + `ANALYTICS_MCP_OAUTH_CLIENT_SECRET` set → `streamable-http` on port 8080 (Cloud Run)
- Not set → `stdio` (local dev, unchanged behaviour)

---

### 4. `analytics_mcp/tools/client.py`
**What:** Added per-request OAuth token extraction before the Application Default Credentials (ADC) fallback.  
**Why:** Without this change, all Analytics API calls ran under the server's service account regardless of which user was signed in. With this change, each user's API calls use their own Google token — extracted from FastMCP's request context via `get_access_token()`.

```python
# New — tries user token first (Cloud Run / OAuth mode)
from fastmcp.server.dependencies import get_access_token
token_obj = get_access_token()
if token_obj and token_obj.token:
    return OAuthCredentials(token=token_obj.token)

# Falls back to ADC (local dev mode — unchanged behaviour)
return google.auth.default(scopes=[...])
```

---

### 5. `Dockerfile` _(new file — did not exist upstream)_
**What:** Added a Dockerfile for building the Cloud Run container image.  
**Why:** Google's repo had no Dockerfile. Required for `gcloud builds submit` and Cloud Run deployment.

```dockerfile
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY . .
RUN uv pip install --system .
EXPOSE 8080
CMD ["analytics-mcp"]
```

---

## Deployment

### Environment variables (Cloud Run)
| Variable | Description |
|----------|-------------|
| `ANALYTICS_MCP_OAUTH_CLIENT_ID` | Google OAuth 2.0 client ID |
| `ANALYTICS_MCP_OAUTH_CLIENT_SECRET` | Google OAuth 2.0 client secret |
| `ANALYTICS_MCP_BASE_URL` | Public URL of the Cloud Run service |

### Deploy command
```shell
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/og-infosec-dev/mcp-servers/analytics-mcp:latest \
  --project=og-infosec-dev .

gcloud run deploy analytics-mcp \
  --image us-central1-docker.pkg.dev/og-infosec-dev/mcp-servers/analytics-mcp:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances=1 \
  --project=og-infosec-dev \
  --set-env-vars="ANALYTICS_MCP_OAUTH_CLIENT_ID=...,ANALYTICS_MCP_OAUTH_CLIENT_SECRET=...,ANALYTICS_MCP_BASE_URL=https://analytics-mcp-228754886076.us-central1.run.app"
```

> `--min-instances=1` is required. Scale-to-zero wipes FastMCP's OAuth client registry, breaking reconnections.

### Local dev (no Cloud Run, no OAuth)
```shell
# Uses ADC — run this first if not already authenticated
gcloud auth application-default login

pip install -e .
analytics-mcp
```

---

## Merging upstream Google changes

See `UPSTREAM.md` for the full workflow.
