#!/usr/bin/env python3
"""
Xero OAuth Debug Tool
This script helps debug Xero OAuth 403 errors
"""

import requests
from setup_wizard import get_configured_credentials

def test_xero_config():
    print("🔍 Xero OAuth Debug Tool")
    print("=" * 50)
    
    # Get credentials
    try:
        creds = get_configured_credentials()
        client_id = creds.get('XERO_CLIENT_ID')
        client_secret = creds.get('XERO_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            print("❌ Error: Missing Xero credentials")
            return
            
        print(f"✅ Found credentials")
        print(f"   Client ID: {client_id[:10]}...")
        print(f"   Client Secret: {client_secret[:10]}...")
        
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")
        return
    
    # Test 1: Check if client_id is valid format
    print(f"\n🔍 Test 1: Client ID Format")
    if len(client_id) < 30:
        print(f"⚠️  Warning: Client ID seems short ({len(client_id)} chars)")
    else:
        print(f"✅ Client ID length OK ({len(client_id)} chars)")
    
    # Test 2: Try to get Xero's OpenID configuration
    print(f"\n🔍 Test 2: Xero OpenID Configuration")
    try:
        response = requests.get('https://identity.xero.com/.well-known/openid-configuration', timeout=10)
        if response.status_code == 200:
            config = response.json()
            print(f"✅ OpenID config accessible")
            print(f"   Authorization endpoint: {config.get('authorization_endpoint', 'Not found')}")
        else:
            print(f"⚠️  OpenID config returned {response.status_code}")
    except Exception as e:
        print(f"❌ Error accessing OpenID config: {e}")
    
    # Test 3: Create test OAuth URL
    print(f"\n🔍 Test 3: OAuth URL Generation")
    
    redirect_uri = "https://localhost:8000/callback"
    scope = "offline_access openid profile email accounting.settings accounting.transactions accounting.contacts"
    
    oauth_url = (
        f"https://login.xero.com/identity/connect/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope.replace(' ', '%20')}"
        f"&state=test123"
    )
    
    print(f"✅ Generated OAuth URL:")
    print(f"   {oauth_url}")
    
    # Test 4: Check URL accessibility
    print(f"\n🔍 Test 4: Test OAuth URL (HEAD request)")
    try:
        # Just test if the authorization endpoint is reachable
        auth_endpoint = "https://login.xero.com/identity/connect/authorize"
        response = requests.head(auth_endpoint, timeout=10)
        print(f"✅ Authorization endpoint reachable (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Authorization endpoint not reachable: {e}")
    
    print(f"\n" + "=" * 50)
    print(f"🔧 Debugging Steps:")
    print(f"1. Copy the OAuth URL above and paste it in your browser")
    print(f"2. If you get 403, check your Xero app settings:")
    print(f"   - Redirect URI must be exactly: {redirect_uri}")
    print(f"   - App must be Published (not Draft)")
    print(f"   - All required scopes must be enabled")
    print(f"3. If you get 400, the client_id might be wrong")
    print(f"4. If it works, the issue is with Flask OAuth integration")

if __name__ == "__main__":
    test_xero_config()