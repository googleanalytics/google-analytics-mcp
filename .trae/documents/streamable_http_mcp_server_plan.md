# Plan: Add Streamable HTTP Transport with Refresh Token Auth to Google Analytics MCP Server

## 1. Repo Research Conclusion

### Current Architecture

The project is a Python MCP server for Google Analytics 4 (GA4) using the `mcp>=1.24.0` SDK's low-level `Server` class.

**Key files:**

* [server.py](file:///Users/peterwong/Documents/projects/phaeth/google-analytics-mcp/analytics_mcp/server.py) — STDIO-only entry point, wires `stdio_server()` streams to `coordinator.app.run()`

* [coordinator.py](file:///Users/peterwong/Documents/projects/phaeth/google-analytics-mcp/analytics_mcp/coordinator.py) — Singleton low-level `Server("Google Analytics MCP Server")`. Registers 9 ADK `FunctionTool`s. Decorated handlers: `@app.list_tools()`, `@app.call_tool(name, arguments)` (no context parameter today).

* [tools/client.py](file:///Users/peterwong/Documents/projects/phaeth/google-analytics-mcp/analytics_mcp/tools/client.py) — Global credential cache (`_CREDENTIALS`) + 4 factory fns:

  * `create_admin_api_client()` → `AnalyticsAdminServiceClient`

  * `create_data_api_client()` → `BetaAnalyticsDataClient`

  * `create_admin_alpha_api_client()` → `AnalyticsAdminServiceClient` (alpha)

  * `create_data_api_alpha_client()` → `AlphaAnalyticsDataClient`
    All obtain credentials from `google.auth.default(scopes=[analytics.readonly])`.

* Tool files (call factories module-level, no args):

  * [tools/admin/info.py](file:///Users/peterwong/Documents/projects/phaeth/google-analytics-mcp/analytics_mcp/tools/admin/info.py)

  * [tools/reporting/core.py](file:///Users/peterwong/Documents/projects/phaeth/google-analytics-mcp/analytics_mcp/tools/reporting/core.py)

  * [tools/reporting/realtime.py](file:///Users/peterwong/Documents/projects/phaeth/google-analytics-mcp/analytics_mcp/tools/reporting/realtime.py)

  * [tools/reporting/metadata.py](file:///Users/peterwong/Documents/projects/phaeth/google-analytics-mcp/analytics_mcp/tools/reporting/metadata.py)

  * [tools/reporting/funnel.py](file:///Users/peterwong/Documents/projects/phaeth/google-analytics-mcp/analytics_mcp/tools/reporting/funnel.py)

  * [tools/reporting/conversions.py](file:///Users/peterwong/Documents/projects/phaeth/google-analytics-mcp/analytics_mcp/tools/reporting/conversions.py)

* [pyproject.toml](file:///Users/peterwong/Documents/projects/phaeth/google-analytics-mcp/pyproject.toml) — Dependencies: `mcp>=1.24.0`, `google-auth~=2.40`, `httpx>=0.28.1`. Entry script: `analytics-mcp = analytics_mcp.server:run_server`.

### MCP SDK Streamable HTTP Capability

The installed low-level `Server` exposes `streamable_http_app(streamable_http_path="/mcp", ...) -> Starlette`, returning a ready-made Starlette ASGI app. It uses `StreamableHTTPSessionManager` and mounts the MCP endpoint at the configured path. The per-request `ServerRequestContext` carries `ctx.request` (the raw Starlette `Request`) whose `.headers` gives access to inbound HTTP headers. Transport-level headers are also set on `DispatchContext.transport.headers`.

### Google Auth Equivalent for "authorized\_user" Refresh Token

In Python (parallel to the Node.js pattern the user showed):

```python
from google.oauth2.credentials import Credentials as OAuth2UserCreds

credentials = OAuth2UserCreds.from_authorized_user_info(
    info={
        # "type": "authorized_user" NOT required by from_authorized_user_info();
        # the three keys below are the required minimum.
        "client_id":     os.environ["GOOGLE_ANALYTICS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_ANALYTICS_CLIENT_SECRET"],
        "refresh_token": <from HTTP header>,
    },
    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
)
```

Then pass `credentials=` to every `BetaAnalyticsDataClient(...)` / `AnalyticsAdminServiceClient(...)` constructor.

### Request-Scoped Credential Propagation Challenge

Tools call `create_*_api_client()` with zero arguments from inside `asyncio.to_thread(_sync_call)` workers. Thread workers need access to the request's refresh token.

**Chosen approach:** **`contextvars.ContextVar`** — Python's `contextvars` correctly propagates through `asyncio` tasks *and* `asyncio.to_thread()` workers in Py 3.9+. A `ServerMiddleware` reads the header, sets the ContextVar, and `create_*_api_client()` uses it to build user credentials before falling back to `google.auth.default()`.

***

## 2. Files and Modules to Be Edited

| # | File                            | Change Type                                                                                                                                                                                      |
| - | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 | `analytics_mcp/tools/client.py` | Modify — add ContextVar + refresh-token credential builder; add optional `credentials` parameter to client factory fns                                                                           |
| 2 | `analytics_mcp/coordinator.py`  | Modify — add middleware that extracts `x-ga-refresh-token` header and sets ContextVar; update `@app.call_tool` signature to receive `ServerRequestContext` (so middleware is active on the path) |
| 3 | `analytics_mcp/server.py`       | Modify — add `run_http_server_async()` + Starlette/uvicorn runner on `/mcp` path; keep STDIO runner as default                                                                                   |
| 4 | `pyproject.toml`                | Modify — add `uvicorn` (or `hypercorn`) dep and new `analytics-mcp-http` entry script                                                                                                            |

Optionally touched (no logic changes, only new imports): tool files under `tools/admin` and `tools/reporting` if client function signature changes — but we'll keep backward-compatible defaults so they are unaffected.

***

## 3. Steps for Modifications or New Features

### Step 3.1 — Add per-request refresh token context and credential builder (`client.py`)

1. **New imports:** `contextvars`, `os`, `google.oauth2.credentials`.
2. **Add a ContextVar:**

   ```python
   _refresh_token_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
       "ga_refresh_token", default=None
   )
   ```

   Expose module-level `set_refresh_token(token)` / `clear_refresh_token()` helpers for middleware use.
3. **Add** **`_build_authorized_user_credentials(refresh_token: str)`** **helper:**

   * Reads `GOOGLE_ANALYTICS_CLIENT_ID` and `GOOGLE_ANALYTICS_CLIENT_SECRET` from env.

   * Raises a clear error if either env var is missing (actionable error message).

   * Calls `google.oauth2.credentials.Credentials.from_authorized_user_info(info={"client_id","client_secret","refresh_token"}, scopes=[_READ_ONLY_ANALYTICS_SCOPE])`.
4. **Rework** **`_get_credentials()`** **to be request-aware:**

   * Remove the `global _CREDENTIALS` singleton path (or keep it as stdio/local fallback only).

   * New logic:

     1. `tok = _refresh_token_ctx.get()` → if set, return `_build_authorized_user_credentials(tok)` (no caching needed; google-oauth2 caches access token on the creds object).
     2. Otherwise use the existing `google.auth.default()` path cached via `_CREDENTIALS` for STDIO mode.

   * Keep `_client_lock` for the `google.auth.default()` leg only.
5. **Update the 4 client factory signatures** to keep them backward compatible with tool call sites:

   * `def create_admin_api_client(credentials=None) -> ...`

   * Same for `create_data_api_client`, `create_admin_alpha_api_client`, `create_data_api_alpha_client`.

   * Body: if `credentials` passed use it, else call `_get_credentials()` (which reads the ContextVar or falls back to ADC).

   * Tool call sites need **zero edits** because defaults apply.

### Step 3.2 — Middleware to pull refresh token from HTTP header (`coordinator.py`)

1. **New imports:** `ServerMiddleware` from `mcp.server.context`, `ServerRequestContext`, `set_refresh_token` / `clear_refresh_token` from `analytics_mcp.tools.client`.
2. **Header name:** Use `x-ga-refresh-token` (configurable via env if desired). Document that this header is the carrier for the Google OAuth refresh token.
3. **Middleware fn:**

   ```python
   async def refresh_token_middleware(ctx, call_next):
       tok = None
       req = ctx.request  # Starlette Request on streamable HTTP
       if req is not None and hasattr(req, "headers"):
           tok = req.headers.get("x-ga-refresh-token")
           # Also try canonical forms (case-insensitive via .get() already in Starlette)
       if tok:
           token = set_refresh_token(tok)
           try:
               return await call_next(ctx)
           finally:
               clear_refresh_token(token)
       else:
           return await call_next(ctx)
   ```
4. **Register middleware on the low-level Server:** append `refresh_token_middleware` to `app.middleware` after constructing `app = Server(...)`.
5. **Update** **`@app.call_tool`** **handler signature** so it takes `ctx: ServerRequestContext` explicitly (even if unused) — this guarantees the middleware chain is correctly wired for tool invocations on the low-level Server. Keep existing logic intact but ensure the signature change is compatible. If the decorator in the installed SDK doesn't support context arg transparently, fall back to register via `on_call_tool=` in the constructor.

### Step 3.3 — Streamable HTTP server entry point (`server.py`)

1. **New imports:** `os`, `uvicorn` (or hypercorn). Import `coordinator.app`.
2. **New coroutine** **`run_http_server_async(host, port, path="/mcp")`:**

   * Build ASGI app: `starlette_app = coordinator.app.streamable_http_app(streamable_http_path=path, host=host)`

   * Run under uvicorn programmatically via `uvicorn.Server(Config(...))` inside `anyio.run` / `asyncio.run`, matching the transport=streamable-http pattern from `MCPServer.run_streamable_http_async`.

   * Or simply: use the low-level Server's `run(transport="streamable-http", ...)` if the SDK version exports it on the low-level Server; the installed SDK exposes `streamable_http_app()` which can be fed into any ASGI runner.
3. **New sync** **`run_http_server()`** **wrapper** mirroring `run_server()`.
4. **Entry-point CLI switch:** allow running mode via env `ANALYTICS_MCP_TRANSPORT=stdio|http` or argv — if argv says `--http` or transport env is `http`, start HTTP server; otherwise STDIO (preserves backward compat).
5. Print startup banner with transport mode + endpoint URL on stderr for visibility.

### Step 3.4 — Project manifest updates (`pyproject.toml`)

1. Add an `[project.optional-dependencies]` extra `http` that includes `uvicorn>=0.30.0, starlette>=0.40.0` (starlette should already be a transitive dep of `mcp`, but pinning is safe).
2. New script entry:

   ```toml
   analytics-mcp-http = "analytics_mcp.server:run_http_server"
   ```

   Keep the existing `analytics-mcp` script bound to `run_server` (stdio by default, env-switchable).

### Step 3.5 — Validation / verification steps

1. **Syntax:** `python -m compileall analytics_mcp/` — should exit 0.
2. **Imports smoke test:** `python -c "from analytics_mcp.tools.client import create_data_api_client; from analytics_mcp import coordinator; from analytics_mcp.server import run_http_server"` — no exceptions.
3. **Credential builder unit test (no network):** set env `GOOGLE_ANALYTICS_CLIENT_ID=id`, `GOOGLE_ANALYTICS_CLIENT_SECRET=secret`, set refresh token ContextVar, call `_get_credentials()` and assert a `google.oauth2.credentials.Credentials` instance is returned with correct scopes.
4. **HTTP smoke run (no real GA4):** start `ANALYTICS_MCP_TRANSPORT=http analytics-mcp-http`, curl `POST /mcp` with a valid JSON-RPC initialize request; include dummy `x-ga-refresh-token` header and verify the middleware runs (add a debug log if needed). Expect the MCP handshake to proceed (tool calls will fail on actual Google APIs if token is invalid — that's expected).

***

## 4. Potential Dependencies or Considerations

* **`uvicorn`** **/** **`hypercorn`** **ASGI runner** — needed to actually serve the Starlette app. Added as an optional extra (`[http]`). Starlette itself is already a dependency of the `mcp` SDK, so runtime import is guaranteed.

* **Env vars required for HTTP mode:** `GOOGLE_ANALYTICS_CLIENT_ID`, `GOOGLE_ANALYTICS_CLIENT_SECRET`. The middleware path will error at credential-construction time if either is unset while a refresh-token header is present. Provide clear, actionable error text including the name of the missing variable.

* **Case-insensitive header lookup:** Starlette `Request.headers` already performs case-insensitive lookups for HTTP/1.x. Use header name exactly as documented (we pick `x-ga-refresh-token`) and note it in the code comment.

* **`asyncio.to_thread`** **+** **`contextvars`:** Python 3.9+ propagates contextvars into `to_thread` workers automatically. Project requires `>=3.10`, so this is guaranteed. Verified behavior on 3.10/3.11 by CPython release notes.

* **Global** **`_CREDENTIALS`** **+ request-scoped creds coexistence:** Keep the global cache only for the `google.auth.default()` fallback. Never cache per-request refresh-token-derived credentials in a module global — that would leak credentials across users. They live for the request only and are GC'd after.

* **Thread-safety of the ContextVar approach:** ContextVar values are per (async) task and per thread, so concurrent requests are fully isolated. No additional lock needed.

* **`tool.run_async(..., tool_context=None)`** **in coordinator:** Currently passes `None` — ADK `tool_context` isn't used here, so this remains unchanged; the ContextVar carries the credential info for the Google client libraries underneath.

* **Streamable HTTP transport stateless vs stateful:** Default `stateless_http=False` on the SDK — fine for an LLM-facing server. If high horizontal scale is needed later, enable stateless mode and re-test tool behavior (the tools themselves are stateless — no session state stored server-side — so enabling stateless should work without code changes).

* **`prevent_stdio_inheritance()`** **deadlock fix:** Still applicable to the `google.auth.default()` path. For the authorized-user credential path (direct OAuth2 refresh), no subprocess is spawned; only HTTP calls happen via `httpx`. The `prevent_stdio_inheritance` context manager can be removed from the new leg — keep it wrapped around the `google.auth.default()` call only.

* **Security — logging:** Never log the refresh token or client secret. Make sure error messages exclude the actual token values.

* **Backward compatibility:** The existing STDIO entry point (`analytics-mcp` script) must keep working 100% as before with Application Default Credentials. No env vars are required when running in STDIO mode.

***

## 5. Risk Handling

| Risk                                                                                                                                 | Likelihood | Impact   | Mitigation                                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------ | ---------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Installed `mcp` SDK version's `@app.call_tool` decorator doesn't accept the `ServerRequestContext` arg (older lowlevel API mismatch) | Medium     | High     | Fall back: use `on_call_tool=` kwarg in Server constructor instead of decorator. If middleware runs before dispatch, the ContextVar is already set, so even a no-context handler still observes correct credentials. The header extraction lives in middleware, not in the handler — handler signature is irrelevant for credential propagation. |
| Starlette `ctx.request` is `None` for legacy handshake on streamable HTTP                                                            | Medium     | Low      | Handshake messages (`initialize`) don't invoke tools, so no credentials are needed. Middleware only sets ContextVar when `ctx.request is not None and hasattr(req, "headers")`. Tool calls on the modern era always carry the request.                                                                                                           |
| Missing `GOOGLE_ANALYTICS_CLIENT_ID`/`CLIENT_SECRET` env vars at runtime when refresh token header is supplied                       | High       | Medium   | Throw `ValueError` from `_build_authorized_user_credentials` with the exact env var names. Wrap the call in the middleware (or at credential-build time) so the error is returned to the caller as an MCP tool error text, not an HTTP 500.                                                                                                      |
| Caching per-request credentials globally across users → data leak                                                                    | High       | Critical | Explicitly: never store ContextVar-built credentials on module globals. The `_CREDENTIALS` module cache is ONLY populated by the `google.auth.default()` fallback branch. Locks on `_client_lock` protect only the global fallback branch.                                                                                                       |
| `asyncio.to_thread` loses ContextVar on 3.10 edge cases                                                                              | Low        | High     | Explicitly verify by unit test or REPL: set var, schedule a to\_thread fn that reads it, assert equality. If failure observed, wrap thread entry via `contextvars.copy_context().run(...)` manually using `asyncio.get_event_loop().run_in_executor` with a context-bound callable.                                                              |
| `uvicorn` not installed when user runs `analytics-mcp-http`                                                                          | Medium     | Medium   | Catch `ModuleNotFoundError` for `uvicorn` at import time inside `run_http_server` and print a one-line install hint: `pip install "analytics-mcp[http]"`. Document in the script entry that the extra is required.                                                                                                                               |
| `host=0.0.0.0` on streamable\_http\_app disables DNS-rebinding protection built into SDK                                             | Low        | Medium   | Pass the actual `host` arg through to `streamable_http_app(host=host, transport_security=...)` so the SDK's auto-configuration stays engaged. Default host for HTTP mode to `127.0.0.1` (same as the SDK default); only bind `0.0.0.0` if the user explicitly passes it via env/CLI.                                                             |

