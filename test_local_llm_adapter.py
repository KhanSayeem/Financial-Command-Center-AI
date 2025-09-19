"""
Simple test script for the Local LLM MCP Adapter
This script tests the components without requiring a running LLM
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fcc-local-llm-adapter'))

try:
    # Test importing the adapter
    from fcc_local_llm_adapter.adapters.local_llm_mcp_adapter import LocalLLMMCPAdapter
    print("✓ LocalLLMMCPAdapter imported successfully")
    
    # Test importing the router
    from fcc_local_llm_adapter.utils.mcp_router import MCPRouter
    print("✓ MCPRouter imported successfully")
    
    # Test importing the tool schemas
    from fcc_local_llm_adapter.models.tool_schemas import all_tools
    print(f"✓ Tool schemas imported successfully ({len(all_tools)} tools available)")
    
    # Test importing the configuration
    from fcc_local_llm_adapter.config.settings import LLM_PROVIDER, LLM_MODEL, MCP_SERVER_URL
    print(f"✓ Configuration imported successfully")
    print(f"  LLM_PROVIDER: {LLM_PROVIDER}")
    print(f"  LLM_MODEL: {LLM_MODEL}")
    print(f"  MCP_SERVER_URL: {MCP_SERVER_URL}")
    
    print("\n✓ All components imported successfully!")
    print("\nTo test with a real LLM:")
    print("1. Install Ollama from https://ollama.com")
    print("2. Pull a model: ollama pull llama3.2")
    print("3. Run the example: python fcc-local-llm-adapter/example.py")
    
except Exception as e:
    print(f"✗ Error importing components: {e}")
    sys.exit(1)