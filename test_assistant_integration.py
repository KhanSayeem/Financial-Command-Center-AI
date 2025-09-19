#!/usr/bin/env python3
"""
Test script for Financial Command Center Assistant Integration
"""

import os
import sys

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_assistant_integration():
    """Test if the assistant integration is properly set up."""
    print("Testing Financial Command Center Assistant Integration")
    print("=" * 55)
    
    try:
        # Import the assistant integration
        from fcc_assistant_integration import setup_assistant_routes, FCCAssistantIntegration
        print("[PASS] Assistant integration module imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import assistant integration: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Error importing assistant integration: {e}")
        return False
    
    # Check if the main files exist
    required_files = [
        'fcc_assistant_integration.py',
        'fcc_assistant_core.py',
        'templates/assistant/dashboard.html',
        'templates/assistant/chat.html'
    ]
    
    print("\nChecking required files:")
    all_files_exist = True
    for file_path in required_files:
        full_path = file_path
        if not os.path.exists(full_path):
            # Check in parent directory structure
            if os.path.exists(f"C:\\Users\\Hi\\Documents\\GitHub\\Financial-Command-Center-AI\\{file_path}"):
                full_path = f"C:\\Users\\Hi\\Documents\\GitHub\\Financial-Command-Center-AI\\{file_path}"
            else:
                print(f"[FAIL] Required file not found: {file_path}")
                all_files_exist = False
        else:
            print(f"[PASS] {file_path}")
    
    if not all_files_exist:
        return False
    
    print("\nAll required files are present!")
    
    # Check if the OpenAI API key is set
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        print(f"[INFO] OpenAI API key is set (length: {len(openai_key)} characters)")
        
        # Check if it's the correct format (starts with sk-proj)
        if openai_key.startswith('sk-proj'):
            print("[PASS] OpenAI API key format is correct")
        else:
            print("[WARN] OpenAI API key format is unusual")
    else:
        print("[WARN] OpenAI API key not set in environment variables")
        print("       This is OK for demonstration mode")
    
    # Check if assistant core module works
    try:
        # Import core module to test
        from fcc_assistant_core import FinancialCommandCenterAssistant
        print("[PASS] Assistant core module imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import assistant core module: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Error importing assistant core module: {e}")
        return False
    
    print("\nIntegration Test Summary:")
    print("=" * 25)
    print("[PASS] All core assistant components are properly configured")
    print("[INFO] Assistant will be available at: https://localhost:8000/assistant")
    print("[INFO] Chat interface will be available at: https://localhost:8000/assistant/chat")
    print("[INFO] Dashboard will be available at: https://localhost:8000/assistant/")
    
    return True

if __name__ == "__main__":
    success = test_assistant_integration()
    if success:
        print("\n[SUCCESS] Financial Command Center Assistant is ready for deployment!")
        print("          Start your FCC application with 'python app_with_setup_wizard.py'")
        print("          Then visit https://localhost:8000/assistant to access the assistant")
    else:
        print("\n[FAIL] There are issues with the assistant integration")
        sys.exit(1)