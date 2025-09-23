"""
Debug script to see exactly what data the assistant dashboard receives
"""
from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)

import requests
import json

def debug_assistant_data():
    """Debug what data the assistant dashboard receives"""
    print("Debugging assistant dashboard data...")
    print("=" * 50)
    
    try:
        response = requests.get(
            "https://127.0.0.1:8000/api/dashboard",
            headers={"Accept": "application/json"},
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            print("Full API Response:")
            print(json.dumps(data, indent=2))
            
            print("\n" + "=" * 50)
            print("DATA STRUCTURE ANALYSIS:")
            
            # Check Xero data structure
            if "xero_data" in data:
                print("xero_data key exists")
                xero_data = data["xero_data"]
                print(f"  xero_data type: {type(xero_data)}")
                print(f"  xero_data keys: {list(xero_data.keys())}")
                
                if "error" in xero_data:
                    print(f"  xero_data has error: {xero_data['error']}")
                else:
                    print("  xero_data has no error key")
                    
                if "xero" in xero_data:
                    print("  xero_data.xero exists")
                    xero_info = xero_data["xero"]
                    print(f"    xero keys: {list(xero_info.keys())}")
                    print(f"    invoices_count: {xero_info.get('invoices_count', 'N/A')}")
                else:
                    print("  xero_data.xero does not exist")
            else:
                print("xero_data key does not exist")
                
            # Check Stripe data structure
            if "stripe_data" in data:
                print("stripe_data key exists")
                stripe_data = data["stripe_data"]
                if "error" in stripe_data:
                    print(f"  stripe_data has error: {stripe_data['error']}")
                else:
                    print("  stripe_data has no error")
            else:
                print("stripe_data key does not exist")
                
            print("\n" + "=" * 50)
            print("CONDITION EVALUATION:")
            
            # Test the exact conditions from the JavaScript
            xero_condition = "xero_data" in data and "error" not in data["xero_data"] and "xero" in data["xero_data"]
            stripe_condition = "stripe_data" in data and "charges" in data["stripe_data"] and "error" not in data["stripe_data"]
            
            print(f"Xero condition (data.xero_data && !data.xero_data.error && data.xero_data.xero): {xero_condition}")
            print(f"Stripe condition (data.stripe_data && data.stripe_data.charges && !data.stripe_data.error): {stripe_condition}")
            
            if xero_condition:
                print("Should show 'From Xero integration'")
            elif stripe_condition:
                print("Should show Stripe data")
            else:
                print("Will show mock data")
                
            print("\n" + "=" * 50)
            print("XERO DATA DETAILED VIEW:")
            if "xero_data" in data:
                xero_data = data["xero_data"]
                print(f"  xero_data keys: {list(xero_data.keys())}")
                # Check for any error-like keys
                error_keys = [k for k in xero_data.keys() if 'error' in k.lower()]
                if error_keys:
                    print(f"  Error-like keys found: {error_keys}")
                    for key in error_keys:
                        print(f"    {key}: {xero_data[key]}")
                        
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_assistant_data()
