#!/usr/bin/env python3
"""
Diagnostic script for Financial Command Center MCP connection
"""
import json
import os
import subprocess
import time
from pathlib import Path

def check_financial_server():
    """Check if Financial Command Center server is running"""
    try:
        import requests
        import urllib3
        urllib3.disable_warnings()
        
        response = requests.get('https://localhost:8000/health', 
                              verify=False, timeout=5, 
                              headers={'Accept': 'application/json'})
        if response.status_code == 200:
            data = response.json()
            print("✅ Financial Command Center Server: RUNNING")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Version: {data.get('version', 'unknown')}")
            print(f"   Mode: {data.get('mode', 'unknown')}")
            return True
        else:
            print(f"❌ Financial Command Center Server: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Financial Command Center Server: NOT REACHABLE ({e})")
        return False

def check_mcp_server():
    """Test the MCP server directly"""
    try:
        python_exe = ".venv\\Scripts\\python.exe"
        if not os.path.exists(python_exe):
            python_exe = "python"
        
        # Simple initialize test
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "diagnostic", "version": "1.0.0"}
            }
        }
        
        process = subprocess.Popen(
            [python_exe, "mcp_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(
            input=json.dumps(init_request) + "\n", 
            timeout=10
        )
        
        if process.returncode == 0 and stdout.strip():
            try:
                response = json.loads(stdout.strip())
                if response.get('result', {}).get('serverInfo'):
                    print("✅ MCP Server: WORKING")
                    server_info = response['result']['serverInfo']
                    print(f"   Name: {server_info.get('name')}")
                    print(f"   Version: {server_info.get('version')}")
                    return True
            except json.JSONDecodeError:
                pass
        
        print("❌ MCP Server: FAILED")
        if stderr:
            print(f"   Error: {stderr[:200]}...")
        return False
        
    except Exception as e:
        print(f"❌ MCP Server: ERROR ({e})")
        return False

def check_claude_config():
    """Check Claude Desktop configuration"""
    config_path = Path(os.environ['APPDATA']) / "Claude" / "claude_desktop_config.json"
    
    if not config_path.exists():
        print("❌ Claude Desktop Config: NOT FOUND")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if 'financial-command-center' in config.get('mcpServers', {}):
            fcc_config = config['mcpServers']['financial-command-center']
            print("✅ Claude Desktop Config: CONFIGURED")
            print(f"   Command: {fcc_config.get('command', 'unknown')}")
            print(f"   Args: {fcc_config.get('args', [])}")
            
            # Check if paths exist
            command_path = fcc_config.get('command', '')
            if os.path.exists(command_path):
                print("   ✅ Python executable exists")
            else:
                print("   ❌ Python executable not found")
                return False
            
            args = fcc_config.get('args', [])
            if args and os.path.exists(args[0]):
                print("   ✅ MCP server script exists")
            else:
                print("   ❌ MCP server script not found")
                return False
            
            return True
        else:
            print("❌ Claude Desktop Config: financial-command-center not configured")
            return False
            
    except Exception as e:
        print(f"❌ Claude Desktop Config: ERROR ({e})")
        return False

def check_claude_logs():
    """Check recent Claude Desktop logs"""
    log_path = Path(os.environ['APPDATA']) / "Claude" / "logs" / "mcp-server-financial-command-center.log"
    
    if not log_path.exists():
        print("❌ Claude MCP Logs: NO LOG FILE")
        return False
    
    try:
        # Get last 10 lines
        with open(log_path, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-10:]
        
        print("📋 Recent Claude MCP Logs:")
        for line in recent_lines:
            line = line.strip()
            if line:
                # Show only relevant parts
                if any(keyword in line.lower() for keyword in ['error', 'failed', 'exception']):
                    print(f"   ❌ {line[-100:]}")
                elif 'successfully' in line.lower() or 'connected' in line.lower():
                    print(f"   ✅ {line[-100:]}")
                elif 'Message from server' in line:
                    print(f"   📡 Server response received")
        
        return True
        
    except Exception as e:
        print(f"❌ Claude MCP Logs: ERROR ({e})")
        return False

def main():
    print("🔍 Financial Command Center MCP Connection Diagnostic")
    print("=" * 60)
    
    # Check all components
    server_ok = check_financial_server()
    print()
    
    mcp_ok = check_mcp_server()
    print()
    
    config_ok = check_claude_config()
    print()
    
    check_claude_logs()
    print()
    
    # Summary
    print("📋 SUMMARY:")
    if server_ok and mcp_ok and config_ok:
        print("✅ All components are working!")
        print("📝 Next steps:")
        print("   1. Restart Claude Desktop completely")
        print("   2. Start a new conversation")
        print("   3. Try: 'Show me the financial health'")
    else:
        print("❌ Issues found that need to be resolved:")
        if not server_ok:
            print("   - Start Financial Command Center server")
        if not mcp_ok:
            print("   - Fix MCP server issues")
        if not config_ok:
            print("   - Fix Claude Desktop configuration")

if __name__ == "__main__":
    main()