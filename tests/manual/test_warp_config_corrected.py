#!/usr/bin/env python3
"""
Test the corrected Warp configuration format
"""
import sys
import json
sys.path.append('.')

from warp_integration import setup_warp_routes
from flask import Flask

def test_corrected_warp_config():
    """Test that the corrected Warp configuration has the right format"""
    print("Testing corrected Warp configuration format...")
    
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    setup_warp_routes(app)
    
    with app.test_client() as client:
        response = client.get('/api/warp/generate-config')
        
        if response.status_code == 200:
            data = response.get_json()
            if data and data.get('success'):
                config_json = data.get('config')
                if config_json:
                    config_obj = json.loads(config_json)
                    
                    print(f"✅ Configuration generated successfully")
                    print(f"📋 Structure keys: {list(config_obj.keys())}")
                    
                    if 'mcpServers' in config_obj:
                        servers = config_obj['mcpServers']
                        print(f"✅ Correct 'mcpServers' structure found")
                        print(f"🔧 Number of servers: {len(servers)}")
                        print(f"📝 Server names: {list(servers.keys())}")
                        
                        # Check one server structure
                        if servers:
                            first_server_name = list(servers.keys())[0]
                            first_server = servers[first_server_name]
                            print(f"\n📊 Sample server '{first_server_name}' structure:")
                            print(f"   • command: {first_server.get('command', 'MISSING')}")
                            print(f"   • args: {first_server.get('args', 'MISSING')}")
                            print(f"   • working_directory: {first_server.get('working_directory', 'MISSING')}")
                            print(f"   • env keys: {list(first_server.get('env', {}).keys())}")
                            
                            # Check if unnecessary fields are removed
                            unnecessary_fields = ['name', 'description', 'capabilities', 'tools', 'version', 'author']
                            clean_config = True
                            for field in unnecessary_fields:
                                if field in first_server:
                                    print(f"   ⚠️  Found unnecessary field: {field}")
                                    clean_config = False
                            
                            if clean_config:
                                print(f"   ✅ Clean server configuration (no unnecessary fields)")
                        
                        # Show the full configuration for comparison
                        print(f"\n🔍 Full generated configuration:")
                        print(json.dumps(config_obj, indent=2))
                        
                        return True
                    else:
                        print(f"❌ Missing 'mcpServers' key, found: {list(config_obj.keys())}")
                        return False
                else:
                    print(f"❌ No config data returned")
                    return False
            else:
                print(f"❌ API call failed: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False

if __name__ == "__main__":
    success = test_corrected_warp_config()
    sys.exit(0 if success else 1)