# Google Analytics MCP Server (Experimental)

[![PyPI version](https://img.shields.io/pypi/v/analytics-mcp.svg)](https://pypi.org/project/analytics-mcp/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub branch check runs](https://img.shields.io/github/check-runs/googleanalytics/google-analytics-mcp/main)](https://github.com/googleanalytics/google-analytics-mcp/actions?query=branch%3Amain++)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/analytics-mcp)](https://pypi.org/project/analytics-mcp/)
[![GitHub stars](https://img.shields.io/github/stars/googleanalytics/google-analytics-mcp?style=social)](https://github.com/googleanalytics/google-analytics-mcp/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/googleanalytics/google-analytics-mcp?style=social)](https://github.com/googleanalytics/google-analytics-mcp/network/members)
[![YouTube Video Views](https://img.shields.io/youtube/views/PT4wGPxWiRQ)](https://www.youtube.com/watch?v=PT4wGPxWiRQ)

This repo contains the source code for a
[MCP](https://modelcontextprotocol.io) server that interacts with APIs for
[Google Analytics](https://support.google.com/analytics).

The server supports two deployment modes:

- **Local (stdio)** — run as a subprocess by Gemini CLI, Claude Desktop, or
  any MCP client. Uses Application Default Credentials. No extra infrastructure
  needed.
- **Remote (HTTP + OAuth)** — deploy to
  [Google Cloud Run](https://cloud.google.com/run) and connect from web-based
  clients such as [claude.ai](https://claude.ai). Users authenticate via OAuth
  2.0; no credentials need to be shared with the server operator.

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

Choose the mode that fits your use case:

- [Local setup (stdio)](#local-setup-stdio) — simplest, runs on your machine
- [Remote deployment (Cloud Run + OAuth)](#remote-deployment-cloud-run--oauth) — accessible from claude.ai and other web clients

---

### Local setup (stdio)

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

---

### Remote deployment (Cloud Run + OAuth)

Deploy the server to Cloud Run so web-based MCP clients such as
[claude.ai](https://claude.ai) can connect to it. Each user authenticates with
their own Google account via OAuth 2.0 — no credentials need to be configured
on the server.

#### 1. Enable APIs ✅

[Enable](https://support.google.com/googleapi/answer/6158841) the same two APIs
as for local setup:

- [Google Analytics Admin API](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com)
- [Google Analytics Data API](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com)

#### 2. Create an OAuth 2.0 client 🔑

1. Open [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
   in the Google Cloud Console.
1. Click **Create credentials → OAuth client ID**.
1. Choose **Web application** as the application type.
1. Under **Authorized redirect URIs**, add a placeholder for now — you will
   update it after deploying:

   ```text
   https://YOUR_SERVICE_URL/auth/callback
   ```

1. Click **Create** and note the **Client ID** and **Client secret**.

#### 3. Build and push the image with Cloud Build 🐳

[Cloud Build](https://cloud.google.com/build) builds and pushes the image
without requiring Docker locally. Substitute your Artifact Registry repository
path:

```shell
gcloud builds submit \
  --tag REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO/google-analytics-mcp:latest .
```

#### 4. First deploy — get the service URL ☁️

Deploy without `ANALYTICS_MCP_BASE_URL` first so Cloud Run can assign the
service URL:

```shell
gcloud run deploy YOUR_SERVICE_NAME \
  --image REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO/google-analytics-mcp:latest \
  --platform managed \
  --region YOUR_REGION \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_PROJECT_ID=YOUR_PROJECT_ID,\
ANALYTICS_MCP_OAUTH_CLIENT_ID=YOUR_OAUTH_CLIENT_ID,\
ANALYTICS_MCP_OAUTH_CLIENT_SECRET=YOUR_OAUTH_CLIENT_SECRET,\
FASTMCP_HOST=0.0.0.0"
```

Note the **Service URL** printed at the end of the output, e.g.
`https://YOUR_SERVICE_NAME-1234567890.REGION.run.app`.

#### 5. Update OAuth redirect URI and redeploy ☁️

1. Return to your OAuth client in the
   [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   and replace the placeholder redirect URI with:

   ```text
   https://YOUR_SERVICE_URL/auth/callback
   ```

1. Redeploy with `ANALYTICS_MCP_BASE_URL` set to the service URL:

   ```shell
   gcloud run deploy YOUR_SERVICE_NAME \
     --image REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO/google-analytics-mcp:latest \
     --platform managed \
     --region YOUR_REGION \
     --allow-unauthenticated \
     --set-env-vars="GOOGLE_PROJECT_ID=YOUR_PROJECT_ID,\
   ANALYTICS_MCP_OAUTH_CLIENT_ID=YOUR_OAUTH_CLIENT_ID,\
   ANALYTICS_MCP_OAUTH_CLIENT_SECRET=YOUR_OAUTH_CLIENT_SECRET,\
   ANALYTICS_MCP_BASE_URL=https://YOUR_SERVICE_URL,\
   FASTMCP_HOST=0.0.0.0"
   ```

#### 6. Connect from claude.ai 🤖

1. Open [claude.ai](https://claude.ai) and go to **Settings → Integrations**.
1. Add a new integration with the URL:

   ```text
   https://YOUR_SERVICE_URL/mcp
   ```

1. Authorize with your Google account when prompted.

#### Environment variable reference

| Variable | Required | Description |
| --- | --- | --- |
| `ANALYTICS_MCP_OAUTH_CLIENT_ID` | Yes (HTTP mode) | OAuth 2.0 client ID |
| `ANALYTICS_MCP_OAUTH_CLIENT_SECRET` | Yes (HTTP mode) | OAuth 2.0 client secret |
| `ANALYTICS_MCP_BASE_URL` | Yes (HTTP mode) | Public URL of the deployed service |
| `FASTMCP_HOST` | Cloud Run | Set to `0.0.0.0` to accept external connections |
| `PORT` | Cloud Run | Port to listen on (default: `8080`, auto-set by Cloud Run) |

---

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

## Contributing ✨

Contributions welcome! See the [Contributing Guide](CONTRIBUTING.md).
