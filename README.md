# Google Analytics MCP Server

This repo contains the source code for running a local
[MCP](https://modelcontextprotocol.io) server that interacts with APIs for
[Google Analytics](https://support.google.com/analytics).

## Setup instructions

Setup involves the following steps:

1.  Configure Python and install dependencies.
1.  Configure credentials for Google Analytics.
1.  Configure Gemini.

### Configure Python

Navigate to the `analytics-mcp` directory, then complete the following steps.

1.  Create a Python virtual environment in the `env` directory.

    ```shell
    python3 -m venv .venv
    ```

1.  Activate the virtual environment.

    ```shell
    source .venv/bin/activate
    ```

1.  Setup the project and its dependencies.

    ```shell
    pip install .
    ```


### Configure credentials

Configure your [Application Default Credentials
(ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc).
Make sure the credentials are for a user with access to your Google Analytics
accounts or properties.

Credentials must include a Google Analytics scope. We recommend using the
read-only scope:

```
https://www.googleapis.com/auth/analytics.readonly
```

Here are some sample `gcloud` commands you might find useful:

* Set up ADC using user credentials and an OAuth web client after
  downloading the client JSON to `YOUR_WEB_CLIENT_JSON_FILE`.

  ```shell
  gcloud auth application-default login \
    --scopes https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform \
    --client-id-file=YOUR_WEB_CLIENT_JSON_FILE
  ```

* Set up ADC using service account impersonation.

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

1.  Get a Gemini API key and set the `GEMINI_API_KEY` environment variable.

    ```shell
    export GEMINI_API_KEY=YOUR_GEMINI_API_KEY
    ```

1.  Create or edit the file at `~/.gemini/settings.json`, adding your server
    to the `mcpServers` list.

    Replace `PATH_TO_SERVER` with the complete path to the directory where you
    cloned this repo.

    ```
    {
      "mcpServers": {
        "analytics-mcp": {
          "command": "PATH_TO_SERVER/env/bin/python",
          "args": [
            "PATH_TO_SERVER/server.py"
          ],
          "env": {
            "MCP_DEBUG": "true"
          }
        }
      },
      "selectedAuthType": "gemini-api-key",
      "fileFiltering": {
        "enableRecursiveFileSearch": false
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

    ```
    {
      "mcpServers": {
        "analytics-mcp": {
          "command": "PATH_TO_SERVER/.venv/bin/python",
          "args": [
            "PATH_TO_SERVER/server.py"
          ],
          "env": {
            "MCP_DEBUG": "true",
            "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_ADC_JSON"
          }
        }
      },
      "selectedAuthType": "gemini-api-key",
      "fileFiltering": {
        "enableRecursiveFileSearch": false
      }
    }
    ```

## Try it out

Launch Gemini Code Assist or Gemini CLI and type `/mcp`. You should see
`analytics-mcp` listed in the results.

Here are some sample prompts to get you started:

* Ask what the server can do:

  ```
  what can the analytics-mcp server do?
  ```

* Ask about a Google Analytics property

  ```
  Give me details about my Google Analytics property with 'xyz' in the name
  ```

* Prompt for analysis:

  ```
  what are the most popular events in my Google Analytics property in the last 180 days?
  ```

* Ask about signed-in users:

  ```
  were most of my users in the last 6 months logged in?
  ```

* Ask about property configuration:

  ```
  what are the custom dimensions and custom metrics in my property?
  ```
