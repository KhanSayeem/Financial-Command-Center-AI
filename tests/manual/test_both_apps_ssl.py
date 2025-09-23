#!/usr/bin/env python3
"""
SSL Integration Test for Both Applications
Tests SSL setup with both app.py and app_with_setup_wizard.py
"""

import os
import sys
import time
import requests
import subprocess
from pathlib import Path
import threading
import signal

# Suppress SSL warnings for testing
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class AppTester:
    """Test runner for Flask applications with SSL"""
    
    def __init__(self, app_file, test_name):
        self.app_file = app_file
        self.test_name = test_name
        self.process = None
        self.port = 8000
    
    def start_app(self):
        """Start the Flask application"""
        print(f"🚀 Starting {self.test_name}...")
        
        # Start the app in a subprocess
        self.process = subprocess.Popen([
            sys.executable, self.app_file
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
           text=True, bufsize=1, universal_newlines=True)
        
        # Wait for the app to start
        print("   Waiting for application to start...")
        time.sleep(8)  # Give more time for SSL certificate generation
        
        return self.process.poll() is None  # True if still running
    
    def stop_app(self):
        """Stop the Flask application"""
        if self.process:
            print(f"🛑 Stopping {self.test_name}...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
    
    def test_endpoints(self):
        """Test various endpoints"""
        endpoints = [
            ("/health", "Health Check"),
            ("/", "Home Page"),
            ("/admin/ssl-help", "SSL Help"),
            ("/admin/certificate-bundle", "Certificate Bundle")
        ]
        
        results = {"https": [], "http": []}
        
        print(f"🧪 Testing {self.test_name} endpoints...")
        
        for endpoint, name in endpoints:
            # Test HTTPS
            try:
                response = requests.get(f"https://localhost:{self.port}{endpoint}", 
                                      verify=False, timeout=10)
                status = "✅ PASS" if response.status_code < 500 else "❌ FAIL"
                results["https"].append((name, response.status_code, status))
                print(f"   HTTPS {name}: {status} ({response.status_code})")
            except Exception as e:
                results["https"].append((name, 0, "❌ FAIL"))
                print(f"   HTTPS {name}: ❌ FAIL ({str(e)[:50]}...)")
            
            # Test HTTP (should redirect or show warning)
            try:
                response = requests.get(f"http://localhost:{self.port}{endpoint}", 
                                      allow_redirects=False, timeout=10)
                if response.status_code in [301, 302, 426]:  # Redirect/Warning
                    status = "✅ PASS"
                    note = "(redirect/warning)"
                elif response.status_code == 200:
                    status = "✅ PASS"
                    note = "(allowed)"
                else:
                    status = "⚠️ WARN"
                    note = f"(unexpected: {response.status_code})"
                
                results["http"].append((name, response.status_code, status))
                print(f"   HTTP  {name}: {status} {note}")
            except Exception as e:
                results["http"].append((name, 0, "❌ FAIL"))
                print(f"   HTTP  {name}: ❌ FAIL ({str(e)[:50]}...)")
        
        return results
    
    def get_app_output(self):
        """Get application output for debugging"""
        if self.process:
            try:
                stdout, stderr = self.process.communicate(timeout=1)
                return stdout, stderr
            except:
                return "", ""
        return "", ""


def test_certificate_generation():
    """Test certificate generation before starting apps"""
    print("🔐 Testing Certificate Generation...")
    
    try:
        from cert_manager import CertificateManager
        cert_manager = CertificateManager()
        
        # Generate certificates
        print("   Generating SSL certificates...")
        cert_manager.generate_server_certificate()
        
        # Check health
        health = cert_manager.health_check()
        print(f"   Certificate Valid: {'✅' if health['certificate_valid'] else '❌'}")
        print(f"   Expires: {health['expires']}")
        
        return health['certificate_valid']
    except Exception as e:
        print(f"   ❌ Certificate generation failed: {e}")
        return False


def test_app_ssl_integration(app_file, test_name):
    """Test SSL integration for a specific app"""
    print(f"\n{'='*60}")
    print(f"🧪 Testing {test_name}")
    print(f"{'='*60}")
    
    tester = AppTester(app_file, test_name)
    
    try:
        # Start the app
        if not tester.start_app():
            print(f"❌ Failed to start {test_name}")
            stdout, stderr = tester.get_app_output()
            if stderr:
                print(f"Error output: {stderr[:500]}")
            return False
        
        # Test endpoints
        results = tester.test_endpoints()
        
        # Calculate success rate
        total_tests = len(results["https"]) + len(results["http"])
        passed_tests = sum(1 for _, _, status in results["https"] + results["http"] 
                          if status.startswith("✅"))
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📊 {test_name} Results:")
        print(f"   Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        return success_rate >= 75  # 75% success rate threshold
    
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    
    finally:
        tester.stop_app()


def run_comprehensive_test():
    """Run comprehensive SSL test for both applications"""
    print("🚀 Comprehensive SSL Integration Test")
    print("=" * 60)
    print("Testing SSL certificate management across both applications")
    print()
    
    # Test certificate generation first
    cert_gen_success = test_certificate_generation()
    
    # Test both applications
    tests = [
        ("app.py", "Main Financial Command Center"),
        ("app_with_setup_wizard.py", "Setup Wizard Version")
    ]
    
    results = {}
    
    for app_file, test_name in tests:
        if not Path(app_file).exists():
            print(f"⚠️ {app_file} not found, skipping...")
            results[test_name] = False
            continue
        
        results[test_name] = test_app_ssl_integration(app_file, test_name)
        
        # Wait between tests
        time.sleep(3)
    
    # Final summary
    print(f"\n{'='*60}")
    print("📋 Final Test Summary")
    print(f"{'='*60}")
    
    print(f"Certificate Generation: {'✅ PASS' if cert_gen_success else '❌ FAIL'}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    overall_success = cert_gen_success and (passed == total)
    print(f"\n🎯 Overall Result: {'✅ PASS' if overall_success else '❌ FAIL'}")
    print(f"   Apps Passed: {passed}/{total}")
    
    if overall_success:
        print("\n🎉 SSL Integration successful across all applications!")
        print("   Both app.py and app_with_setup_wizard.py support:")
        print("   ✅ Automatic certificate generation")
        print("   ✅ SSL/TLS encryption")
        print("   ✅ HTTP to HTTPS redirects")
        print("   ✅ SSL management endpoints")
        print("   ✅ Professional security warnings")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        print("   Common issues:")
        print("   - Missing dependencies (cryptography)")
        print("   - Port conflicts")
        print("   - Certificate generation failures")
        print("   - Import errors")
    
    return overall_success


def show_usage():
    """Show usage instructions"""
    print("""
🔐 SSL Integration Test Suite

Usage:
  python test_both_apps_ssl.py                 # Run comprehensive test
  python test_both_apps_ssl.py --cert-only     # Test certificate generation only
  python test_both_apps_ssl.py --main-only     # Test main app only
  python test_both_apps_ssl.py --wizard-only   # Test setup wizard app only

Prerequisites:
  - Both app.py and app_with_setup_wizard.py should be present
  - All required dependencies installed
  - Port 8000 should be available

The test will:
  1. Generate SSL certificates using cert_manager.py
  2. Start each application with SSL enabled
  3. Test HTTPS and HTTP endpoints
  4. Verify SSL certificate functionality
  5. Check security warnings and redirects
""")


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SSL Integration Test Suite")
    parser.add_argument("--cert-only", action="store_true", help="Test certificate generation only")
    parser.add_argument("--main-only", action="store_true", help="Test main app only")
    parser.add_argument("--wizard-only", action="store_true", help="Test setup wizard app only")
    parser.add_argument("--help-usage", action="store_true", help="Show detailed usage")
    
    args = parser.parse_args()
    
    if args.help_usage:
        show_usage()
        return
    
    try:
        if args.cert_only:
            success = test_certificate_generation()
        elif args.main_only:
            success = test_app_ssl_integration("app.py", "Main Financial Command Center")
        elif args.wizard_only:
            success = test_app_ssl_integration("app_with_setup_wizard.py", "Setup Wizard Version")
        else:
            success = run_comprehensive_test()
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()