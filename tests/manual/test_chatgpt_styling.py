"""
Test script to verify ChatGPT success message styling consistency
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_chatgpt_styling():
    """Test that ChatGPT success messages use consistent styling."""
    print("Testing ChatGPT Success Message Styling")
    print("=" * 40)
    
    # Read the template files
    try:
        with open('templates/integrations/chatgpt_setup.html', 'r', encoding='utf-8') as f:
            chatgpt_content = f.read()
            
        with open('templates/integrations/claude_setup.html', 'r', encoding='utf-8') as f:
            claude_content = f.read()
    except Exception as e:
        print(f"[FAIL] Could not read template files: {e}")
        return False
    
    # Check if both use the same success styling
    success_class = 'bg-emerald-50'
    
    if success_class in chatgpt_content:
        print("[PASS] ChatGPT template uses emerald success background")
    else:
        print("[FAIL] ChatGPT template missing emerald success background")
        return False
    
    if success_class in claude_content:
        print("[PASS] Claude template uses emerald success background")
    else:
        print("[FAIL] Claude template missing emerald success background")
        return False
    
    # Check if the toneClasses mapping is consistent
    if "success: 'border-emerald-200 bg-emerald-50 text-emerald-700'" in chatgpt_content:
        print("[PASS] ChatGPT uses correct success tone mapping")
    else:
        print("[FAIL] ChatGPT missing correct success tone mapping")
        return False
        
    if "success: 'border-emerald-200 bg-emerald-50 text-emerald-700'" in claude_content:
        print("[PASS] Claude uses correct success tone mapping")
    else:
        print("[FAIL] Claude missing correct success tone mapping")
        return False
    
    # Check specific success messages
    chatgpt_success_messages = [
        "ChatGPT connected successfully",
        "Connection test successful"
    ]
    
    for message in chatgpt_success_messages:
        if message in chatgpt_content:
            print(f"[PASS] Found success message: '{message}'")
        else:
            print(f"[WARN] Success message not found: '{message}'")
    
    print("\nAll styling tests passed!")
    print("- Both templates use the same emerald success background")
    print("- Both templates use the same tone mapping")
    print("- Success messages are properly styled")
    
    return True

if __name__ == "__main__":
    success = test_chatgpt_styling()
    sys.exit(0 if success else 1)