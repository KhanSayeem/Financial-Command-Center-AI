"""
Script to update Xero credentials and exit demo mode
"""
import os
import json
from pathlib import Path

def update_xero_credentials():
    """Update Xero credentials in the config file"""
    
    # Xero credentials
    xero_client_id = "67834CA82C5B49889A95668DAA6EACB0"
    xero_client_secret = "Z_d_41wPxl_cwQEU2-9R5y0niNOuIsPhZq-u7MYCBixpLJhu"
    
    # Set environment variables (for current session)
    os.environ['XERO_CLIENT_ID'] = xero_client_id
    os.environ['XERO_CLIENT_SECRET'] = xero_client_secret
    
    print("Environment variables set:")
    print(f"XERO_CLIENT_ID: {os.environ.get('XERO_CLIENT_ID')}")
    print(f"XERO_CLIENT_SECRET: {os.environ.get('XERO_CLIENT_SECRET')}")
    
    # Update the app mode to live
    mode_file = Path('secure_config/app_mode.json')
    if mode_file.exists():
        mode_data = json.loads(mode_file.read_text())
        print(f"Current mode: {mode_data['mode']}")
        
        # Set to live mode
        mode_data['mode'] = 'live'
        mode_data['updated_at'] = __import__('datetime').datetime.utcnow().isoformat()
        
        mode_file.write_text(json.dumps(mode_data, indent=2))
        print("App mode updated to live")
    else:
        print("Mode file not found")
    
    print("\nNext steps:")
    print("1. Restart the Financial Command Center application")
    print("2. The app should now connect to real Xero data")
    print("3. The assistant dashboard will show real-time data instead of mock values")

if __name__ == "__main__":
    update_xero_credentials()