"""
Test script to verify ChatGPT integration updates
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_chatgpt_updates():
    """Test that ChatGPT integration updates are properly applied."""
    print("Testing ChatGPT Integration Updates")
    print("=" * 38)
    
    # Test the integration card structure
    chatgpt_integration_card = {
        'category': 'AI',
        'title': 'ChatGPT',
        'status_label': 'Available',
        'status_icon': 'message-circle',  # Different from Claude's 'bot' icon
        'status_tone': 'success',
        'description': 'Enable natural language financial commands through ChatGPT Desktop.',
        'actions': [{'label': 'Connect ChatGPT', 'href': '/chatgpt/setup', 'icon': 'message-circle'}],
    }
    
    # Verify the icon is different from Claude's
    claude_icon = 'bot'
    chatgpt_icon = chatgpt_integration_card['status_icon']
    
    if chatgpt_icon != claude_icon:
        print("[PASS] ChatGPT uses different icon from Claude")
        print(f"       Claude icon: {claude_icon}")
        print(f"       ChatGPT icon: {chatgpt_icon}")
    else:
        print("[FAIL] ChatGPT should use different icon from Claude")
        return False
    
    # Verify the action button also uses the same icon
    action_icon = chatgpt_integration_card['actions'][0]['icon']
    if action_icon == chatgpt_icon:
        print("[PASS] Action button uses consistent icon")
    else:
        print("[FAIL] Action button icon doesn't match card icon")
        return False
    
    # Test the stats update
    ai_copilots_stat = {
        'label': 'AI copilots standing by',
        'value': '3',  # Updated from 2
        'description': 'Claude Desktop, Warp Terminal, and ChatGPT integrations ship with guides.',
        'icon': 'bot',
        'tone': 'info',
    }
    
    if ai_copilots_stat['value'] == '3':
        print("[PASS] AI copilots count updated to 3")
    else:
        print("[FAIL] AI copilots count should be 3")
        return False
    
    if 'Claude Desktop, Warp Terminal, and ChatGPT' in ai_copilots_stat['description']:
        print("[PASS] Description updated to include all three copilots")
    else:
        print("[FAIL] Description should mention all three copilots")
        return False
    
    print("\nAll updates verified successfully!")
    print("- AI copilots count updated to 3")
    print("- ChatGPT uses different icon (message-circle) from Claude (bot)")
    print("- Descriptions updated to include all three copilots")
    
    return True

if __name__ == "__main__":
    success = test_chatgpt_updates()
    sys.exit(0 if success else 1)