#!/usr/bin/env python3
"""
Test script to verify Xero configuration
"""
import os
import sys
from setup_wizard import SetupWizardAPI

def main():
    print("🔍 Testing Xero Configuration")
    print("=" * 50)
    
    # Load setup wizard API
    api = SetupWizardAPI()
    
    # Get current configuration
    config = api.get_configuration_status()
    print(f"Setup Status: {config}")
    
    # Load credentials directly
    try:
        from setup_wizard import get_configured_credentials
        creds = get_configured_credentials()
        
        print(f"\nCredentials found:")
        print(f"- Has XERO_CLIENT_ID: {bool(creds.get('XERO_CLIENT_ID'))}")
        print(f"- Has XERO_CLIENT_SECRET: {bool(creds.get('XERO_CLIENT_SECRET'))}")
        
        if creds.get('XERO_CLIENT_ID'):
            client_id = creds['XERO_CLIENT_ID']
            print(f"- Client ID starts with: {client_id[:10]}..." if len(client_id) > 10 else f"- Client ID: {client_id}")
        
        if creds.get('XERO_CLIENT_SECRET'):
            secret = creds['XERO_CLIENT_SECRET']
            print(f"- Client Secret starts with: {secret[:10]}..." if len(secret) > 10 else f"- Client Secret: {secret}")
        
    except Exception as e:
        print(f"Error loading credentials: {e}")
    
    print(f"\n🔗 Test OAuth URL:")
    print(f"Try visiting: https://login.xero.com/identity/connect/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://localhost:8000/callback&scope=offline_access%20openid%20profile%20email%20accounting.settings%20accounting.transactions%20accounting.contacts&state=test")
    
    print(f"\n💡 Tips for 403 Error:")
    print(f"1. Verify Xero app redirect URI is exactly: https://localhost:8000/callback")
    print(f"2. Check all required scopes are enabled in your Xero app")
    print(f"3. Verify Client ID and Secret match your Xero app")
    print(f"4. Make sure your Xero app is not in 'Draft' status")

if __name__ == "__main__":
    main()