#!/usr/bin/env python3
"""
Test Flask app with Warp integration
"""
import os
import sys
import requests
import json
import time
import threading

# Add current directory to path
sys.path.append('.')

def test_warp_flask_routes():
    """Test Flask app with Warp integration loaded"""
    print("🚀 Testing Flask App with Warp Integration")
    print("=" * 60)
    
    try:
        from warp_integration import setup_warp_routes
        from flask import Flask
        
        # Create Flask app
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-key-for-warp'
        app.config['TESTING'] = True
        
        # Setup Warp routes
        result = setup_warp_routes(app)
        print(f"✅ Warp routes setup: {result}")
        
        # Create test client
        with app.test_client() as client:
            print("\n🔍 Testing Warp routes:")
            
            # Test 1: Warp setup page
            print("  Testing /warp/setup...")
            response = client.get('/warp/setup')
            success = response.status_code == 200
            print(f"  {'✅' if success else '❌'} /warp/setup: {response.status_code}")
            if success:
                print(f"    📄 Response length: {len(response.data)} bytes")
                content = response.get_data(as_text=True)
                if 'Warp AI Terminal' in content:
                    print("    📝 Page content looks correct")
                else:
                    print("    ⚠️  Page content may be incorrect")
            
            # Test 2: Warp config generation API
            print("  Testing /api/warp/generate-config...")
            response = client.get('/api/warp/generate-config')
            success = response.status_code == 200
            print(f"  {'✅' if success else '❌'} /api/warp/generate-config: {response.status_code}")
            
            if success:
                try:
                    data = response.get_json()
                    if data and data.get('success'):
                        print(f"    📊 Generated config with {data.get('summary', {}).get('total_servers', 0)} servers")
                        config_data = data.get('config')
                        if config_data:
                            config_obj = json.loads(config_data)
                            print(f"    🔧 Config name: {config_obj.get('name', 'Unknown')}")
                            print(f"    📋 Servers: {list(config_obj.get('servers', {}).keys())}")
                    else:
                        print(f"    ⚠️  Config generation failed: {data.get('message', 'Unknown error')}")
                except Exception as e:
                    print(f"    ❌ Failed to parse config response: {e}")
            
        print("\n✅ Flask app with Warp integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_warp_flask_routes()
    sys.exit(0 if success else 1)