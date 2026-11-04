# Multi-Tenant Google Analytics Agent Example (End-User OAuth)

This example shows how a third-party developer can host `analytics-mcp` in
**multi-tenant HTTP mode** and build an agent where **end users sign in with
their own Google account in the browser**—never touching bearer tokens,
`gcloud`, or JSON keyfiles.

It also shows how to combine **Google Analytics MCP** alongside other MCP
servers (such as a CRM or e-commerce server) in a single agent.

---

## Architecture Overview

1. **`analytics-mcp --transport http --stateless-http`**:
   - Runs as a shared HTTP service (e.g., on Cloud Run, GKE, or locally on
     port `8080`).
   - Strictly requires a per-request `Authorization: Bearer <token>` header on
     tool calls and isolates each tenant's credentials using Python's
     `contextvars.ContextVar` (never falling back to server-side Application
     Default Credentials).
2. **End-User OAuth Flow**:
   - **Option A — Agent Framework OAuth (Google ADK)**: Configured per
     `McpToolset` in [`agent.py`](./agent.py). When an end user asks a question
     that triggers a Google Analytics tool, ADK automatically renders a
     **"Sign in"** button in the chat UI, completes the Google OAuth 2.0
     browser flow, and passes the user's token to `analytics-mcp`. This mode is
     stateless and horizontally scalable across multiple instances.
   - **Option B — Native MCP OAuth 2.1 Server (`--oauth`)**: For MCP clients
     that rely on the MCP server itself to perform OAuth 2.1 (such as Claude
     Desktop, Cursor, or MCP Inspector), passing `--oauth` enables a built-in
     OAuth 2.1 Authorization Server on `analytics-mcp` that proxies to Google
     OAuth 2.0 (`accounts.google.com`).

---

## Step 1: Create a Google OAuth 2.0 Client

