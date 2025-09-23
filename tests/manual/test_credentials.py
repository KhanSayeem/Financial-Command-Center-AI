"""
Test script to verify Xero credentials are properly saved and loaded
"""
import os
import json
from pathlib import Path

def test_credentials():
    """Test if Xero credentials are properly configured"""
    print("Testing Xero credentials configuration...")
    print("=" * 50)
    
    # Check environment variables
    print("1. Environment Variables:")
    xero_client_id = os.getenv('XERO_CLIENT_ID')
    xero_client_secret = os.getenv('XERO_CLIENT_SECRET')
    print(f"   XERO_CLIENT_ID: {'SET' if xero_client_id else 'NOT SET'}")
    print(f"   XERO_CLIENT_SECRET: {'SET' if xero_client_secret else 'NOT SET'}")
    
    # Check config file
    print("\n2. Encrypted Config File:")
    config_file = Path('secure_config/config.enc')
    if config_file.exists():
        print(f"   Config file exists: YES")
        try:
            # Try to load the config to see if it contains Xero credentials
            from setup_wizard import ConfigurationManager
            config_manager = ConfigurationManager()
            config = config_manager.load_config()
            if config:
                print(f"   Config loaded successfully: YES")
                xero_config = config.get('xero', {})
                if xero_config:
                    print(f"   Xero config found: YES")
                    client_id = xero_config.get('client_id')
                    client_secret = xero_config.get('client_secret')
                    skipped = xero_config.get('skipped', False)
                    print(f"   Client ID present: {'YES' if client_id else 'NO'}")
                    print(f"   Client Secret present: {'YES' if client_secret else 'NO'}")
                    print(f"   Skipped: {skipped}")
                else:
                    print(f"   Xero config found: NO")
            else:
                print(f"   Config loaded successfully: NO")
        except Exception as e:
            print(f"   Error loading config: {e}")
    else:
        print(f"   Config file exists: NO")
    
    # Check app mode
    print("\n3. App Mode:")
    mode_file = Path('secure_config/app_mode.json')
    if mode_file.exists():
        try:
            mode_data = json.loads(mode_file.read_text())
            print(f"   Current mode: {mode_data.get('mode', 'unknown')}")
        except Exception as e:
            print(f"   Error reading mode file: {e}")
    else:
        print(f"   Mode file exists: NO")
    
    print("\n" + "=" * 50)
    print("NEXT STEPS:")
    print("If credentials are not properly set:")
    print("1. Enter credentials in the setup wizard again")
    print("2. Click 'Save Configuration' button")
    print("3. Restart the application")
    print("4. Check that the app exits demo mode")

if __name__ == "__main__":
    test_credentials()