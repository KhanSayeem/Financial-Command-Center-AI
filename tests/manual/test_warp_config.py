#!/usr/bin/env python3
"""
Test script for Warp configuration generation
"""
import os
import sys
import json

# Add current directory to path
sys.path.append('.')

def test_warp_config_generation():
    """Test Warp configuration generation"""
    print("🚀 Testing Warp MCP Configuration Generation")
    print("=" * 60)
    
    try:
        # Import the Warp integration
        from warp_integration import setup_warp_routes
        from flask import Flask
        from setup_wizard import ConfigurationManager
        
        # Create Flask app
        app = Flask(__name__)
        
        # Setup Warp routes
        result = setup_warp_routes(app)
        print(f"✅ Warp routes setup: {result}")
        
        # Test configuration manager
        config_manager = ConfigurationManager()
        stored_config = config_manager.load_config() or {}
        
        print(f"📋 Current stored config keys: {list(stored_config.keys())}")
        
        # Simulate the config generation logic
        current_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"📁 Current directory: {current_dir}")
        
        # Check for Warp MCP server files
        warp_server_files = [
            "mcp_server_warp.py",
            "stripe_mcp_warp.py", 
            "plaid_mcp_warp.py",
            "xero_mcp_warp.py",
            "compliance_mcp_warp.py"
        ]
        
        print("\n🔍 Checking for Warp MCP server files:")
        found_servers = []
        for server_file in warp_server_files:
            server_path = os.path.join(current_dir, server_file)
            exists = os.path.exists(server_path)
            print(f"  {'✅' if exists else '❌'} {server_file}: {server_path}")
            if exists:
                found_servers.append(server_file)
        
        print(f"\n📊 Summary:")
        print(f"  • Found {len(found_servers)}/{len(warp_server_files)} Warp MCP servers")
        print(f"  • Configured services: {list(stored_config.keys())}")
        
        # Test Python path detection
        python_candidates = [
            os.path.join(current_dir, ".venv", "Scripts", "python.exe"),
            os.path.join(current_dir, ".venv", "bin", "python"),
            os.path.join(current_dir, "venv", "Scripts", "python.exe"),
            os.path.join(current_dir, "venv", "bin", "python"),
            "python",
            "python3"
        ]
        
        print(f"\n🐍 Python executable detection:")
        for candidate in python_candidates:
            if candidate in ["python", "python3"]:
                print(f"  🔧 {candidate}: system python (fallback)")
            else:
                exists = os.path.exists(candidate)
                print(f"  {'✅' if exists else '❌'} {candidate}")
        
        print("\n🎯 Warp configuration generation test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_warp_config_generation()