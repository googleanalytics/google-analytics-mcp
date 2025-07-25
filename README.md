# Google Analytics MCP Server (Experimental)

This repo contains the source code for running a local
[MCP](https://modelcontextprotocol.io) server that interacts with APIs for
[Google Analytics](https://support.google.com/analytics).

## Tools :hammer_and_wrench:

The server uses the
[Google Analytics Admin API](https://developers.google.com/analytics/devguides/config/admin/v1)
and
[Google Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1)
to provide several
[Tools](https://modelcontextprotocol.io/docs/concepts/tools) for use with LLMs.

### Retrieve account and property information :orange_circle:

- `get_account_summaries`: Retrieves information about the user's Google
  Analytics accounts and properties.
- `get_property_details`: Returns details about a property.
- `list_google_ads_links`: Returns a list of links to Google Ads accounts for
  a property.

### Run core reports :orange_book:

- `run_report`: Runs a Google Analytics report using the Data API.
- `get_custom_dimensions_and_metrics`: Retrieves the custom dimensions and
  metrics for a specific property.

### Run realtime reports :hourglass_flowing_sand:

- `run_realtime_report`: Runs a Google Analytics realtime report using the
  Data API.

## Setup instructions

Setup involves the following steps:

1.  Configure Python.
1.  Configure credentials for Google Analytics.
1.  Configure Gemini.

### Configure Python :snake:

[Install pipx](https://pipx.pypa.io/stable/#install-pipx).

### Enable APIs in your project :white_check_mark:

[Follow the instructions](https://support.google.com/googleapi/answer/6158841)
to enable the following APIs in your Google Cloud project:

* [Google Analytics Admin API](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com)
* [Google Analytics Data API](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com)

### Configure credentials :key:

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

### Configure Gemini

1.  Install [Gemini
    CLI](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/index.md)
    or [Gemini Code
    Assist](https://marketplace.visualstudio.com/items?itemName=Google.geminicodeassist)

1.  Create or edit the file at `~/.gemini/settings.json`, adding your server
    to the `mcpServers` list.

    ```json
    {
      "mcpServers": {
        "analytics-mcp": {
          "command": "pipx",
          "args": [
            "run",
            "--spec",
            "git+https://github.com/googleanalytics/google-analytics-mcp.git",
            "google-analytics-mcp"
          ]
        }
      }
    }
    ```

1.  **Optional:** Configure the `GOOGLE_APPLICATION_CREDENTIALS` environment
    variable in Gemini settings. You may want to do this if you always want to
    use a specific set of credentials, regardless of which Application Default
    Credentials are selected in your current environment.

    In `~/.gemini/settings.json`, add a `GOOGLE_APPLICATION_CREDENTIALS`
    attribute to the `env` object. Replace `PATH_TO_ADC_JSON` in the following
    example with the full path to the ADC JSON file you always want to use for
    your MCP server.

    ```json
    {
      "mcpServers": {
        "analytics-mcp": {
          "command": "pipx",
          "args": [
            "run",
            "--spec",
            "git+https://github.com/googleanalytics/google-analytics-mcp.git",
            "google-analytics-mcp"
          ],
          "env": {
            "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_ADC_JSON"
          }
        }
      }
    }
    ```

## Try it out :lab_coat:

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

## Contributing

Contributions welcome! See the [Contributing Guide](CONTRIBUTING.md).
