"""Interactive helper to set up Google Analytics MCP credentials.

This wraps `gcloud auth application-default login` with the right scopes,
writes the OAuth client JSON to the repo root (gitignored), and prints the
path you'll plug into `~/.claude.json` as GOOGLE_APPLICATION_CREDENTIALS.

Two flows:

  (1) Bring your own OAuth client JSON
      You've already created a "Desktop app" OAuth client in Google Cloud
      Console and downloaded the client JSON. Drop the path in when asked
      and we use it for the browser sign-in.

  (2) Use existing ADC
      You've already run `gcloud auth application-default login` previously
      (maybe for another tool). Skip the auth flow and just point the MCP
      at the existing ADC file.

Run from the repo root:
    uv run setup_credentials.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/cloud-platform",
]
DEFAULT_ADC_PATH = (
    Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
)


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def main() -> None:
    print("\n=== Google Analytics MCP credential setup ===\n")

    if not shutil.which("gcloud"):
        print("ERROR: gcloud CLI not found on PATH.")
        print("  Install with: brew install --cask google-cloud-sdk")
        sys.exit(1)

    if DEFAULT_ADC_PATH.is_file():
        print(f"Found existing ADC file at: {DEFAULT_ADC_PATH}")
        reuse = ask("Reuse it without re-authenticating? (y/N)", "n").lower()
        if reuse.startswith("y"):
            _verify_and_finish(DEFAULT_ADC_PATH)
            return

    print()
    print("Step 1/3 — OAuth client JSON")
    print("  Create at: https://console.cloud.google.com/apis/credentials")
    print("  Type: 'Desktop app' (or 'Web app' with http://localhost redirect)")
    print("  Then click 'Download JSON' and paste the file path below.")
    print()
    print("  If you already have the OAuth client we set up for Google Ads,")
    print("  you can reuse that JSON here — same project, same client works.")
    client_path = ask("Path to OAuth client JSON")
    if not client_path or not Path(client_path).is_file():
        print(f"ERROR: not a file: {client_path}")
        sys.exit(1)

    print()
    print("Step 2/3 — Enable required APIs in the Google Cloud project")
    print("  Open: https://console.cloud.google.com/apis/library")
    print("  Search for and enable BOTH:")
    print("    - Google Analytics Data API")
    print("    - Google Analytics Admin API")
    input("  Press Enter when both are enabled...")

    print()
    print("Step 3/3 — Browser authorization")
    print("  A browser window will open. Sign in with the Google account that")
    print("  has access to your GA4 properties, then click 'Allow'.\n")
    input("  Press Enter to launch the browser...")

    cmd = [
        "gcloud",
        "auth",
        "application-default",
        "login",
        f"--scopes={','.join(SCOPES)}",
        f"--client-id-file={client_path}",
    ]
    print(f"  Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("ERROR: gcloud auth failed.")
        sys.exit(1)

    if not DEFAULT_ADC_PATH.is_file():
        print(f"ERROR: ADC file not found at {DEFAULT_ADC_PATH} after auth.")
        sys.exit(1)

    _verify_and_finish(DEFAULT_ADC_PATH)


def _verify_and_finish(adc_path: Path) -> None:
    try:
        data = json.loads(adc_path.read_text())
    except Exception as exc:
        print(f"ERROR: couldn't parse {adc_path}: {exc}")
        sys.exit(1)

    if "refresh_token" not in data and data.get("type") != "service_account":
        print("WARNING: no refresh_token in the ADC file. The MCP may need")
        print("re-auth often. Re-run this script if queries start failing.")

    print()
    print("✓ ADC ready.")
    print(f"  Path: {adc_path}")
    print()
    print("Plug this into ~/.claude.json under env.GOOGLE_APPLICATION_CREDENTIALS:")
    print(f'  "GOOGLE_APPLICATION_CREDENTIALS": "{adc_path}"')
    print()
    print("Smoke test:")
    print(
        '  GOOGLE_APPLICATION_CREDENTIALS="'
        + str(adc_path)
        + '" uv run python -c "from google.analytics.admin import '
        'AnalyticsAdminServiceClient; c = AnalyticsAdminServiceClient(); '
        'print([a.account for a in c.list_account_summaries()])"'
    )


if __name__ == "__main__":
    main()
