#!/usr/bin/env python3
"""Script to manually refresh Google OAuth token and update config with expiry.

This script is useful if you need to manually refresh your OAuth token,
though the MCP server will automatically refresh tokens as needed.

Usage:
    python refresh_and_update_config.py /path/to/config.json
"""

import json
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


def refresh_and_update_config(config_path: str) -> bool:
    """Refresh the Google OAuth access token and update config file.

    Args:
        config_path: Path to the Google Analytics config JSON file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Load current config
        with open(config_path, 'r') as f:
            config = json.load(f)

        oauth_config = config.get('googleOAuthCredentials', {})
        tokens = config.get('googleAnalyticsTokens', {})

        if not oauth_config or not tokens:
            print("❌ Config file missing OAuth credentials or tokens", file=sys.stderr)
            return False

        # Create credentials
        credentials = Credentials(
            token=tokens.get('accessToken'),
            refresh_token=tokens.get('refreshToken'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=oauth_config.get('clientId'),
            client_secret=oauth_config.get('clientSecret'),
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )

        # Refresh the token
        credentials.refresh(Request())

        # Update config with new token and expiry
        config['googleAnalyticsTokens']['accessToken'] = credentials.token
        if credentials.expiry:
            config['googleAnalyticsTokens']['expiresAt'] = int(credentials.expiry.timestamp())

        # Save updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✅ Token refreshed and saved to {config_path}")
        return True

    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error refreshing token: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python refresh_and_update_config.py <config_path>", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  python refresh_and_update_config.py /path/to/google-analytics-config.json", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]
    success = refresh_and_update_config(config_path)
    sys.exit(0 if success else 1)