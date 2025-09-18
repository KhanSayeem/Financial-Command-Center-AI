"""
Test script to verify admin dashboard quick links
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.dashboard import build_admin_dashboard_context
from dataclasses import dataclass

@dataclass
class MockDemoManager:
    is_demo = False

def test_quick_links():
    """Test that the quick links include ChatGPT."""
    context = build_admin_dashboard_context(True, None, MockDemoManager())
    
    print("Admin Dashboard Quick Links:")
    print("=" * 30)
    
    for i, link in enumerate(context.quick_links, 1):
        print(f"{i}. {link['label']}")
        print(f"   {link['description']}")
        print(f"   {link['href']}")
        print()
    
    # Check if ChatGPT link is present
    chatgpt_link = next((link for link in context.quick_links if 'chatgpt' in link['href'].lower()), None)
    if chatgpt_link:
        print("[PASS] ChatGPT integration link found in admin dashboard")
        return True
    else:
        print("[FAIL] ChatGPT integration link not found in admin dashboard")
        return False

if __name__ == "__main__":
    success = test_quick_links()
    sys.exit(0 if success else 1)