1. Open the
   [Google Cloud Console Credentials page](https://console.cloud.google.com/apis/credentials)
   in a project with the **Google Analytics Admin API** and **Google Analytics
   Data API** enabled.
2. Click **Create Credentials > OAuth client ID** and select **Web
   application**.
3. Under **Authorized redirect URIs**, add:
   - For Google ADK (`adk web`): `http://localhost:8000/dev-ui` (or your
     production ADK callback URL)
   - For Native MCP OAuth (`analytics-mcp --transport http --oauth`):
     `http://127.0.0.1:8080/oauth/callback` (or
     `https://<your-mcp-domain>/oauth/callback`)
4. Copy the **Client ID** and **Client Secret**:
   ```bash
   export GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
   export GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"
   ```

---

## Step 2: Start `analytics-mcp` in Multi-Tenant HTTP Mode

Run `analytics-mcp` on port `8080` in stateless HTTP mode using `pipx`:

```bash
pipx run analytics-mcp \
  --transport http --stateless-http --host 0.0.0.0 --port 8080
```

*(Add `--allow-write` or `ANALYTICS_MCP_ALLOW_WRITE=true` if you also want to
expose write tools like `create_property_annotation`.)*

Or build and deploy using the repository's root [`Dockerfile`](../../Dockerfile)
(e.g. `gcloud run deploy analytics-mcp --source .` on Google Cloud Run—see the
root [`README.md`](../../README.md#deploy-with-docker--google-cloud-run-) for
full Cloud Run and Secret Manager commands).

> **Note**: In `--transport http` mode, the server does **not** use
> `GOOGLE_APPLICATION_CREDENTIALS` or host-level service accounts—it strictly
> requires each request's OAuth Bearer token.

---

## Step 3: Run the Multi-Tenant ADK Agent

In a second terminal, navigate to the `examples/` directory, export your OAuth
and Gemini credentials, point `ANALYTICS_MCP_URL` at your running MCP server,
and launch the ADK web UI:

```bash
cd examples
export GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"
export ANALYTICS_MCP_URL="http://127.0.0.1:8080/mcp"
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
export GOOGLE_API_KEY="your-gemini-api-key"

adk web
```

1. Open `http://localhost:8000` in your browser and select
   **`multi_tenant_adk_agent`**.
2. Ask: *"What Google Analytics accounts and properties do I have access to?"*
3. The chat UI will display a **Sign in** button. Click it to approve access
   with your Google account in the browser popup.
4. Once approved, the agent automatically executes `get_account_summaries`
   using your OAuth token!

---

## Combining Google Analytics MCP with Other MCP Servers

Because OAuth is configured on each `McpToolset` instance independently, a
third-party developer can combine multiple MCP servers from different providers
in the same agent without any token collisions:

```python
from fastapi.openapi.models import (
    OAuth2,
    OAuthFlowAuthorizationCode,
    OAuthFlows,
)
from google.adk.agents import LlmAgent
from google.adk.auth.auth_credential import (
    AuthCredential,
    AuthCredentialTypes,
    OAuth2Auth,
)
from google.adk.tools.mcp_tool import (
    McpToolset,
    StreamableHTTPConnectionParams,
)
from multi_tenant_adk_agent.agent import create_google_analytics_toolset

# 1. Google Analytics MCP (authenticates with Google OAuth)
ga_mcp = create_google_analytics_toolset(
    mcp_url="https://ga-mcp.example.com/mcp",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
)

# 2. Another MCP server (authenticates with its own OAuth provider)
crm_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://crm-mcp.example.com/mcp"
    ),
    auth_scheme=OAuth2(
        flows=OAuthFlows(
            authorizationCode=OAuthFlowAuthorizationCode(
                authorizationUrl="https://auth.example.com/oauth/authorize",
                tokenUrl="https://auth.example.com/oauth/token",
                scopes={"crm.read": "Read your CRM data"},
            )
        )
    ),
    auth_credential=AuthCredential(
        auth_type=AuthCredentialTypes.OAUTH2,
        oauth2=OAuth2Auth(
            client_id=CRM_CLIENT_ID,
            client_secret=CRM_CLIENT_SECRET,
        ),
    ),
)

# Single agent with both MCP toolsets:
# ADK prompts the user to sign in to each provider separately and routes each
# user token exclusively to its respective MCP server.
analyst_agent = LlmAgent(
    model="gemini-3.8-flash",
    name="cross_platform_analyst",
    instruction="Analyze performance across Google Analytics and CRM data.",
    tools=[ga_mcp, crm_mcp],
)
```

---

## Alternative: Native MCP OAuth 2.1 Mode (`--oauth`)

If your users connect directly to `analytics-mcp` from an MCP client that
supports the **MCP OAuth 2.1 specification** (such as Claude Desktop, Cursor,
or MCP Inspector) rather than through an ADK web app, start `analytics-mcp`
with `--oauth`:

```bash
export GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"
export ANALYTICS_MCP_ISSUER_URL="https://analytics-mcp.yourdomain.com"

pipx run analytics-mcp \
  --transport http --stateless-http --oauth --host 0.0.0.0 --port 8080
```

When the MCP client connects to `http://127.0.0.1:8080/mcp` (or
`https://analytics-mcp.yourdomain.com/mcp`), `analytics-mcp` serves
`/.well-known/oauth-protected-resource/mcp` and
`/.well-known/oauth-authorization-server`, registers the client dynamically at
`/register`, and automatically opens the end user's browser to Google's OAuth
consent screen.

> **Deployment Note**: The built-in `--oauth` provider stores dynamic client
> registrations, pending authorization state, and refresh tokens in process
> memory. Deploy `--oauth` as a single instance (or with sticky sessions) and
> note that server restarts require clients to re-authenticate. For fully
> stateless horizontal scaling across replicas, use Option A (external OAuth
> via ADK + `--transport http --stateless-http`).

> **Local Testing Tip**: When testing `--oauth` locally without
> `ANALYTICS_MCP_ISSUER_URL`, configure your MCP client URL with
> `http://127.0.0.1:8080/mcp` (not `http://localhost:8080/mcp`) so it matches
> the server's default OAuth Protected Resource metadata URL per RFC 9728.
