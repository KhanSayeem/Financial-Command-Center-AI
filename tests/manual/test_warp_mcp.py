#!/usr/bin/env python3
"""
Test script for Warp-compatible MCP servers
This script tests all the Warp MCP servers to ensure they work correctly.
"""
import subprocess
import json
import sys
import os
import time
from typing import Dict, Any, List

def test_mcp_server(server_file: str, server_name: str, test_tools: List[str]) -> Dict[str, Any]:
    """Test a specific MCP server"""
    print(f"\n🔍 Testing {server_name}...")
    print("-" * 50)
    
    results = {
        "server": server_name,
        "file": server_file,
        "status": "unknown",
        "tools_tested": [],
        "errors": []
    }
    
    # Test initialize request
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "warp-test", "version": "1.0.0"}
        }
    }
    
    # Test tools/list request
    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    # Test ping tool if available
    ping_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "ping",
            "arguments": {}
        }
    }
    
    # Create initialized notification (required by MCP protocol)
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    
    # Create input for the MCP server - proper sequence
    input_data = (json.dumps(initialize_request) + "\n" + 
                 json.dumps(initialized_notification) + "\n" +
                 json.dumps(tools_request) + "\n" + 
                 json.dumps(ping_request) + "\n")
    
    python_exe = sys.executable
    
    try:
        # Start the MCP server process
        process = subprocess.Popen(
            [python_exe, server_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.abspath(server_file))
        )
        
        # Send requests and get responses
        stdout, stderr = process.communicate(input=input_data, timeout=20)
        
        print(f"📋 Server Logs for {server_name}:")
        if stderr:
            for line in stderr.strip().split('\n'):
                if line.strip():
                    print(f"  {line}")
        
        print(f"\n📤 Responses from {server_name}:")
        tools_found = []
        
        for i, line in enumerate(stdout.strip().split('\n')):
            if line.strip():
                try:
                    response = json.loads(line)
                    if 'result' in response:
                        if 'tools' in response['result']:
                            tools = response['result']['tools']
                            tools_found = [tool['name'] for tool in tools]
                            print(f"  ✅ Found {len(tools)} tools: {', '.join(tools_found)}")
                        elif 'serverInfo' in response['result']:
                            server_info = response['result']['serverInfo']
                            print(f"  ✅ Server Info: {server_info.get('name', 'Unknown')} v{server_info.get('version', 'Unknown')}")
                        elif response.get('id') == 3:  # ping response
                            print(f"  ✅ Ping successful: {response['result']}")
                            results["tools_tested"].append("ping")
                    elif 'error' in response:
                        error_msg = response['error'].get('message', 'Unknown error')
                        print(f"  ❌ Error: {error_msg}")
                        results["errors"].append(error_msg)
                except json.JSONDecodeError:
                    print(f"  📄 Raw output: {line}")
        
        if process.returncode == 0:
            results["status"] = "success"
            results["tools_tested"] = tools_found
            print(f"  ✅ {server_name} test successful!")
        else:
            results["status"] = "failed"
            results["errors"].append(f"Process exited with code {process.returncode}")
            print(f"  ❌ {server_name} test failed with return code: {process.returncode}")
            
    except subprocess.TimeoutExpired:
        process.kill()
        results["status"] = "timeout"
        results["errors"].append("Test timed out after 20 seconds")
        print(f"  ⏰ {server_name} test timed out")
    except FileNotFoundError:
        results["status"] = "not_found"
        results["errors"].append(f"Server file {server_file} not found")
        print(f"  ❌ {server_name} file not found: {server_file}")
    except Exception as e:
        results["status"] = "error"
        results["errors"].append(str(e))
        print(f"  ❌ {server_name} test failed: {e}")
    
    return results

def main():
    """Test all Warp MCP servers"""
    print("🚀 Testing Warp-Compatible MCP Servers")
    print("=" * 60)
    
    # Define servers to test
    servers_to_test = [
        {
            "file": "mcp_server_warp.py",
            "name": "Financial Command Center (Warp)",
            "tools": ["get_financial_health", "get_invoices", "get_contacts", "get_financial_dashboard", "get_cash_flow", "ping"]
        },
        {
            "file": "stripe_mcp_warp.py", 
            "name": "Stripe Integration (Warp)",
            "tools": ["process_payment", "check_payment_status", "create_customer", "ping"]
        },
        {
            "file": "plaid_mcp_warp.py",
            "name": "Plaid Integration (Warp)", 
            "tools": ["whoami", "list_items", "ping"]
        },
        {
            "file": "xero_mcp_warp.py",
            "name": "Xero Integration (Warp)",
            "tools": ["xero_whoami", "xero_list_contacts", "ping"]
        },
        {
            "file": "compliance_mcp_warp.py",
            "name": "Compliance Suite (Warp)",
            "tools": ["info", "blacklist_list", "ping"]
        }
    ]
    
    all_results = []
    
    for server in servers_to_test:
        result = test_mcp_server(server["file"], server["name"], server["tools"])
        all_results.append(result)
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 WARP MCP TEST SUMMARY")
    print("=" * 60)
    
    successful = 0
    failed = 0
    
    for result in all_results:
        status_icon = {
            "success": "✅",
            "failed": "❌", 
            "timeout": "⏰",
            "not_found": "🔍",
            "error": "💥"
        }.get(result["status"], "❓")
        
        print(f"{status_icon} {result['server']}: {result['status'].upper()}")
        
        if result["status"] == "success":
            successful += 1
            print(f"   Tools available: {len(result['tools_tested'])}")
        else:
            failed += 1
            if result["errors"]:
                print(f"   Errors: {'; '.join(result['errors'][:2])}")  # Show first 2 errors
    
    print(f"\n📈 Results: {successful} successful, {failed} failed out of {len(all_results)} servers")
    
    # Environment check
    print("\n🌍 ENVIRONMENT CHECK")
    print("-" * 30)
    env_vars = [
        "STRIPE_API_KEY", "PLAID_CLIENT_ID", "PLAID_SECRET", 
        "XERO_CLIENT_ID", "XERO_CLIENT_SECRET"
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 20)}")
        else:
            print(f"❌ {var}: Not set")
    
    # Final recommendations
    print(f"\n🎯 WARP INTEGRATION RECOMMENDATIONS")
    print("-" * 40)
    print("1. Set missing environment variables for full functionality")
    print("2. Use warp_mcp_config.json for Warp server discovery")
    print("3. Ensure all servers show 'SUCCESS' status before deploying")
    print("4. Test individual tools using Warp's MCP interface")
    
    if successful == len(all_results):
        print("\n🎉 All Warp MCP servers are ready for integration!")
        return 0
    else:
        print(f"\n⚠️  {failed} server(s) need attention before Warp integration")
        return 1

if __name__ == "__main__":
    sys.exit(main())