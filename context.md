# Google Analytics MCP — Pulse Integrated

## What this project is

A fork of Google's official [google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp), wired up under the Pulse Integrated org. Pairs with the [Google Ads MCP](../googleads/) — together they feed the **Friday recap skill**, which ties ad spend to on-site behavior in plain-English client emails.

## Why we're building this

The Friday recap that summarizes Google Ads performance is incomplete without the on-site half of the story. Knowing a client spent $4,200 on Google Ads tells you nothing about whether those clicks actually did anything — did people land, browse, convert? The GA4 MCP closes that loop.

## What's in this folder

- [`analytics_mcp/`](analytics_mcp/) — the MCP server itself (unchanged from upstream so we can `git pull upstream main` cleanly)
  - [`tools/admin/`](analytics_mcp/tools/admin/) — account/property discovery: `get_account_summaries`, `get_property_details`, `list_google_ads_links` (the critical one for client mapping), `list_property_annotations`
  - [`tools/reporting/`](analytics_mcp/tools/reporting/) — reports: `run_report`, `run_realtime_report`, `run_funnel_report`, `run_conversions_report`, `get_custom_dimensions_and_metrics`
- [`README.md`](README.md) — upstream README + Pulse teammate onboarding section
- [`setup_credentials.py`](setup_credentials.py) — interactive wrapper around `gcloud auth application-default login` with the right scopes
- [`pyproject.toml`](pyproject.toml) — Python 3.10+, managed by `uv`

## How the pieces connect

```
Claude Code (stdio)
    │
    ▼
analytics-mcp  ──reads──▶  ~/.config/gcloud/application_default_credentials.json
    │
    ▼
GA4 Admin API + GA4 Data API
    │
    ▼
get_account_summaries → [{account: "...", properties: [{name: "...", id: "..."}]}]
list_google_ads_links(property_id) → [{customer_id: "1234567890", ...}]
run_report(property_id, dimensions, metrics, date_ranges) → table of values
```

## Auth model — different from Ads, on purpose

The Google Ads MCP used a hand-rolled `google-ads.yaml` with OAuth refresh tokens. This MCP uses Google's **Application Default Credentials (ADC)** flow instead — the standard library reads from `~/.config/gcloud/application_default_credentials.json` and refreshes the token automatically.

Why the difference:
- The upstream GA MCP is built on Google's ADC convention. Diverging means rewriting Google's code, fighting the merge train every time upstream updates.
- ADC tokens refresh longer than the 7-day testing-mode OAuth quirk on the Ads side. Published consent screen → indefinite life.

Reuses the same OAuth client we created for Ads — same GCP project, same client ID. Just needs the `analytics.readonly` and `cloud-platform` scopes added.

## Status

| Phase | Status |
|---|---|
| Repo forked into pulse-integrated | ✅ |
| `uv` deps installed | ✅ |
| `gcloud` CLI installed | ✅ |
| `setup_credentials.py` helper written | ✅ |
| MCP registered in `~/.claude.json` | ✅ |
| ADC generated (Luke or Sean runs `setup_credentials.py`) | ⏳ |
| Enable GA Admin + Data APIs in GCP project | ⏳ — needs Luke (1-click each) |
| Restart Claude Code | ⏳ |
| Smoke test (`get_account_summaries`) | ⏳ |
| Update `/friday-ads-recap` skill to layer GA4 data | ⏳ |
| Pulse teammate onboarding section in README | ⏳ |

## Friday recap integration

Once both MCPs are live, the recap skill will add a **"What happened on-site this week"** section to each per-client email:

- Paid sessions from `google/cpc` (this week vs last week)
- Conversion rate of paid traffic
- Total conversions attributed to `google/cpc`
- Top 3 landing pages for paid traffic
- Average session duration / engagement rate

`list_google_ads_links(property_id)` returns the Google Ads customer IDs linked to each GA4 property — solving the Ads ↔ GA4 client mapping problem without us building it by hand.

## Naming

- **GA4** = Google Analytics 4 (the only currently supported GA version)
- **ADC** = Application Default Credentials, Google's local-machine credential file
- **Property** = a GA4 site/app (analogous to a Google Ads account but flat — no MCC layer)
- **`property_id`** = a numeric ID like `123456789` (no leading "properties/" in the MCP calls)

## Tools used by the recap skill (from this MCP)

- `get_account_summaries` — discover available properties
- `list_google_ads_links` — map Ads customer IDs to GA4 properties
- `run_report` — pull all the metrics for the email

## Working with Claude on this project

Same defaults as the Google Ads MCP and `~/Projects/wealth/CLAUDE.md`:
- Plain English; outputs and visual behavior over diffs
- Make reasonable calls and flag assumptions instead of blocking
- End-of-turn summary: 1–2 sentences, what changed and what's next

Future sessions: read this file first to orient. Update in place when status changes or design decisions land.
