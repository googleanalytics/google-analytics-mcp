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

* [Google Analytics Admin API](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com)
* [Google Analytics Data API](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com)

### Configure credentials 🔑

This server supports two authentication methods:

#### Option 1: OAuth2 with Access/Refresh Tokens (Recommended for integrations)

This method is ideal for applications that need programmatic access without user interaction. You'll need to create a configuration file with your OAuth credentials and tokens.

Create a JSON configuration file with your OAuth credentials and tokens:

```json
{
  "googleOAuthCredentials": {
    "clientId": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "clientSecret": "YOUR_CLIENT_SECRET",
    "redirectUri": "http://localhost:3000/api/integration/google/callback"
  },
  "googleAnalyticsTokens": {
    "accessToken": "YOUR_ACCESS_TOKEN",
    "refreshToken": "YOUR_REFRESH_TOKEN",
    "expiresAt": 1756420934
  }
}
```

To obtain OAuth credentials:

1. [Create OAuth credentials](https://support.google.com/cloud/answer/15549257) in the Google Cloud Console
2. Download the client configuration JSON file
3. Use the OAuth flow to obtain access and refresh tokens with the Google Analytics read-only scope:
   ```
   https://www.googleapis.com/auth/analytics.readonly
   ```

#### Option 2: Application Default Credentials (ADC)

This is the standard Google Cloud authentication method. If no OAuth config file is provided, the server will automatically use [Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc).

To set up ADC:

```shell
gcloud auth application-default login \
  --scopes https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform \
  --client-id-file=YOUR_CLIENT_JSON_FILE
```

### Configure Claude Desktop

1.  Install Claude Desktop or use Claude Code.

2.  Create or edit the Claude Desktop configuration file at `~/.config/claude/claude_desktop_config.json` (Linux/Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows).

3.  Add the analytics-mcp server to the `mcpServers` list:

    **With OAuth2 Config File:**
    ```json
    {
      "mcpServers": {
        "analytics-mcp": {
          "command": "python",
          "args": [
            "-m", "analytics_mcp.server",
            "--config", "/path/to/your/google-analytics-config.json"
          ]
        }
      }
    }
    ```

    **With Application Default Credentials:**
    ```json
    {
      "mcpServers": {
        "analytics-mcp": {
          "command": "python",
          "args": ["-m", "analytics_mcp.server"]
        }
      }
    }
    ```

### Configure Gemini (Alternative)

For Gemini CLI users:

1.  Install [Gemini CLI](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/index.md) or [Gemini Code Assist](https://marketplace.visualstudio.com/items?itemName=Google.geminicodeassist).

2.  Create or edit the file at `~/.gemini/settings.json`:

    **With OAuth2 Config File:**
    ```json
    {
      "mcpServers": {
        "analytics-mcp": {
          "command": "pipx",
          "args": [
            "run",
            "analytics-mcp",
            "--config", "/path/to/your/google-analytics-config.json"
          ]
        }
      }
    }
    ```

    **With Application Default Credentials:**
    ```json
    {
      "mcpServers": {
        "analytics-mcp": {
          "command": "pipx",
          "args": ["run", "analytics-mcp"]
        }
      }
    }
    ```

## Installation 📦

### Install from PyPI (Recommended)

```bash
pip install analytics-mcp
```

### Install from source

```bash
git clone https://github.com/googleanalytics/google-analytics-mcp.git
cd google-analytics-mcp
pip install -r requirements.txt
pip install -e .
```

## Try it out 🥼

Launch Claude Desktop or Gemini and the server should automatically connect. For Claude Desktop, you can verify the connection in the MCP settings.

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
