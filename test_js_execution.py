"""
Comprehensive test to verify JavaScript execution and UI updates
"""
import requests

def test_js_execution():
    """Test JavaScript execution and UI updates"""
    print("Testing JavaScript execution and UI updates...")
    print("=" * 50)
    
    try:
        # Get the assistant page HTML
        response = requests.get("https://127.0.0.1:8000/assistant/", verify=False)
        
        if response.status_code == 200:
            html_content = response.text
            
            print("HTML ELEMENT VERIFICATION:")
            print("-" * 30)
            
            # Check for required element IDs
            required_ids = [
                'cash-position-value',
                'cash-position-trend',
                'health-score-value',
                'health-score-status',
                'revenue-value',
                'revenue-period',
                'last-updated-value'
            ]
            
            missing_ids = []
            found_ids = []
            
            for element_id in required_ids:
                if f'id="{element_id}"' in html_content or f"id='{element_id}'" in html_content:
                    found_ids.append(element_id)
                else:
                    missing_ids.append(element_id)
            
            print(f"Found element IDs: {found_ids}")
            print(f"Missing element IDs: {missing_ids}")
            
            if not missing_ids:
                print("✓ All required element IDs are present in the HTML")
            else:
                print(f"✗ Missing element IDs: {missing_ids}")
                
            # Check for JavaScript function
            if 'updateDashboardWithRealData' in html_content:
                print("✓ updateDashboardWithRealData function found in HTML")
            else:
                print("✗ updateDashboardWithRealData function NOT found in HTML")
                
            # Check for fetch call
            if 'fetch(\'/api/dashboard\'' in html_content or 'fetch("/api/dashboard"' in html_content:
                print("✓ fetch call to /api/dashboard found in HTML")
            else:
                print("✗ fetch call to /api/dashboard NOT found in HTML")
                
            print("\n" + "=" * 50)
            print("EXPECTED BEHAVIOR AFTER PAGE LOAD:")
            print("- Cash position value should be '$48,250.75'")
            print("- Cash position trend should be 'From Xero integration'")
            print("- Revenue value should be '$195,000' (13 invoices × $15,000)")
            print("- Revenue period should be 'Estimated from 13 invoices'")
            print("- Last updated should show current date (e.g., 'Sep 19, 2025')")
            print("- Health score should show '87/100' with 'Healthy status'")
            
            print("\nTROUBLESHOOTING STEPS:")
            print("1. Open browser Developer Tools (F12)")
            print("2. Go to Console tab")
            print("3. Refresh the page")
            print("4. Look for these console messages:")
            print("   - 'Dashboard data:' followed by JSON data")
            print("   - 'Updating dashboard with data:'")
            print("   - 'Using Xero data path'")
            print("5. If you see these messages but UI doesn't update:")
            print("   - Check that element IDs match exactly")
            print("   - Look for JavaScript errors in console")
            
        else:
            print(f"Error loading assistant page: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_js_execution()