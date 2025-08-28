#!/usr/bin/env python3
"""Test script to verify OAuth credentials are working."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analytics_mcp.coordinator import set_config_path
from analytics_mcp.tools.utils import _create_credentials, create_data_api_client

def test_oauth_credentials(config_path: str):
    print("Testing OAuth credentials...")
    
    try:
        # Set the config path
        set_config_path(config_path)
        
        # Test credential creation
        credentials = _create_credentials()
        print(f"✓ Credentials created successfully")
        print(f"  - Has access token: {bool(credentials.token)}")
        print(f"  - Has refresh token: {bool(credentials.refresh_token)}")
        print(f"  - Client ID: {credentials.client_id[:20]}..." if credentials.client_id else "  - Client ID: None")
        
        # Test API client creation
        client = create_data_api_client()
        print(f"✓ Analytics Data API client created successfully")
        
        print("\n✅ OAuth configuration is working correctly!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"   Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "google-analytics-config (4).json"
    test_oauth_credentials(config_path)