#!/usr/bin/env python3
"""
Quick test to see if browser will trust our mkcert certificates
"""

import subprocess
import time
import webbrowser
from pathlib import Path

def start_test_server():
    """Start the app for testing"""
    print("🚀 Starting Financial Command Center for certificate test...")
    print("📱 This will open your browser to test the certificate...")
    print("✅ Look for a GREEN LOCK in the browser address bar")
    print("❌ If you see 'Not Secure', the certificate isn't trusted yet")
    print()
    
    # Launch the application
    try:
        result = subprocess.run([
            "python", "financial_launcher.py"
        ], timeout=10)
    except subprocess.TimeoutExpired:
        print("✅ App started successfully!")
    except Exception as e:
        print(f"❌ Error starting app: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🔐 Browser Certificate Trust Test")
    print("   Financial Command Center AI")
    print("=" * 60)
    print()
    
    # Check if mkcert certs exist
    cert_file = Path("certs/server.crt")
    if cert_file.exists():
        print(f"✅ Certificate found: {cert_file}")
        print(f"   Generated with mkcert: {cert_file.stat().st_mtime}")
    else:
        print("❌ No certificate found - generating with mkcert first...")
        subprocess.run(["python", "cert_manager.py", "--mkcert"])
    
    print()
    print("🌐 Opening browser to test certificate trust...")
    print("⏰ The app will start and your browser will open automatically")
    print()
    
    start_test_server()