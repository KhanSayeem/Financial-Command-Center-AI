#!/usr/bin/env python3
"""
Debug script to inspect Xero contact object structure
Helps identify the exact attributes and their types
"""

from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)

import requests
import json
import urllib3

# Disable SSL warnings for local testing
urllib3.disable_warnings()

def test_contacts_endpoint():
    """Test the contacts endpoint and show response structure"""
    try:
        print("Testing Xero contacts endpoint...")
        response = requests.get("https://localhost:8000/api/oauth/test-flow", verify=False)
        
        if response.status_code == 200:
            data = response.json()
            print("OAuth configuration status:")
            print(json.dumps(data['oauth_config'], indent=2))
            print(f"Has token: {data['token_info']['has_token']}")
            print(f"Has tenant: {data['token_info']['has_tenant_id']}")
        else:
            print(f"OAuth test failed: {response.status_code}")
        
        print("\nTesting web UI contacts endpoint...")
        response = requests.get("https://localhost:8000/xero/contacts", verify=False, allow_redirects=False)
        
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            print(f"Redirected to: {response.headers.get('Location')}")
            print("Need to authenticate first")
        elif response.status_code == 200:
            print("Success! Contact page loaded.")
        else:
            print(f"Response text: {response.text[:500]}...")

    except Exception as e:
        print(f"Error testing endpoint: {e}")

def test_json_api_endpoint():
    """Test the JSON API endpoint to see raw contact structure"""
    try:
        print("\nTesting JSON API contacts endpoint...")
        
        # First need to get a session with token
        session = requests.Session()
        session.verify = False
        
        # Try to access the API endpoint (will fail without auth but shows the error)
        response = session.get("https://localhost:8000/api/xero/contacts")
        
        print(f"API Status: {response.status_code}")
        if response.status_code == 401:
            print("Expected: Need authentication/API key for JSON endpoint")
        elif response.status_code == 200:
            print("Got contacts data from API")
            data = response.json()
            if data.get('contacts'):
                print(f"Number of contacts: {len(data['contacts'])}")
                if len(data['contacts']) > 0:
                    print("First contact structure:")
                    print(json.dumps(data['contacts'][0], indent=2, default=str))
        
    except Exception as e:
        print(f"Error testing JSON API: {e}")

if __name__ == "__main__":
    print("="*60)
    print("Xero Contacts Debug Script")
    print("="*60)
    
    test_contacts_endpoint()
    test_json_api_endpoint()
    
    print("\n" + "="*60)
    print("Debug script completed.")
    print("="*60)
    
    print("\nNext steps to resolve the issue:")
    print("1. If redirected to login, authenticate via /login first")
    print("2. Then test the /xero/contacts endpoint again") 
    print("3. Check server logs for detailed error messages")
    print("4. The improved error handling should prevent crashes now")
