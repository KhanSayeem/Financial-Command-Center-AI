#!/usr/bin/env python3
"""Test script for the Financial Command Center MCP server"""
import subprocess
import json
import sys

def test_mcp_server():
    """Test the MCP server with various requests"""
    
    # Test initialize request
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0.0"}
        }
    }
    
    # Test tools/list request
    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    # Test prompts/list request
    prompts_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "prompts/list",
        "params": {}
    }
    
    # Test resources/list request
    resources_request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "resources/list",
        "params": {}
    }
    
    python_exe = ".venv\\Scripts\\python.exe"
    mcp_server = "mcp_server.py"
    
    # Create input for the MCP server
    input_data = (json.dumps(initialize_request) + "\n" + 
                 json.dumps(tools_request) + "\n" + 
                 json.dumps(prompts_request) + "\n" + 
                 json.dumps(resources_request) + "\n")
    
    try:
        # Start the MCP server process
        process = subprocess.Popen(
            [python_exe, mcp_server],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send requests and get responses
        stdout, stderr = process.communicate(input=input_data, timeout=10)
        
        print("🔍 MCP Server Test Results:")
        print("-" * 50)
        
        if stderr:
            print("📋 Server Logs:")
            for line in stderr.strip().split('\n'):
                if line.strip():
                    print(f"  {line}")
            print()
        
        print("📤 Responses:")
        for i, line in enumerate(stdout.strip().split('\n')):
            if line.strip():
                try:
                    response = json.loads(line)
                    print(f"  Response {i+1}: {response.get('result', {}).get('serverInfo', response.get('method', 'unknown'))}")
                    if 'tools' in response.get('result', {}):
                        tools = response['result']['tools']
                        print(f"  Available Tools: {len(tools)}")
                        for tool in tools:
                            print(f"    - {tool['name']}: {tool['description']}")
                except json.JSONDecodeError:
                    print(f"  Raw output: {line}")
        
        if process.returncode == 0:
            print("\n✅ MCP Server test successful!")
        else:
            print(f"\n❌ MCP Server test failed with return code: {process.returncode}")
            
    except subprocess.TimeoutExpired:
        process.kill()
        print("⏰ MCP Server test timed out")
    except Exception as e:
        print(f"❌ MCP Server test failed: {e}")

if __name__ == "__main__":
    test_mcp_server()