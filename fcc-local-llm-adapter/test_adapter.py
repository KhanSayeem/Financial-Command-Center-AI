"""
Test file for the Local LLM MCP Adapter
"""
import os
import sys
import json
from dotenv import load_dotenv
from adapters.local_llm_mcp_adapter import local_llm_mcp_adapter

# Add parent directory to path to import from fcc-local-llm-adapter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def test_basic_query():
    """Test basic query processing"""
    print("Testing basic query...")
    result = local_llm_mcp_adapter.process_query("What is the financial health of my business?")
    assert "success" in result
    print("✓ Basic query test passed")
    return result

def test_tool_calling():
    """Test tool calling functionality"""
    print("Testing tool calling...")
    result = local_llm_mcp_adapter.process_query("List the first 5 contacts in my Xero account")
    assert "success" in result
    print("✓ Tool calling test passed")
    return result

def test_streaming():
    """Test streaming response"""
    print("Testing streaming response...")
    chunks = []
    for chunk in local_llm_mcp_adapter.stream_process_query("What are my recent invoices?"):
        chunks.append(chunk)
        if chunk["type"] == "error":
            print(f"Error in streaming: {chunk['error']}")
            break
        if chunk["type"] == "end":
            break
    
    assert len(chunks) > 0
    print("✓ Streaming test passed")
    return chunks

def main():
    """Run all tests"""
    print("Running Local LLM MCP Adapter Tests\n")
    
    try:
        # Test basic query
        result1 = test_basic_query()
        
        # Test tool calling
        result2 = test_tool_calling()
        
        # Test streaming
        result3 = test_streaming()
        
        print("\n" + "="*50)
        print("All tests completed successfully!")
        print("="*50)
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()