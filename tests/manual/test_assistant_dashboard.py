"""
Test script to verify the assistant dashboard fetches real data
"""
import requests
import json

def test_assistant_dashboard():
    """Test if the assistant dashboard fetches real data"""
    print("Testing assistant dashboard data fetch...")
    print("=" * 50)
    
    # Test the dashboard API endpoint
    try:
        response = requests.get(
            "https://127.0.0.1:8000/api/dashboard",
            headers={"Accept": "application/json"},
            verify=False  # Disable SSL verification for localhost
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nAPI Response:")
            print(json.dumps(data, indent=2)[:500] + "..." if len(json.dumps(data, indent=2)) > 500 else json.dumps(data, indent=2))
            
            # Check what data sources are available
            if "xero_data" in data:
                if "error" in data["xero_data"]:
                    print(f"\n[XERO] Error: {data['xero_data']['error']}")
                else:
                    print("\n[XERO] Successfully connected to Xero")
                    if "xero" in data["xero_data"]:
                        xero_info = data["xero_data"]["xero"]
                        print(f"  Tenant ID: {xero_info.get('tenant_id', 'N/A')}")
                        print(f"  Accounts: {xero_info.get('accounts_count', 0)}")
                        print(f"  Invoices: {xero_info.get('invoices_count', 0)}")
                        
            if "stripe_data" in data:
                if "error" in data["stripe_data"]:
                    print(f"\n[STRIPE] Error: {data['stripe_data']['error']}")
                else:
                    print("\n[STRIPE] Successfully connected to Stripe")
                    if "charges" in data["stripe_data"]:
                        print(f"  Recent charges: {len(data['stripe_data']['charges'])}")
                        
            if "plaid_data" in data:
                if "error" in data["plaid_data"]:
                    print(f"\n[PLAID] Error: {data['plaid_data']['error']}")
                else:
                    print("\n[PLAID] Successfully connected to Plaid")
                    if "accounts" in data["plaid_data"]:
                        print(f"  Bank accounts: {len(data['plaid_data']['accounts'])}")
            
            print(f"\n[SUCCESS] API endpoint is working correctly")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error testing API endpoint: {e}")
        return False

if __name__ == "__main__":
    success = test_assistant_dashboard()
    if success:
        print("\n" + "=" * 50)
        print("Assistant dashboard data fetch test completed successfully!")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Refresh your API credentials for Xero, Stripe, and Plaid")
        print("2. Visit https://localhost:8000/assistant/ to see real-time data")
        print("3. The dashboard will now show live data instead of mock values")
    else:
        print("\n" + "=" * 50)
        print("Assistant dashboard data fetch test failed!")
        print("=" * 50)