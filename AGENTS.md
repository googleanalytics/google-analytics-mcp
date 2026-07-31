# AGENTS.md — maintenance guide

Guidance for humans and AI coding agents working on **this fork** of
`googleanalytics/google-analytics-mcp`. Read this before making changes.

## What this fork adds

Upstream is a **local (stdio)** MCP server for Google Analytics. This fork adds
an optional **remote, OAuth 2.1-protected HTTP transport**: a self-hostable
server where each user signs in with their **own Google account**
(`analytics.readonly`) — no service accounts. It is built on the MCP Python
SDK's OAuth framework (`mcp.server.auth`), federates to Google, persists
sessions in SQLite, and is deployed as a container behind a reverse proxy.

All of this lives in **new, additive files**. The upstream server and its tools
are unchanged.

## Hard rules (do not break these)

1. **Public repository — no identifiable information.** Never commit real
   domains, emails, hostnames, company/owner names, secrets, or tokens. Use
   only RFC-reserved placeholders in code/tests/docs (`example.com`,
   `example.org`, `<your-host>`). Deployment-specific values (allowlist
   domains, client IDs/secrets, base URL) are supplied **only** via environment
   variables set in the deployment (e.g. a Portainer stack), never in the repo.
2. **Stay rebaseable on upstream.** Google actively develops upstream. Do **not**
   edit upstream files (`analytics_mcp/server.py`, `analytics_mcp/coordinator.py`,
   `analytics_mcp/tools/**`, `pyproject.toml` tool definitions, `README.md`
   content). Put all fork behavior in new files. The one seam into upstream is a
   runtime monkeypatch (see "Credential seam"), not a source edit. Periodically:
   `git fetch upstream && git rebase upstream/main`.
3. **Never commit to `main`.** Always work on a branch, open a PR, and merge the
   PR — even for docs.
4. **TDD.** Write a failing test first, then the implementation. Keep the suite
   green.

## Repository layout

Upstream (treat as read-only — do not edit):
- `analytics_mcp/server.py` — stdio entry point.
- `analytics_mcp/coordinator.py` — the singleton MCP `Server` and tool registry.
- `analytics_mcp/tools/**` — the GA4 tools and the GA API client (`client.py`).

This fork's additions (`analytics_mcp/remote/`):
- `config.py` — env → `Config`. Allowlist/secret values come only from env.
- `store.py` — `TokenStore`: SQLite persistence (clients, tokens↔Google tokens,
  auth codes, federation states), WAL mode, survives restarts.
- `credentials.py` — request-scoped Google credentials `ContextVar` + the
  monkeypatch of `client._get_credentials` (the credential seam).
- `google.py` — Google federation: auth URL (`access_type=offline`,
  `prompt=consent`), code exchange, userinfo, `Credentials` builder.
- `allowlist.py` — email / hosted-domain (`hd`) allowlist; open mode + warning
  when unset.
- `ratelimit.py` — per-IP token bucket + body-size limit middleware.
- `provider.py` — `GoogleMCPProvider(OAuthAuthorizationServerProvider)`.
- `app.py` — Starlette app wiring (SDK auth routes + `/oauth/callback` +
  authenticated `/mcp` + `/health`) and `main()` (uvicorn). Console script
  `analytics-mcp-http`.

Tests: `tests/remote/*_test.py`. Deployment: `Dockerfile`,
`docker-compose.portainer.yml`, `.env.example`, `DEPLOY.md`.

## How the remote OAuth flow works

1. The MCP client (e.g. Claude) hits `/mcp` unauthenticated → `401` with a
   `WWW-Authenticate` pointing at the protected-resource metadata.
2. It discovers the auth server, registers via Dynamic Client Registration
   (`/register`), and starts PKCE at `/authorize`.
3. `provider.authorize()` stores a federation `state` and redirects the user to
   **Google's** consent screen (`redirect_uri=<BASE_URL>/oauth/callback`).
4. `/oauth/callback` exchanges the Google code, fetches userinfo, and
   **enforces the allowlist before issuing anything** (non-allowlisted → 403).
   It then mints our authorization code and redirects back to the MCP client.
5. The client exchanges our code at `/token` (PKCE verified by the SDK) for our
   access + refresh tokens, mapped to the stored Google tokens.
6. On each `/mcp` request, the bearer middleware validates the token; `app.py`
   loads the user's Google credentials and binds them for the request.

### Credential seam (the only link into upstream)

Upstream tools call `analytics_mcp.tools.client._get_credentials()` (ADC).
`remote/credentials.py` **monkeypatches** that function to return the current
request's `google.oauth2.credentials.Credentials` from a `contextvars.ContextVar`
when set, else fall back to ADC. `contextvars` are task-local, so concurrent
requests never share credentials. This is why upstream tool code needs no edits.

## Develop & test

The project uses `uv` with a local `.venv`.

```bash
uv run python -m pytest tests/ -q          # full suite
uv run python -m pytest tests/remote -q    # fork tests only
```

Run the remote server locally (needs a Google OAuth client whose redirect URI is
`http://localhost:8080/oauth/callback`):

```bash
docker build -t ga4-mcp:dev .
docker run --rm -p 8080:8080 --env-file .env -v ga_data:/data ga4-mcp:dev
```

## Deployment

See [`DEPLOY.md`](DEPLOY.md). Key operational gotchas already encoded there:

- **Reverse proxy / scheme:** `main()` enables uvicorn `proxy_headers`; the proxy
  must forward `X-Forwarded-Proto` and `TRUST_PROXY=true` must be set, or
  redirects downgrade to `http://`.
- **`/data` volume:** the image pre-creates `/data` owned by the non-root user so
  a fresh named volume is writable (else the SQLite store fails to open).
- **SSE:** disable proxy buffering for streaming responses.
- **`/mcp` 307:** `/mcp` redirects to `/mcp/`; clients follow it (keep https).

## Conventions

- Match the surrounding code style; keep each `remote/` module single-purpose.
- No new runtime dependency unless necessary; prefer stdlib and what `mcp` /
  `google-auth` / `httpx` already provide.
- Document operational caveats in `DEPLOY.md`, architecture/maintenance here.

## Issue tracking

GitHub issues are the authoritative tracker for individual work items. Work with them
continuously, without being asked.

- **One issue per deferred item**, assigned to a milestone where the repo uses them. If
  it isn't an issue, it isn't tracked — never keep a parallel list in a doc or in memory.
- **Write issues to stand alone**: the evidence, the ground truth you verified, and the
  concrete fix. A future reader won't have the conversation.
- **Never defer silently.** If work is dropped, narrowed, or postponed, open an issue in
  the same turn and say so.
- **Close issues in the PR that resolves them** (`Closes #N`), not afterwards.
- **Check for staleness proactively**, especially issues predating recent decisions.
  Prefer a **dated update comment** over rewriting the body — the original framing plus
  an update is more useful than a silently edited issue.
- **Docs ship with the work.** Any doc whose claims a PR changes is updated in that PR,
  not a follow-up. Verify doc claims against ground truth (code, data, computed output) —
  never against another doc, since both can be stale.
