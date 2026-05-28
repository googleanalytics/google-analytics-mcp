# Google Analytics MCP Server (Experimental)

[![PyPI version](https://img.shields.io/pypi/v/analytics-mcp.svg)](https://pypi.org/project/analytics-mcp/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub branch check runs](https://img.shields.io/github/check-runs/googleanalytics/google-analytics-mcp/main)](https://github.com/googleanalytics/google-analytics-mcp/actions?query=branch%3Amain++)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/analytics-mcp)](https://pypi.org/project/analytics-mcp/)
[![GitHub stars](https://img.shields.io/github/stars/googleanalytics/google-analytics-mcp?style=social)](https://github.com/googleanalytics/google-analytics-mcp/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/googleanalytics/google-analytics-mcp?style=social)](https://github.com/googleanalytics/google-analytics-mcp/network/members)
[![YouTube Video Views](https://img.shields.io/youtube/views/PT4wGPxWiRQ)](https://www.youtube.com/watch?v=PT4wGPxWiRQ)

This repo contains the source code for running a local
[MCP](https://modelcontextprotocol.io) server that interacts with APIs for
[Google Analytics](https://support.google.com/analytics).

Join the discussion and ask questions in the
[🤖-analytics-mcp channel](https://discord.com/channels/971845904002871346/1398002598665257060)
on Discord.

## Tools 🛠️

The server uses the
[Google Analytics Admin API](https://developers.google.com/analytics/devguides/config/admin/v1)
and
[Google Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1)
to provide several
[Tools](https://modelcontextprotocol.io/docs/concepts/tools) for use with LLMs.

### Retrieve account and property information 🟠

- `get_account_summaries`: Retrieves information about the user's Google
  Analytics accounts and properties.
- `get_property_details`: Returns details about a property.
- `list_google_ads_links`: Returns a list of links to Google Ads accounts for
  a property.

### Run core reports 📙

- `run_report`: Runs a Google Analytics report using the Data API.
- `run_funnel_report`: Runs a Google Analytics funnel report using the Data API.
- `get_custom_dimensions_and_metrics`: Retrieves the custom dimensions and
  metrics for a specific property.

### Run realtime reports ⏳

- `run_realtime_report`: Runs a Google Analytics realtime report using the
  Data API.

## Setup instructions 🔧

✨ Watch the [Google Analytics MCP Setup
Tutorial](https://youtu.be/nS8HLdwmVlY) on YouTube for a step-by-step
walkthrough of these instructions.

[![Watch the video](https://img.youtube.com/vi/nS8HLdwmVlY/mqdefault.jpg)](https://www.youtube.com/watch?v=nS8HLdwmVlY)

Setup involves the following steps:

1.  Configure Python.
1.  Configure credentials for Google Analytics.
1.  Configure Gemini.

### Configure Python 🐍

[Install pipx](https://pipx.pypa.io/stable/#install-pipx).

### Enable APIs in your project ✅

[Follow the instructions](https://support.google.com/googleapi/answer/6158841)
to enable the following APIs in your Google Cloud project:

- [Google Analytics Admin API](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com)
- [Google Analytics Data API](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com)

### Configure credentials 🔑

Configure your [Application Default Credentials
(ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc).
Make sure the credentials are for a user with access to your Google Analytics
accounts or properties.

Credentials must include the Google Analytics read-only scope:

```
https://www.googleapis.com/auth/analytics.readonly
```

Check out
[Manage OAuth Clients](https://support.google.com/cloud/answer/15549257)
for how to create an OAuth client.

Here are some sample `gcloud` commands you might find useful:

- Set up ADC using user credentials and an OAuth desktop or web client after
  downloading the client JSON to `YOUR_CLIENT_JSON_FILE`.

  ```shell
  gcloud auth application-default login \
    --scopes https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform \
    --client-id-file=YOUR_CLIENT_JSON_FILE
  ```

- Set up ADC using service account impersonation.

  ```shell
  gcloud auth application-default login \
    --impersonate-service-account=SERVICE_ACCOUNT_EMAIL \
    --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform
  ```

When the `gcloud auth application-default` command completes, copy the
`PATH_TO_CREDENTIALS_JSON` file location printed to the console in the
following message. You'll need this for the next step!

```
Credentials saved to file: [PATH_TO_CREDENTIALS_JSON]
```

### Configure Gemini

1.  Install [Gemini
    CLI](https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/installation.md)
    or [Gemini Code
    Assist](https://marketplace.visualstudio.com/items?itemName=Google.geminicodeassist).

1.  Create or edit the file at `~/.gemini/settings.json`, adding your server
    to the `mcpServers` list.

    Replace `PATH_TO_CREDENTIALS_JSON` with the path you copied in the previous
    step.

    We also recommend that you add a `GOOGLE_CLOUD_PROJECT` attribute to the
    `env` object. Replace `YOUR_PROJECT_ID` in the following example with the
    [project ID](https://support.google.com/googleapi/answer/7014113) of your
    Google Cloud project.

    ```json
    {
      "mcpServers": {
        "analytics-mcp": {
          "command": "pipx",
          "args": ["run", "analytics-mcp"],
          "env": {
            "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_CREDENTIALS_JSON",
            "GOOGLE_PROJECT_ID": "YOUR_PROJECT_ID"
          }
        }
      }
    }
    ```

## Try it out 🥼

Launch Gemini Code Assist or Gemini CLI and type `/mcp`. You should see
`analytics-mcp` listed in the results.

Here are some sample prompts to get you started:

- Ask what the server can do:

  ```
  what can the analytics-mcp server do?
  ```

- Ask about a Google Analytics property

  ```
  Give me details about my Google Analytics property with 'xyz' in the name
  ```

- Prompt for analysis:

  ```
  what are the most popular events in my Google Analytics property in the last 180 days?
  ```

- Ask about signed-in users:

  ```
  were most of my users in the last 6 months logged in?
  ```

- Ask about property configuration:

  ```
  what are the custom dimensions and custom metrics in my property?
  ```

---

## Setup for Pulse teammates

> Pulse-specific instructions. Pairs with the Pulse fork of [google-ads-mcp](https://github.com/pulse-integrated/google-ads-mcp). Same `~/Projects/mcp/` parent folder convention. If a teammate has already set up the Google Ads MCP on this Mac, most of the prerequisites are already done.

### Prerequisites

- **Claude Code installed** (not the regular Claude desktop app — different installer)
- **Homebrew installed**
- **A user account with access** to the GA4 properties you want to query (Pulse defaults to Sean's identity, since he has property-level access across our managed accounts)

### Steps

1. **Install gcloud and uv** if you don't have them:

   ```bash
   brew install --cask google-cloud-sdk
   brew install uv
   ```

2. **Clone the repo** anywhere:

   ```bash
   git clone https://github.com/pulse-integrated/google-analytics-mcp.git
   cd google-analytics-mcp
   ```

3. **Install dependencies:**

   ```bash
   uv sync
   ```

4. **Get the OAuth client JSON.** If Pulse already created an OAuth client for the Google Ads MCP, you can reuse it — same GCP project, same client ID and secret work for both APIs. Otherwise:

   - https://console.cloud.google.com/apis/credentials
   - Create OAuth client → Application type: **Desktop app**
   - Download the JSON file. Don't commit it.

5. **Enable the two GA APIs** in the GCP project (one-time, only needs to be done by one teammate):

   - https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com
   - https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com

6. **Run the credential setup helper:**

   ```bash
   uv run setup_credentials.py
   ```

   It'll ask for the OAuth client JSON path, open a browser, and walk you through sign-in. Sign in with the Google account that has GA4 access. When done, the script prints the path to your ADC file (typically `~/.config/gcloud/application_default_credentials.json`).

7. **Register the MCP with Claude Code.** Open `~/.claude.json` and add the entry to your top-level `mcpServers` block (merge alongside any existing entries like `google-ads`):

   ```json
   {
     "mcpServers": {
       "google-analytics": {
         "type": "stdio",
         "command": "/opt/homebrew/bin/uv",
         "args": [
           "--directory",
           "/absolute/path/to/google-analytics-mcp",
           "run",
           "analytics-mcp"
         ],
         "env": {
           "GOOGLE_APPLICATION_CREDENTIALS": "/Users/YOU/.config/gcloud/application_default_credentials.json"
         }
       }
     }
   }
   ```

8. **Restart Claude Code** so the new MCP loads.

9. **Smoke test** from a terminal in the repo root:

   ```bash
   GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json" \
     uv run python -c "from google.analytics.admin import AnalyticsAdminServiceClient; \
     c = AnalyticsAdminServiceClient(); \
     print([(a.display_name, a.account) for a in c.list_account_summaries()])"
   ```

   You should see a list of `(account_name, account_id)` pairs. That confirms the MCP can reach the GA4 Admin API. If it errors, the message usually points at the fix (often a missing scope on the OAuth flow).

### Trade-offs worth knowing

- **Shared identity:** if all teammates use the same ADC file (e.g. Sean's), reports will look like Sean made them in audit logs. For read-only reporting this is fine.
- **API enablement is GCP-project-wide:** enabling the two GA APIs in the project covers every teammate using that OAuth client. Only one person needs to do step 5.
- **No mutation tools:** this MCP is read-only. We're not building goals, audiences, or admin mutations into it for now.

---

## Contributing ✨

Contributions welcome! See the [Contributing Guide](CONTRIBUTING.md).
