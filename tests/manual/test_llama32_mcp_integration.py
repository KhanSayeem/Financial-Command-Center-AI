#!/usr/bin/env python3
"""
Test script for Llama 3.2 MCP Integration
Verifies that the integration can properly call MCP tools through natural language
"""

import os
import sys
import json
import requests
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_llama32_connection():
    """Test connection to Llama 3.2 service."""
    try:
        base_url = os.getenv('LLAMA_BASE_URL', 'http://localhost:11434/v1')
        model = os.getenv('LLAMA_MODEL', 'llama3.2')

        logger.info(f"Testing connection to {base_url}")

        # Test models endpoint
        response = requests.get(f"{base_url}/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get("data", [])
            model_names = [model["id"] for model in models]
            logger.info(f"Available models: {model_names}")

            if model in model_names or f"{model}:latest" in model_names:
                logger.info(f"✓ Model '{model}' is available")
                return True
            else:
                logger.error(f"✗ Model '{model}' not found")
                return False
        else:
            logger.error(f"✗ Models endpoint returned {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
        return False

def test_mcp_tools_import():
    """Test that MCP tools can be imported."""
    try:
        # Add the adapter directory to Python path
        adapter_path = os.path.join(os.path.dirname(__file__), 'fcc-local-llm-adapter')
        if adapter_path not in sys.path:
            sys.path.insert(0, adapter_path)

        # Import with full module paths
        import importlib.util

        # Load mcp_router module
        router_spec = importlib.util.spec_from_file_location(
            "mcp_router",
            os.path.join(adapter_path, 'utils', 'mcp_router.py')
        )
        router_module = importlib.util.module_from_spec(router_spec)
        router_spec.loader.exec_module(router_module)
        MCPRouter = router_module.MCPRouter

        # Load tool_schemas module
        schemas_spec = importlib.util.spec_from_file_location(
            "tool_schemas",
            os.path.join(adapter_path, 'models', 'tool_schemas.py')
        )
        schemas_module = importlib.util.module_from_spec(schemas_spec)
        schemas_spec.loader.exec_module(schemas_module)
        all_tools = schemas_module.all_tools

        logger.info(f"✓ MCP Router imported successfully")
        logger.info(f"✓ Found {len(all_tools)} MCP tools")

        # List some available tools
        tool_names = [tool.get('function', {}).get('name', 'unknown') for tool in all_tools[:10]]
        logger.info(f"Sample tools: {tool_names}")

        return True, MCPRouter(), all_tools

    except Exception as e:
        logger.error(f"✗ MCP import failed: {e}")
        return False, None, []

def test_natural_language_processing():
    """Test natural language processing with MCP tools."""
    try:
        # Import the integration
        from fcc_llama32_integration import FCCLlama32Integration
        from flask import Flask

        # Create test Flask app
        app = Flask(__name__)

        # Initialize integration
        integration = FCCLlama32Integration(app)

        if not integration.client_available:
            logger.error("✗ Llama 3.2 not available for testing")
            return False

        if not integration.mcp_router:
            logger.error("✗ MCP Router not available for testing")
            return False

        logger.info("✓ Integration initialized successfully")

        # Test natural language queries
        test_queries = [
            "What's our current cash position?",
            "Show me the top 5 customers by revenue",
            "Get the latest profit and loss statement",
            "List any overdue invoices",
            "What's our financial health score?"
        ]

        for query in test_queries:
            logger.info(f"\n🧪 Testing query: '{query}'")

            # Create a test session
            session_id = 'test_session'
            integration.threads[session_id] = {
                'thread_id': 'test_thread',
                'messages': [{"role": "user", "content": query}]
            }

            # Process with MCP tools
            result = integration._process_with_mcp_tools(session_id)

            if result["success"]:
                logger.info(f"✓ Query processed successfully")
                logger.info(f"Response: {result['response'][:200]}...")
                logger.info(f"Turns used: {result.get('turns_used', 0)}")
            else:
                logger.error(f"✗ Query failed: {result.get('error', 'Unknown error')}")

        return True

    except Exception as e:
        logger.error(f"✗ Natural language processing test failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("🚀 Starting Llama 3.2 MCP Integration Tests")
    logger.info("=" * 60)

    # Test 1: Llama 3.2 connection
    logger.info("\n📡 Test 1: Llama 3.2 Connection")
    llama_ok = test_llama32_connection()

    # Test 2: MCP tools import
    logger.info("\n🔧 Test 2: MCP Tools Import")
    mcp_ok, mcp_router, tools = test_mcp_tools_import()

    # Test 3: Natural language processing (only if both previous tests pass)
    if llama_ok and mcp_ok:
        logger.info("\n🧠 Test 3: Natural Language Processing")
        nlp_ok = test_natural_language_processing()
    else:
        logger.warning("\n⚠️  Skipping natural language test due to previous failures")
        nlp_ok = False

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 Test Summary:")
    logger.info(f"  Llama 3.2 Connection: {'✓ PASS' if llama_ok else '✗ FAIL'}")
    logger.info(f"  MCP Tools Import:     {'✓ PASS' if mcp_ok else '✗ FAIL'}")
    logger.info(f"  Natural Language:     {'✓ PASS' if nlp_ok else '✗ FAIL'}")

    if llama_ok and mcp_ok and nlp_ok:
        logger.info("\n🎉 All tests passed! Llama 3.2 MCP integration is ready.")
        return True
    else:
        logger.error("\n❌ Some tests failed. Please check the configuration.")
        logger.info("\nTroubleshooting:")
        if not llama_ok:
            logger.info("  • Ensure Ollama/LM Studio is running")
            logger.info("  • Verify llama3.2 model is installed")
            logger.info("  • Check LLAMA_BASE_URL environment variable")
        if not mcp_ok:
            logger.info("  • Check that fcc-local-llm-adapter directory exists")
            logger.info("  • Verify MCP server dependencies are installed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)