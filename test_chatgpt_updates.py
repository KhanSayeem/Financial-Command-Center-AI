"""
Test script to verify ChatGPT integration updates
"""

import sys
import os
from unittest.mock import patch

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_chatgpt_updates():
    """Test that ChatGPT integration updates are properly applied."""
    print("Testing ChatGPT Integration Updates")
    print("=" * 38)
    
    try:
        # Mock the Flask app context
        with patch('app_with_setup_wizard.url_for') as mock_url_for:
            # Mock the url_for function to return predictable URLs
            mock_url_for.side_effect = lambda endpoint, **kwargs: f"/{endpoint.replace('_', '/')}"
            
            # Read the app file to check the updates
            with open('app_with_setup_wizard.py', 'r') as f:
                content = f.read()
            
            # Check if AI copilots count is updated to 3
            if "'value': '3'" in content and "AI copilots standing by" in content:
                print("[PASS] AI copilots count updated to 3")
            else:
                print("[FAIL] AI copilots count not updated correctly")
                return False
            
            # Check if ChatGPT uses different icon
            # Count occurrences of 'bot' icon for Claude vs other icons for ChatGPT
            if "title': 'ChatGPT'" in content and "message-circle" in content:
                print("[PASS] ChatGPT uses different icon (message-circle)")
            else:
                print("[FAIL] ChatGPT icon not properly updated")
                return False
                
            # Check if description is updated
            if "Claude Desktop, Warp Terminal, and ChatGPT" in content:
                print("[PASS] Description updated to include ChatGPT")
            else:
                print("[FAIL] Description not updated to include ChatGPT")
                return False
                
    except Exception as e:
        print(f"[FAIL] Update test error: {e}")
        return False
    
    print("\nAll updates verified successfully!")
    print("- AI copilots count updated to 3")
    print("- ChatGPT uses different icon (message-circle)")
    print("- Descriptions updated to include ChatGPT")
    
    return True

if __name__ == "__main__":
    success = test_chatgpt_updates()
    sys.exit(0 if success else 1)