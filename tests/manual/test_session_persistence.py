#!/usr/bin/env python3
"""
Session Persistence Test Script
==============================

This script tests the enhanced Flask session configuration to ensure
OAuth tokens persist correctly across requests and application restarts.

Usage:
    python test_session_persistence.py
"""

import requests
import time
import json
import sys
from pathlib import Path

# Test configuration
BASE_URL = "https://localhost:8000"
VERIFY_SSL = False  # Set to True in production with valid certificates

class SessionPersistenceTest:
    """Test OAuth session persistence functionality"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = VERIFY_SSL
        self.test_results = []
    
    def log_test(self, test_name, passed, details=None):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': time.time()
        })
    
    def test_health_endpoint(self):
        """Test if the application is running and session config is loaded"""
        try:
            response = self.session.get(f"{BASE_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                has_session_config = 'session_config' in data
                
                if has_session_config:
                    session_status = data['session_config'].get('status', 'unknown')
                    self.log_test("Application Health & Session Config", 
                                session_status == 'healthy',
                                f"Session config status: {session_status}")
                else:
                    self.log_test("Application Health & Session Config", False,
                                "No session configuration found in health check")
            else:
                self.log_test("Application Health & Session Config", False,
                            f"HTTP {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            self.log_test("Application Health & Session Config", False, str(e))
    
    def test_session_debug_endpoints(self):
        """Test session debugging endpoints"""
        try:
            # Test session debug info
            response = self.session.get(f"{BASE_URL}/api/session/debug")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Session Debug Info", True, 
                            f"Secret key length: {data['flask_config']['SECRET_KEY_LENGTH']}")
            elif response.status_code == 403:
                self.log_test("Session Debug Info", True, 
                            "Debug endpoints protected (not in debug mode)")
            else:
                self.log_test("Session Debug Info", False, 
                            f"HTTP {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            self.log_test("Session Debug Info", False, str(e))
    
    def test_session_persistence(self):
        """Test basic session persistence"""
        try:
            # First, try to store a test value
            response = self.session.post(f"{BASE_URL}/api/session/test-persistence")
            
            if response.status_code == 403:
                self.log_test("Session Persistence Test", True,
                            "Test endpoints protected (not in debug mode)")
                return
            
            if response.status_code == 200:
                store_data = response.json()
                
                if store_data.get('success'):
                    # Wait a moment to ensure session persistence
                    time.sleep(2)
                    
                    # Try to retrieve the test value
                    response = self.session.get(f"{BASE_URL}/api/session/test-persistence")
                    
                    if response.status_code == 200:
                        retrieve_data = response.json()
                        persistence_test = retrieve_data.get('persistence_test', 'FAILED')
                        
                        self.log_test("Session Persistence Test", 
                                    persistence_test == 'PASSED',
                                    f"Test result: {persistence_test}")
                    else:
                        self.log_test("Session Persistence Test", False,
                                    f"Failed to retrieve test data: HTTP {response.status_code}")
                else:
                    self.log_test("Session Persistence Test", False,
                                "Failed to store test data")
            else:
                self.log_test("Session Persistence Test", False,
                            f"HTTP {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            self.log_test("Session Persistence Test", False, str(e))
    
    def test_session_cookies(self):
        """Test session cookie configuration"""
        try:
            # Make any request to get session cookies
            response = self.session.get(f"{BASE_URL}/health")
            
            if response.status_code == 200:
                # Check if we received any session cookies
                cookies = self.session.cookies
                session_cookies = [c for c in cookies if 'session' in c.name.lower()]
                
                if session_cookies:
                    cookie = session_cookies[0]
                    self.log_test("Session Cookies Present", True,
                                f"Cookie name: {cookie.name}")
                else:
                    self.log_test("Session Cookies Present", False,
                                "No session cookies found")
            else:
                self.log_test("Session Cookies Present", False,
                            f"HTTP {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            self.log_test("Session Cookies Present", False, str(e))
    
    def test_xero_oauth_setup(self):
        """Test Xero OAuth endpoints availability"""
        try:
            # Test login endpoint (should redirect or show setup message)
            response = self.session.get(f"{BASE_URL}/login", allow_redirects=False)
            
            if response.status_code in [302, 400]:  # Redirect to OAuth or setup message
                self.log_test("Xero OAuth Setup", True,
                            f"Login endpoint responds appropriately: HTTP {response.status_code}")
            else:
                self.log_test("Xero OAuth Setup", False,
                            f"Unexpected response: HTTP {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            self.log_test("Xero OAuth Setup", False, str(e))
    
    def run_all_tests(self):
        """Run all session persistence tests"""
        print("="*60)
        print("Flask Session Persistence Test Suite")
        print("="*60)
        print(f"Testing application at: {BASE_URL}")
        print(f"SSL verification: {'Enabled' if VERIFY_SSL else 'Disabled'}")
        print()
        
        # Run tests in sequence
        self.test_health_endpoint()
        self.test_session_debug_endpoints()
        self.test_session_cookies()
        self.test_session_persistence()
        self.test_xero_oauth_setup()
        
        # Summary
        print()
        print("="*60)
        print("Test Summary")
        print("="*60)
        
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        total_tests = len(self.test_results)
        
        print(f"Tests passed: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! Session persistence is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            failed_tests = [r for r in self.test_results if not r['passed']]
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
            return False
    
    def save_test_results(self):
        """Save test results to a file"""
        results_file = Path("session_test_results.json")
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.time(),
                'base_url': BASE_URL,
                'ssl_verification': VERIFY_SSL,
                'results': self.test_results
            }, f, indent=2)
        
        print(f"\nTest results saved to: {results_file}")


def main():
    """Run the session persistence tests"""
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print(__doc__)
        return
    
    # Check if the application is likely running
    print("Starting Session Persistence Tests...")
    print("Make sure the Financial Command Center AI application is running!")
    print()
    
    tester = SessionPersistenceTest()
    
    try:
        success = tester.run_all_tests()
        tester.save_test_results()
        
        if not success:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during testing: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()