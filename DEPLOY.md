# Deploying google-analytics-mcp to Render

This guide covers running the MCP server over HTTP/SSE — the mode required
for hosted deployments. The original `analytics_mcp/server.py` (stdio) is
unchanged and still works for local Claude Desktop usage.

---

## How it works

`analytics_mcp/http_server.py` wraps the existing MCP server with:

| Path | Protocol | Purpose |
|------|----------|---------|
| `GET /health` | HTTP | Liveness probe (Render health-check) |
| `GET /tools` | HTTP | Lists all registered MCP tools — no credentials needed |
| `GET /sse` | SSE | MCP server→client event stream |
| `POST /messages/` | HTTP | MCP client→server messages |

Credentials are bootstrapped once at startup. The server reads
`GOOGLE_APPLICATION_CREDENTIALS_JSON` (a JSON string), writes it to a
temporary file, and sets `GOOGLE_APPLICATION_CREDENTIALS` so that the
standard `google.auth.default()` call in the existing tools code picks it up.

---

## Running locally

### 1. Install dependencies

```bash
cd google-analytics-mcp
pip install -e .
```

### 2. Set credentials

**Option A — JSON string in env var (mirrors how Render works):**
```bash
export GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat /path/to/your-service-account.json)"
```

**Option B — Standard ADC file path:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account.json
```

### 3. Start the server

```bash
python -m analytics_mcp.http_server
# Server starts on http://localhost:8000
```

### 4. Run smoke tests

```bash
./test.sh
# or explicitly:
BASE_URL=http://localhost:8000 ./test.sh
```

---

## Deploying to Render

### Option A — One-click via render.yaml (recommended)

The repo includes a `render.yaml` Blueprint file. Render will read it
automatically if you connect the repo.

1. Push this repo to GitHub / GitLab.
2. In the Render dashboard → **New > Blueprint** → connect your repo.
3. Render detects `render.yaml` and creates the `google-analytics-mcp` service.
4. Fill in the secret env vars (see next section).

### Option B — Manual service creation

1. Render dashboard → **New > Web Service**
2. Connect your repo.
3. Set:
   - **Runtime:** Python
   - **Build command:** `pip install -e .`
   - **Start command:** `python -m analytics_mcp.http_server`
   - **Health check path:** `/health`

---

## Setting environment variables on Render

Go to **Service > Environment** in the Render dashboard and add:

| Key | Value | Notes |
|-----|-------|-------|
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | _(paste full JSON)_ | Mark as **Secret** |
| `GA_PROPERTY_ID` | e.g. `123456789` | Optional default property |

> **How to get the service-account JSON:**
> Google Cloud Console → IAM & Admin → Service Accounts →
> select your account → Keys → Add Key → JSON.
> The downloaded file contents go in `GOOGLE_APPLICATION_CREDENTIALS_JSON`.
> The service account needs the **Viewer** role on your GA4 property.

---

## Running smoke tests against the live Render URL

Once deployed, note your Render service URL (e.g.
`https://google-analytics-mcp.onrender.com`) and run:

```bash
BASE_URL=https://google-analytics-mcp.onrender.com ./test.sh
```

Expected output (before real credentials are set):

```
1. GET /health     → PASS (200 OK)
2. GET /tools      → PASS (200 OK, 7 tools listed)
3. GET /sse        → PASS (SSE stream opens)
4. MCP initialize  → PASS (202 Accepted)
```

The MCP `initialize` handshake succeeds even without GA credentials — actual
GA tool calls will return an auth error until `GOOGLE_APPLICATION_CREDENTIALS_JSON`
is configured, which is expected.

---

## Connecting an MCP client to the live server

For Claude Desktop or any MCP client that supports HTTP/SSE transport,
point it at the `/sse` endpoint:

```json
{
  "mcpServers": {
    "google-analytics": {
      "url": "https://google-analytics-mcp.onrender.com/sse"
    }
  }
}
```

---

## Files added by this guide

| File | Purpose |
|------|---------|
| `analytics_mcp/http_server.py` | HTTP/SSE server entry point |
| `render.yaml` | Render Blueprint deployment config |
| `test.sh` | curl-based smoke-test script |
| `DEPLOY.md` | This file |
