#!/usr/bin/env python3
"""Script to manually refresh Google OAuth access token."""

import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def refresh_token():
    """Refresh the Google OAuth access token."""
    try:
        # Load current config
        config_path = 'google-analytics-config (4).json'
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        oauth_config = config.get('googleOAuthCredentials', {})
        tokens = config.get('googleAnalyticsTokens', {})
        
        print("Current tokens:")
        print(f"  Access token: {tokens.get('accessToken', 'None')[:50]}...")
        print(f"  Refresh token: {tokens.get('refreshToken', 'None')[:50]}...")
        print(f"  Client ID: {oauth_config.get('clientId', 'None')[:50]}...")
        
        # Create credentials
        credentials = Credentials(
            token=tokens.get('accessToken'),
            refresh_token=tokens.get('refreshToken'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=oauth_config.get('clientId'),
            client_secret=oauth_config.get('clientSecret'),
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        
        print(f"\nToken expired: {credentials.expired}")
        
        if credentials.refresh_token:
            print("Attempting to refresh token...")
            credentials.refresh(Request())
            
            # Update config with new token
            config['googleAnalyticsTokens']['accessToken'] = credentials.token
            
            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print("✅ Token refreshed successfully!")
            print(f"New access token: {credentials.token[:50]}...")
            print("Config file updated.")
            
        else:
            print("❌ No refresh token available. Need to re-authenticate.")
            
    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    refresh_token()
