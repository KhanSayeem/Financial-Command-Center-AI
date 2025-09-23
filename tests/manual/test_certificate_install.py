#!/usr/bin/env python3
"""
Certificate Installation Test
Tests and guides users through certificate installation process
"""

import os
import sys
import ssl
import socket
import subprocess
from pathlib import Path
import requests
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def test_certificate_generation():
    """Test certificate generation"""
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
        
        if health['certificate_valid']:
            print(f"   Certificate expires: {health['expires']}")
            print(f"   Hostnames: {', '.join(health['hostnames'])}")
            return True
        else:
            print("   ❌ Certificate generation failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def create_certificate_bundle():
    """Create certificate installation bundle"""
    print("\n📦 Creating Certificate Bundle...")
    
    try:
        from cert_manager import CertificateManager
        cert_manager = CertificateManager()
        
        bundle_dir = cert_manager.create_client_bundle()
        print(f"   ✅ Bundle created at: {bundle_dir}")
        
        # List bundle contents
        print("   Bundle contents:")
        for file_path in bundle_dir.iterdir():
            if file_path.is_file():
                size = file_path.stat().st_size
                print(f"     - {file_path.name} ({size} bytes)")
        
        return str(bundle_dir)
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def test_ssl_connection():
    """Test SSL connection to localhost:8000"""
    print("\n🌐 Testing SSL Connection...")
    
    try:
        # Test basic SSL handshake
        print("   Testing SSL handshake...")
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection(("localhost", 8000), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname="localhost") as ssock:
                print(f"   ✅ SSL handshake successful")
                print(f"   SSL Version: {ssock.version()}")
                return True
                
    except socket.timeout:
        print("   ❌ Connection timeout - is the server running?")
        return False
    except Exception as e:
        print(f"   ❌ SSL connection failed: {e}")
        return False


def test_https_request():
    """Test HTTPS request to the application"""
    print("\n🔗 Testing HTTPS Request...")
    
    try:
        # Test with certificate verification disabled (should always work)
        response = requests.get("https://localhost:8000/health", verify=False, timeout=5)
        print(f"   ✅ HTTPS request successful (status: {response.status_code})")
        
        # Test with certificate verification enabled (will fail if not trusted)
        try:
            response_verified = requests.get("https://localhost:8000/health", verify=True, timeout=5)
            print("   ✅ Certificate is trusted by system!")
            return "trusted"
        except requests.exceptions.SSLError:
            print("   ⚠️  Certificate not trusted yet - needs installation")
            return "not_trusted"
            
    except Exception as e:
        print(f"   ❌ HTTPS request failed: {e}")
        return "failed"


def show_installation_instructions(bundle_path):
    """Show platform-specific installation instructions"""
    print(f"\n📋 Certificate Installation Instructions")
    print("=" * 50)
    
    if os.name == 'nt':  # Windows
        print("🪟 Windows Installation:")
        print(f"1. Navigate to: {bundle_path}")
        print("2. Right-click 'install_certificate_windows.bat'")
        print("3. Select 'Run as administrator'")
        print("4. Follow the prompts")
        print("5. Restart your browser completely")
        print()
        print("Alternative manual method:")
        print("1. Open 'certlm.msc' as administrator")
        print("2. Navigate to: Trusted Root Certification Authorities > Certificates")
        print("3. Right-click > All Tasks > Import")
        print("4. Browse to: ca_certificate.crt in the bundle folder")
        
    else:  # Unix-like
        print("🐧 Unix/Linux/macOS Installation:")
        print(f"1. Open Terminal")
        print(f"2. Navigate to: {bundle_path}")
        print("3. Run: ./install_certificate_unix.sh")
        print("4. Enter your password when prompted")
        print("5. Restart your browser completely")
    
    print(f"\n📂 Bundle Location: {bundle_path}")


def main():
    """Main test and installation guide"""
    print("🔐 Certificate Installation Test & Guide")
    print("=" * 50)
    print()
    
    # Test certificate generation
    cert_success = test_certificate_generation()
    if not cert_success:
        print("\n❌ Certificate generation failed. Cannot proceed.")
        return False
    
    # Create bundle
    bundle_path = create_certificate_bundle()
    if not bundle_path:
        print("\n❌ Bundle creation failed. Cannot proceed.")
        return False
    
    # Test SSL connection
    ssl_success = test_ssl_connection()
    if not ssl_success:
        print("\n❌ SSL connection failed. Make sure the server is running.")
        print("Start the server with: python app.py")
        return False
    
    # Test HTTPS request
    https_status = test_https_request()
    
    if https_status == "trusted":
        print("\n🎉 Success! Certificate is already trusted.")
        print("You should be able to access https://localhost:8000 without warnings.")
        return True
    
    elif https_status == "not_trusted":
        print("\n📋 Certificate needs to be installed to eliminate browser warnings.")
        show_installation_instructions(bundle_path)
        
        print(f"\n🔧 Next Steps:")
        print("1. Follow the installation instructions above")
        print("2. Restart your browser completely")
        print("3. Visit https://localhost:8000")
        print("4. The warning should be gone!")
        
        return True
    
    else:
        print("\n❌ HTTPS requests are failing. Check your server configuration.")
        return False


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print(f"\n✅ Test completed successfully!")
        else:
            print(f"\n❌ Test failed. Check the output above for details.")
        
        input("\nPress Enter to exit...")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")