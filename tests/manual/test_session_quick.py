#!/usr/bin/env python3
"""
Quick test to verify session configuration is working
"""

import sys
sys.path.append('.')

from flask import Flask
from session_config import configure_flask_sessions

# Create a test Flask app
app = Flask(__name__)
app.config['DEBUG'] = True

# Configure sessions
session_config = configure_flask_sessions(app)

# Test session configuration
print("Testing session configuration...")
health = session_config.health_check()

print(f"Session Config Status: {health['status']}")
print(f"Config Directory: {health['config_directory']}")
print(f"Session Lifetime: {health['session_lifetime']}")

print("\nSession Configuration Details:")
for check_name, check_result in health['checks'].items():
    status = "✅" if check_result else "❌"
    print(f"  {status} {check_name}: {check_result}")

if health['status'] == 'healthy':
    print("\n🎉 Session configuration is working correctly!")
else:
    print("\n⚠️ Session configuration has issues. Check the details above.")

print(f"\nFlask app configuration:")
print(f"  SECRET_KEY length: {len(app.config.get('SECRET_KEY', ''))}")
print(f"  SESSION_PERMANENT: {app.config.get('SESSION_PERMANENT')}")
print(f"  SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE')}")
print(f"  SESSION_COOKIE_HTTPONLY: {app.config.get('SESSION_COOKIE_HTTPONLY')}")