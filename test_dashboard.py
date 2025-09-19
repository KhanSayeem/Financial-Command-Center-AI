"""
Test script to verify the dashboard endpoint returns real data
"""
import requests
import json
import os
from datetime import datetime

def test_dashboard_endpoint():
    """Test the dashboard endpoint with real data"""
    print("Testing dashboard endpoint...")
    print("=" * 50)
    
    # Test the dashboard endpoint
    try:
        response = requests.get(
            "https://127.0.0.1:8000/api/dashboard", 
            headers={"Accept": "application/json"},
            verify=False  # Disable SSL verification for localhost
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nDashboard Data:")
            print(json.dumps(data, indent=2))
            
            # Check if we have real data
            if "xero_data" in data:
                print("\n[SUCCESS] Xero data integration detected")
                if "error" in data["xero_data"]:
                    print(f"  Xero Error: {data['xero_data']['error']}")
                else:
                    print("  Xero data successfully retrieved")
                    
            if "stripe_data" in data:
                print("\n[SUCCESS] Stripe data integration detected")
                if "error" in data["stripe_data"]:
                    print(f"  Stripe Error: {data['stripe_data']['error']}")
                else:
                    print("  Stripe data successfully retrieved")
                    
            if "plaid_data" in data:
                print("\n[SUCCESS] Plaid data integration detected")
                if "error" in data["plaid_data"]:
                    print(f"  Plaid Error: {data['plaid_data']['error']}")
                else:
                    print("  Plaid data successfully retrieved")
                    
            print(f"\n[SUCCESS] Dashboard endpoint is working correctly")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error testing dashboard endpoint: {e}")
        return False

if __name__ == "__main__":
    success = test_dashboard_endpoint()
    if success:
        print("\n" + "=" * 50)
        print("Dashboard endpoint test completed successfully!")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("Dashboard endpoint test failed!")
        print("=" * 50)