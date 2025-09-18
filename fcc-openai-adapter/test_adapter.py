"""
Test script for the FCC-OpenAI adapter.
"""

import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.openai_mcp_adapter import openai_mcp_adapter
from utils.mcp_router import mcp_router

def test_mcp_router():
    """Test the MCP router functionality."""
    print("Testing MCP Router...")
    print("-" * 30)
    
    # Test available tools
    tools = mcp_router.get_available_tools()
    print(f"Available tools: {len(tools)}")
    print(f"Sample tools: {tools[:5]}")
    
    # Test routing (this will fail if MCP server is not running)
    print("\nTesting tool routing (requires MCP server)...")
    try:
        result = mcp_router.route_tool_call("xero_ping", {})
        print(f"Ping result: {result}")
    except Exception as e:
        print(f"Ping failed (expected if server not running): {e}")

def test_openai_adapter():
    """Test the OpenAI adapter."""
    print("\nTesting OpenAI Adapter...")
    print("-" * 30)
    
    # Test initialization
    print(f"Adapter model: {openai_mcp_adapter.model}")
    print(f"Max turns: {openai_mcp_adapter.max_turns}")

if __name__ == "__main__":
    test_mcp_router()
    test_openai_adapter()
    print("\nTest completed!")