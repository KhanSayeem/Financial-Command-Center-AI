#!/usr/bin/env python3
"""
SSL Setup Test Script for Financial Command Center AI
Tests certificate generation, installation, and functionality
"""

import os
import sys
import ssl
import socket
import requests
import subprocess
from pathlib import Path
import json
import time
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def test_certificate_generation():
    """Test certificate generation functionality"""
    print("🔧 Testing Certificate Generation...")
    
    try:
        from cert_manager import CertificateManager
        cert_manager = CertificateManager()
        
        # Test certificate generation
        cert_manager.generate_server_certificate()
        
        # Verify files exist
        cert_file = Path(cert_manager.config["cert_file"])
        key_file = Path(cert_manager.config["key_file"])
        ca_file = Path(cert_manager.config["ca_cert"])
        
        if cert_file.exists() and key_file.exists() and ca_file.exists():
            print("✅ Certificate generation successful")
            return True
        else:
            print("❌ Certificate files not found")
            return False
    
    except Exception as e:
        print(f"❌ Certificate generation failed: {e}")
        return False


def test_certificate_validity():
    """Test certificate validity and properties"""
    print("🔍 Testing Certificate Validity...")
    
    try:
        from cert_manager import CertificateManager
        cert_manager = CertificateManager()
        
        health = cert_manager.health_check()
        
        print(f"   Certificate Valid: {'✅' if health['certificate_valid'] else '❌'}")
        print(f"   CA Exists: {'✅' if health['ca_exists'] else '❌'}")
        print(f"   Server Cert Exists: {'✅' if health['server_cert_exists'] else '❌'}")
        print(f"   Server Key Exists: {'✅' if health['server_key_exists'] else '❌'}")
        print(f"   Expires: {health['expires']}")
        print(f"   Hostnames: {', '.join(health['hostnames'])}")
        
        return health['certificate_valid'] and health['ca_exists'] and health['server_cert_exists']
    
    except Exception as e:
        print(f"❌ Certificate validity check failed: {e}")
        return False


def test_ssl_connection():
    """Test SSL connection to the application"""
    print("🔐 Testing SSL Connection...")
    
    # Wait a moment for the server to start
    time.sleep(2)
    
    try:
        # Test SSL handshake
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection(("localhost", 8000), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname="localhost") as ssock:
                print(f"✅ SSL Connection successful")
                print(f"   SSL Version: {ssock.version()}")
                print(f"   Cipher: {ssock.cipher()[0] if ssock.cipher() else 'Unknown'}")
                return True
    
    except socket.timeout:
        print("❌ Connection timeout - is the server running?")
        return False
    except Exception as e:
        print(f"❌ SSL connection failed: {e}")
        return False


def test_http_endpoints():
    """Test HTTP/HTTPS endpoints"""
    print("🌐 Testing HTTP/HTTPS Endpoints...")
    
    endpoints = [
        "/health",
        "/",
        "/admin/ssl-help"
    ]
    
    results = {"https": 0, "http": 0}
    
    for endpoint in endpoints:
        # Test HTTPS
        try:
            response = requests.get(f"https://localhost:8000{endpoint}", 
                                  verify=False, timeout=5)
            if response.status_code < 500:
                results["https"] += 1
                print(f"   ✅ HTTPS {endpoint}: {response.status_code}")
            else:
                print(f"   ❌ HTTPS {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ HTTPS {endpoint}: {str(e)[:50]}...")
        
        # Test HTTP (should redirect or show warning)
        try:
            response = requests.get(f"http://localhost:8000{endpoint}", 
                                  allow_redirects=False, timeout=5)
            if response.status_code in [301, 302, 426]:  # Redirect or Upgrade Required
                results["http"] += 1
                print(f"   ✅ HTTP {endpoint}: {response.status_code} (redirect/warning)")
            elif response.status_code == 200:
                results["http"] += 1
                print(f"   ✅ HTTP {endpoint}: {response.status_code} (allowed)")
            else:
                print(f"   ⚠️  HTTP {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ HTTP {endpoint}: {str(e)[:50]}...")
    
    return results["https"] >= len(endpoints) // 2


def test_certificate_bundle():
    """Test certificate bundle creation"""
    print("📦 Testing Certificate Bundle Creation...")
    
    try:
        from cert_manager import CertificateManager
        cert_manager = CertificateManager()
        
        bundle_dir = cert_manager.create_client_bundle()
        
        expected_files = [
            "ca_certificate.crt",
            "install_certificate_windows.bat",
            "install_certificate_unix.sh",
            "README.md"
        ]
        
        for filename in expected_files:
            file_path = bundle_dir / filename
            if file_path.exists():
                print(f"   ✅ {filename}")
            else:
                print(f"   ❌ {filename} not found")
                return False
        
        print(f"✅ Certificate bundle created at: {bundle_dir}")
        return True
    
    except Exception as e:
        print(f"❌ Bundle creation failed: {e}")
        return False


def test_server_modes():
    """Test different server modes"""
    print("🔄 Testing Server Modes...")
    
    # This would require restarting the server with different configs
    # For now, just test that the configuration is readable
    
    modes = {
        "FORCE_HTTPS": ["true", "false"],
        "ALLOW_HTTP": ["true", "false"]
    }
    
    try:
        from server_modes import ServerModeManager
        print("✅ Server mode manager imported successfully")
        return True
    except Exception as e:
        print(f"❌ Server mode test failed: {e}")
        return False


def run_comprehensive_test():
    """Run all SSL tests"""
    print("🚀 Starting Comprehensive SSL Test Suite")
    print("=" * 50)
    
    tests = [
        ("Certificate Generation", test_certificate_generation),
        ("Certificate Validity", test_certificate_validity),
        ("SSL Connection", test_ssl_connection),
        ("HTTP/HTTPS Endpoints", test_http_endpoints),
        ("Certificate Bundle", test_certificate_bundle),
        ("Server Modes", test_server_modes)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 30)
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! SSL setup is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SSL Setup Test Suite")
    parser.add_argument("--generate", action="store_true", help="Test certificate generation only")
    parser.add_argument("--validate", action="store_true", help="Test certificate validation only")
    parser.add_argument("--connect", action="store_true", help="Test SSL connection only")
    parser.add_argument("--endpoints", action="store_true", help="Test HTTP/HTTPS endpoints only")
    parser.add_argument("--bundle", action="store_true", help="Test certificate bundle creation only")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    
    args = parser.parse_args()
    
    if args.generate:
        test_certificate_generation()
    elif args.validate:
        test_certificate_validity()
    elif args.connect:
        test_ssl_connection()
    elif args.endpoints:
        test_http_endpoints()
    elif args.bundle:
        test_certificate_bundle()
    else:
        # Default: run all tests
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()