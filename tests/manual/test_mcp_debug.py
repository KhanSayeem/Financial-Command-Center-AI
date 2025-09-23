#!/usr/bin/env python3
"""
Simple test script for the MCP server
"""

import asyncio
import json
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_server import FinancialCommandCenterMCP

async def test_mcp_server():
    """Test the MCP server with a simple request"""
    server = FinancialCommandCenterMCP()
    
    # Create a test request
    test_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test",
                "version": "1.0.0"
            }
        }
    }
    
    print("Sending test request...")
    print(f"Request: {json.dumps(test_request, indent=2)}")
    
    try:
        # Test the handle_request method directly
        response = await server.handle_request(test_request)
        print(f"Response: {json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())