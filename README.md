Google Analytics MCP Server (Personal Fork — Kesig777)

Personalized fork of the Model Context Protocol (MCP) server for Google Analytics, maintained and configured for Mr. Kesegan Govender.12
👤 Account & Ownership Details
Account Owner: Mr. Kesegan Govender12
Primary Email: 1kesig777@gmail.com13
Secondary / GitHub Email: kesig777@gmail.com24
GitHub Username / Fork: Kesig7774
🔒 POPI Act & Privacy Compliance Statement

In compliance with the Protection of Personal Information Act (POPIA) of South Africa:
Scope Restriction: Authentication and API interactions utilize the read-only scope (https://www.googleapis.com/auth/analytics.readonly).3
Local Data Integrity: Personal Identifiable Information (PII), application default credentials (ADC), and OAuth tokens are maintained strictly within local environments (~/.gemini/settings.json) and are never committed to remote repositories.
Access Control: Account administration and API keys are strictly restricted to the authorized owner, Mr. Kesegan Govender.24
🛠️ Linked Google Cloud Projects & Analytics PropertiesGoogle Cloud Projects
Gemini API Project ID: gen-lang-client-017141752425
Restore Project ID: total-now-31290056
Google Analytics Property
Property Name: Master System's3
Property ID: 5388945873
🛠️ MCP Tools Summary

The server utilizes the Google Analytics Admin API and Google Analytics Data API to provide tools for LLM integration.Account & Property Information
get_account_summaries: Retrieves account and property details for 1kesig777@gmail.com.3
get_property_details: Returns property metadata for Property 538894587.3
list_google_ads_links: Lists linked Google Ads accounts (e.g., 354-729-1911).3
Reporting Tools
run_report: Runs standard Google Analytics Data API reports.
run_funnel_report: Generates funnel analysis reports.
get_custom_dimensions_and_metrics: Fetches custom metrics and dimensions.
run_realtime_report: Queries real-time traffic data.
🔧 Recovery & Setup Instructions1. Configure Python Environment

Install pipx for isolated tool execution:
pipx install analytics-mcp
2. Enable Google Cloud APIs

Ensure the following APIs are enabled in project gen-lang-client-0171417524:25
Google Analytics Admin API
Google Analytics Data API
3. Authenticate Application Default Credentials (ADC)

Run gcloud to re-establish your local OAuth credentials under 1kesig777@gmail.com:23
gcloud auth application-default login \
  --scopes https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform
Copy the credentials file path printed in the output (e.g., /home/user/.config/gcloud/application_default_credentials.json).4. Configure Gemini Client

Update or create your ~/.gemini/settings.json file:
{
  "mcpServers": {
    "analytics-mcp": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/PATH/TO/YOUR/application_default_credentials.json",
        "GOOGLE_PROJECT_ID": "gen-lang-client-0171417524"
      }
    }
  }
}
5. Configure Claude Code

To link the MCP server with Claude Code:
claude mcp add analytics-mcp \
  --scope user \
  -e "GOOGLE_APPLICATION_CREDENTIALS=/PATH/TO/YOUR/application_default_credentials.json" \
  -e "GOOGLE_PROJECT_ID=gen-lang-client-0171417524" \
  -- pipx run analytics-mcp
🥼 Verification & Testing

Launch Gemini CLI or Gemini Code Assist and verify tool connectivity using /mcp.

Sample Prompts:
"Show details for my Google Analytics Property 538894587."
"What are the top events recorded in my property over the last 30 days?"
"Check realtime active users on Master System's."
Next Steps & Recommendations
Verify Client File Path: Replace /PATH/TO/YOUR/application_default_credentials.json with the exact path on your machine where gcloud saved your ADC file.
Review Access: Confirm that 1kesig777@gmail.com has active read/edit access in the Google Analytics Console for Property ID 538894587.3
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
