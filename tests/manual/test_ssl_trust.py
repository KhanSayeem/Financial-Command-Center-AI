#!/usr/bin/env python3
"""
SSL Trust Test Script for Financial Command Center AI
Tests if SSL certificates are properly trusted by the system
"""

import ssl
import socket
import urllib3
import requests
from urllib3.exceptions import InsecureRequestWarning
import sys
import subprocess
import platform


def test_ssl_connection(host="localhost", port=8000):
    """Test SSL connection without disabling verification"""
    print(f"🔐 Testing SSL connection to {host}:{port}...")
    
    try:
        # Test with Python's ssl module
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                print(f"✅ SSL handshake successful")
                print(f"   SSL Version: {ssock.version()}")
                print(f"   Cipher Suite: {ssock.cipher()[0]}")
                cert = ssock.getpeercert()
                print(f"   Certificate Subject: {cert.get('subject', 'Unknown')}")
                return True
    except ssl.SSLError as e:
        print(f"❌ SSL Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False


def test_requests_library(url="https://localhost:8000/health"):
    """Test with requests library (should work without verify=False)"""
    print(f"📡 Testing HTTPS request to {url}...")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"✅ HTTPS request successful")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Size: {len(response.text)} bytes")
        return True
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL Certificate Error: {e}")
        print("   Certificate is not trusted by the system")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        print("   Make sure the Financial Command Center is running")
        return False
    except Exception as e:
        print(f"❌ Request Error: {e}")
        return False


def test_curl_command():
    """Test with curl command (should work without -k flag)"""
    print("🌐 Testing with curl command...")
    
    try:
        # Test curl without -k flag (should work with trusted certificates)
        result = subprocess.run(
            ["curl", "-I", "https://localhost:8000/health"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("✅ curl command successful (certificate trusted)")
            print(f"   Response: {result.stdout.split()[1] if result.stdout.split() else 'Unknown'}")
            return True
        else:
            print("❌ curl command failed")
            print(f"   Error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("⚠️  curl command not available")
        return None
    except Exception as e:
        print(f"❌ curl test error: {e}")
        return False


def check_certificate_store():
    """Check if certificate is installed in system store (Windows only)"""
    if platform.system() != "Windows":
        print("ℹ️  Certificate store check only available on Windows")
        return None
    
    print("🏪 Checking Windows certificate store...")
    
    try:
        # Check if our CA certificate is in the trusted root store
        result = subprocess.run([
            "powershell", "-Command", 
            "Get-ChildItem -Path 'Cert:\\LocalMachine\\Root' | Where-Object {$_.Subject -like '*Financial Command Center*'}"
        ], capture_output=True, text=True, timeout=30)
        
        if "Financial Command Center" in result.stdout:
            print("✅ Certificate found in Windows trusted root store")
            return True
        else:
            print("❌ Certificate not found in Windows trusted root store")
            print("   Try running: python cert_manager.py --install-ca")
            return False
    except Exception as e:
        print(f"⚠️  Could not check certificate store: {e}")
        return None


def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 SSL Certificate Trust Test")
    print("   Financial Command Center AI")
    print("=" * 60)
    
    # Check if server is running
    print("1️⃣ Checking if server is running...")
    try:
        response = requests.get("https://localhost:8000/health", verify=False, timeout=5)
        print("✅ Server is running")
    except:
        print("❌ Server is not running or not accessible")
        print("   Please start the Financial Command Center AI first")
        print("   Command: python app.py")
        sys.exit(1)
    
    print()
    
    # Run tests
    tests_passed = 0
    total_tests = 0
    
    # Test 1: SSL Connection
    total_tests += 1
    if test_ssl_connection():
        tests_passed += 1
    
    print()
    
    # Test 2: Requests Library
    total_tests += 1
    if test_requests_library():
        tests_passed += 1
    
    print()
    
    # Test 3: curl Command
    curl_result = test_curl_command()
    if curl_result is not None:
        total_tests += 1
        if curl_result:
            tests_passed += 1
    
    print()
    
    # Test 4: Certificate Store (Windows only)
    store_result = check_certificate_store()
    if store_result is not None:
        total_tests += 1
        if store_result:
            tests_passed += 1
    
    print()
    print("=" * 60)
    print("📊 Test Results")
    print("=" * 60)
    
    if tests_passed == total_tests and total_tests > 0:
        print("🎉 ALL TESTS PASSED!")
        print("   Your SSL certificates are properly trusted by the system.")
        print("   Browsers should show secure connections without warnings.")
    elif tests_passed > 0:
        print(f"⚠️  PARTIAL SUCCESS: {tests_passed}/{total_tests} tests passed")
        print("   Some certificate trust issues remain.")
        print()
        print("🔧 Suggested fixes:")
        print("   1. Generate trusted certificates: python cert_manager.py --mkcert")
        print("   2. Install CA certificate: python cert_manager.py --install-ca")
        print("   3. Create installation bundle: python cert_manager.py --bundle")
    else:
        print("❌ ALL TESTS FAILED")
        print("   SSL certificates are not trusted by the system.")
        print()
        print("🔧 Immediate fixes:")
        print("   1. Generate trusted certificates: python cert_manager.py --mkcert")
        print("   2. Install CA certificate: python cert_manager.py --install-ca")
        print("   3. Follow browser-specific instructions in BROWSER_TRUST_GUIDE.md")
    
    print()
    print("📚 Additional help:")
    print("   • SSL Health Check: python cert_manager.py --health")
    print("   • Browser Trust Guide: BROWSER_TRUST_GUIDE.md")
    print("   • SSL Setup Guide: SSL_SETUP_GUIDE.md")
    print("   • In-app help: https://localhost:8000/admin/ssl-help")
    
    return tests_passed == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)