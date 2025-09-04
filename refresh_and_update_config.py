#!/usr/bin/env python3
"""Script to refresh Google OAuth token and update config with expiry."""

import json
import time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def refresh_and_update_config():
    """Refresh the Google OAuth access token and update config."""
    config_path = '/Users/mkotsollaris/projects/google-analytics-mcp/google-analytics-config (4).json'
    
    try:
        # Load current config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        oauth_config = config.get('googleOAuthCredentials', {})
        tokens = config.get('googleAnalyticsTokens', {})
        
        print("🔄 Refreshing OAuth token...")
        print(f"Current access token: {tokens.get('accessToken', 'None')[:50]}...")
        
        # Create credentials
        credentials = Credentials(
            token=tokens.get('accessToken'),
            refresh_token=tokens.get('refreshToken'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=oauth_config.get('clientId'),
            client_secret=oauth_config.get('clientSecret'),
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        
        # Force refresh the token
        print("🔄 Refreshing token...")
        credentials.refresh(Request())
        
        # Calculate expiry time (1 hour from now - typical OAuth token expiry)
        expires_at = int(time.time()) + 3600
        
        # Update config with new token and expiry
        config['googleAnalyticsTokens']['accessToken'] = credentials.token
        config['googleAnalyticsTokens']['expiresAt'] = expires_at
        
        # Save updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✅ Token refreshed successfully!")
        print(f"New access token: {credentials.token[:50]}...")
        print(f"Expires at: {expires_at} ({time.ctime(expires_at)})")
        print("Config file updated.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = refresh_and_update_config()
    if success:
        print("\n🎉 Token refresh complete! You can now restart your MCP server.")
    else:
        print("\n💥 Token refresh failed. Check the error messages above.")