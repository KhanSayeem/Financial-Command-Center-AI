"""
Test script for ChatGPT integration
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_chatgpt_integration():
    """Test the ChatGPT integration components."""
    print("Testing ChatGPT Integration Components")
    print("=" * 40)
    
    # Test 1: Check if the integration module can be imported
    try:
        import chatgpt_integration
        print("[PASS] ChatGPT integration module imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import chatgpt_integration: {e}")
        return False
    
    # Test 2: Check if the template exists
    template_path = Path(__file__).parent / 'templates' / 'integrations' / 'chatgpt_setup.html'
    if template_path.exists():
        print("[PASS] ChatGPT setup template exists")
    else:
        print("[FAIL] ChatGPT setup template not found")
        return False
    
    # Test 3: Check if the FCC-OpenAI adapter is available
    adapter_path = Path(__file__).parent / 'fcc-openai-adapter'
    if adapter_path.exists():
        print("[PASS] FCC-OpenAI adapter directory exists")
    else:
        print("[FAIL] FCC-OpenAI adapter directory not found")
        return False
    
    # Test 4: Check if required adapter components exist
    required_files = [
        'adapters/openai_mcp_adapter.py',
        'models/tool_schemas.py',
        'utils/mcp_router.py',
        'config/settings.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = adapter_path / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"[FAIL] Missing adapter files: {missing_files}")
        return False
    else:
        print("[PASS] All required adapter components present")
    
    print("\nAll tests passed! ChatGPT integration is ready to use.")
    return True

if __name__ == "__main__":
    success = test_chatgpt_integration()
    sys.exit(0 if success else 1)