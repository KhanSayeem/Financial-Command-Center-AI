#!/usr/bin/env python3
"""
Xero Configuration Fixer
=========================
Helps diagnose and fix Xero OAuth configuration issues
"""

from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)

import sys

def check_xero_config():
    """Check current Xero configuration"""
    print("Checking Xero Configuration...")
    print()

    # Check environment variables
    client_id = os.getenv('XERO_CLIENT_ID')
    client_secret = os.getenv('XERO_CLIENT_SECRET')
    redirect_uri = os.getenv('XERO_REDIRECT_URI')

    print("Environment Variables:")
    print(f"  XERO_CLIENT_ID: {'[SET]' if client_id else '[NOT SET]'}")
    print(f"  XERO_CLIENT_SECRET: {'[SET]' if client_secret else '[NOT SET]'}")
    print(f"  XERO_REDIRECT_URI: {'[SET]' if redirect_uri else '[NOT SET] (will use default)'}")
    print()

    # Check if setup wizard config exists
    try:
        from setup_wizard import get_configured_credentials
        credentials = get_configured_credentials()
        print("Setup Wizard Configuration:")
        print(f"  XERO_CLIENT_ID: {'[SET]' if credentials.get('XERO_CLIENT_ID') else '[NOT SET]'}")
        print(f"  XERO_CLIENT_SECRET: {'[SET]' if credentials.get('XERO_CLIENT_SECRET') else '[NOT SET]'}")
        print()

        if credentials.get('XERO_CLIENT_ID'):
            stored_id = credentials['XERO_CLIENT_ID']
            print(f"  Stored Client ID: {stored_id}")
            if stored_id == "051E5CA4C55E4783B933A1D5227788E7":
                print("  [OK] Client ID matches what you provided")
            else:
                print(f"  [WARNING] Client ID differs from what you provided (051E5CA4C55E4783B933A1D5227788E7)")

    except Exception as e:
        print(f"[ERROR] Could not check setup wizard config: {e}")

    print()
    print("Expected Redirect URI:")
    port = os.getenv('FCC_PORT') or os.getenv('PORT') or '8000'
    force_https = os.getenv('FORCE_HTTPS', 'true').lower() == 'true'
    allow_http = os.getenv('ALLOW_HTTP', 'false').lower() == 'true'
    scheme = 'https' if force_https or not allow_http else 'http'
    host = os.getenv('XERO_REDIRECT_HOST', 'localhost')
    expected_uri = f"{scheme}://{host}:{port}/callback"
    print(f"  {expected_uri}")
    print()
    print("IMPORTANT: Make sure this EXACT URI is configured in your Xero app settings!")
    print()

def fix_xero_config():
    """Fix Xero configuration with provided credentials"""
    print("Fixing Xero Configuration...")
    print()

    client_id = "051E5CA4C55E4783B933A1D5227788E7"

    # Prompt for client secret
    import getpass
    print(f"Client ID: {client_id}")
    client_secret = getpass.getpass("Enter your Xero Client Secret: ").strip()

    if not client_secret:
        print("[ERROR] Client secret is required!")
        return False

    try:
        # Import and use the setup wizard to save credentials
        from setup_wizard import SetupWizardAPI

        setup_api = SetupWizardAPI()

        # Save Xero configuration
        result = setup_api.save_service_config('xero', {
            'client_id': client_id,
            'client_secret': client_secret
        })

        if result.get('success'):
            print("[SUCCESS] Xero credentials saved successfully!")

            # Also set environment variables for this session
            os.environ['XERO_CLIENT_ID'] = client_id
            os.environ['XERO_CLIENT_SECRET'] = client_secret

            print()
            print("Configuration complete! Try connecting to Xero again.")
            print()
            print("If you still get 'invalid_client' error, check:")
            print("1. Your Xero app's redirect URI matches exactly:")
            port = os.getenv('FCC_PORT') or os.getenv('PORT') or '8000'
            force_https = os.getenv('FORCE_HTTPS', 'true').lower() == 'true'
            allow_http = os.getenv('ALLOW_HTTP', 'false').lower() == 'true'
            scheme = 'https' if force_https or not allow_http else 'http'
            host = os.getenv('XERO_REDIRECT_HOST', 'localhost')
            expected_uri = f"{scheme}://{host}:{port}/callback"
            print(f"   {expected_uri}")
            print("2. Your client secret is correct")
            print("3. Your Xero app is not in demo company mode if you're using production")

            return True
        else:
            print(f"[ERROR] Failed to save credentials: {result.get('message', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"[ERROR] Error saving configuration: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        success = fix_xero_config()
        if success:
            print("\n[SUCCESS] Done! You can now restart your application and try connecting to Xero.")
        else:
            print("\n[ERROR] Configuration failed. Please check the errors above.")
    else:
        check_xero_config()
        print("To fix the configuration, run:")
        print("python fix_xero_config.py fix")
