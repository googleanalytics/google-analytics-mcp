# Google Analytics MCP Extension

This extension provides tools to interact with Google Analytics 4 (GA4) properties.
It uses the Google Analytics Admin API and Data API.

## Available Tools

- `get_account_summaries`: List accounts and properties.
- `get_property_details`: Get details for a specific property.
- `list_google_ads_links`: List linked Google Ads accounts.
- `run_report`: Execute core reporting queries.
- `get_custom_dimensions_and_metrics`: List custom definitions for a property.
- `run_realtime_report`: Execute realtime reporting queries.

## Usage Guidelines

- Always try to find the `property_id` first using `get_account_summaries` if the user doesn't provide it.
- When running reports, refer to the official GA4 schema for dimensions and metrics names.
- For complex filters, follow the hints provided in the tool descriptions.
