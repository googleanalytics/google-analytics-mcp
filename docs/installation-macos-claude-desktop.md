# Installing Google Analytics MCP on macOS with Claude Desktop

This guide walks through installing the Google Analytics MCP server on macOS
and connecting it to Claude Desktop. It covers common issues not addressed in
the main README, including quota project configuration, API enablement, and
troubleshooting authentication errors.

**Tested with:**
- macOS Sequoia 15.x
- Claude Desktop (latest)
- Python 3.10–3.13
- Google Cloud SDK 533+

---

## Prerequisites

Before you start, make sure you have:

- A Google account with access to at least one Google Analytics 4 property
- Admin access to a Google Cloud project (you can
  [create one for free](https://console.cloud.google.com/projectcreate))
- [Homebrew](https://brew.sh/) installed (recommended for installing Python
  and gcloud)

---

## Step 1 — Install Python and pipx

The MCP server requires Python 3.10 or later. Check your current version:

```shell
python3 --version
```

If you need to install or upgrade Python:

```shell
brew install python@3.13
```

Install [pipx](https://pipx.pypa.io/stable/), which runs the MCP server in
an isolated environment:

```shell
brew install pipx
pipx ensurepath
```

Restart your terminal after running `pipx ensurepath`, then verify:

```shell
pipx --version
```

---

## Step 2 — Install the Google Cloud SDK

Install the `gcloud` CLI if you don't have it:

```shell
brew install --cask google-cloud-sdk
```

Verify the installation:

```shell
gcloud --version
```

---

## Step 3 — Create or select a Google Cloud project

The MCP server uses Application Default Credentials (ADC) tied to a Google
Cloud project. You need a project to configure OAuth credentials.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Select an existing project or click **New Project** to create one.
   A free project works fine — you won't incur charges for GA4 API calls
   within standard quota limits.
3. Copy your **Project ID** (visible in the project selector dropdown). You'll
   need it in Step 6.

---

## Step 4 — Enable required APIs

Enable the two APIs the MCP server uses:

```shell
gcloud services enable analyticsdata.googleapis.com \
  analyticsadmin.googleapis.com \
  --project=YOUR_PROJECT_ID
```

Or enable them in the console:
- [Google Analytics Data API](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com)
- [Google Analytics Admin API](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com)

---

## Step 5 — Create an OAuth 2.0 Desktop client

The MCP server authenticates as you (the user), not as a service account.
This requires an OAuth 2.0 Desktop client.

1. Go to **APIs & Services → Credentials** in the
   [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Click **+ Create Credentials → OAuth client ID**.
3. If prompted to configure the OAuth consent screen first:
   - Choose **External** (works for personal Google accounts).
   - Fill in App name (e.g. "GA4 MCP") and your email for support and
     developer contact fields.
   - Click **Save and Continue** through the Scopes and Test users screens.
   - You do **not** need to add scopes here — they are passed at login time.
4. Back on Create credentials, select **Desktop app** as the Application type.
5. Click **Create**, then **Download JSON**.
6. Save the downloaded file somewhere memorable, e.g.:
   ```
   ~/keys/ga4-mcp-oauth-client.json
   ```

---

## Step 6 — Configure Application Default Credentials

Run the following command, replacing the path with where you saved your client
JSON:

```shell
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform \
  --client-id-file=~/keys/ga4-mcp-oauth-client.json
```

Your browser will open and ask you to sign in with a Google account that has
access to your GA4 properties. After approving, you'll see:

```
Credentials saved to file: [/Users/YOU/.config/gcloud/application_default_credentials.json]
```

Copy the full path shown in brackets — you'll need it in Step 8.

### Set the quota project

If you see a warning like `Quota project is not set`, run:

```shell
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

This links API quota to your project, which is required for the GA4 APIs to
work correctly even on the free tier.

---

## Step 7 — Verify the credentials work

Test that the credentials can reach the GA4 API:

```shell
pipx run analytics-mcp
```

If successful, you'll see output like:

```
Starting MCP Stdio Server: Google Analytics MCP Server
```

Press `Ctrl+C` to stop. If you see an auth error, check the
[Troubleshooting](#troubleshooting) section below.

---

## Step 8 — Configure Claude Desktop

1. Open Claude Desktop.
2. Go to **Claude menu → Settings → Developer → Edit Config**.
   This opens `~/Library/Application Support/Claude/claude_desktop_config.json`
   in your default editor.
3. Add the `analytics-mcp` server to the `mcpServers` object. Replace the
   placeholder paths with your actual values:

```json
{
  "mcpServers": {
    "analytics-mcp": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/Users/YOU/.config/gcloud/application_default_credentials.json",
        "GOOGLE_CLOUD_PROJECT": "YOUR_PROJECT_ID"
      }
    }
  }
}
```

> **Tip:** Use the full absolute path for `GOOGLE_APPLICATION_CREDENTIALS`.
> The `~` shorthand does not expand in Claude Desktop's environment.

4. Save the file and **fully quit and relaunch Claude Desktop**
   (not just close the window — use ⌘Q or Claude menu → Quit).

---

## Step 9 — Verify the connection

After relaunching Claude Desktop:

1. Start a new conversation.
2. Click the **tools icon** (hammer icon) in the chat input area. You should
   see `analytics-mcp` listed with its tools.

Try a test prompt:

```
What Google Analytics accounts and properties do I have access to?
```

Claude should call `get_account_summaries` and return a list of your GA4
properties.

---

## Troubleshooting

### "Could not automatically determine credentials"

The `GOOGLE_APPLICATION_CREDENTIALS` path is wrong or the file doesn't exist.
Verify with:

```shell
cat "/Users/YOU/.config/gcloud/application_default_credentials.json"
```

If the file is missing, re-run the `gcloud auth application-default login`
command from Step 6.

### "Request had insufficient authentication scopes"

The credentials were created without the Analytics scope. Re-run:

```shell
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform \
  --client-id-file=~/keys/ga4-mcp-oauth-client.json
```

### "Quota exceeded" or "RESOURCE_EXHAUSTED"

Set the quota project:

```shell
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

Then update `GOOGLE_CLOUD_PROJECT` in `claude_desktop_config.json` to match.

### "analytics-mcp not found" in Claude Desktop tools

Claude Desktop didn't pick up the config change. Make sure you fully quit
(⌘Q) and relaunched — closing the window is not enough. Also check that the
JSON in `claude_desktop_config.json` is valid (no trailing commas, correct
bracket nesting).

### Server listed in tools but calls fail silently

Open the Claude Desktop logs:

```shell
tail -f ~/Library/Logs/Claude/mcp*.log
```

This shows the raw MCP server output and any Python errors.

### "Cannot perform dynamic registration without issuer" (Gemini CLI only)

This error occurs in Gemini CLI when using `/mcp auth`. It is not an issue
with Claude Desktop. Use the `GOOGLE_APPLICATION_CREDENTIALS` environment
variable approach instead of the interactive `/mcp auth` flow.

---

## Keeping the server up to date

The server is published to PyPI. `pipx run` always fetches the latest version.
If you want to pin to a specific version:

```json
"args": ["run", "analytics-mcp==0.2.0"]
```

Check the [releases page](https://github.com/googleanalytics/google-analytics-mcp/releases)
for the latest version.
