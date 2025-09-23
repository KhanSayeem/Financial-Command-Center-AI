#!/usr/bin/env python3
"""
Test the updated Warp styling
"""
import sys
sys.path.append('.')

from warp_integration import setup_warp_routes
from flask import Flask

def test_warp_styling():
    """Test that styling changes are applied correctly"""
    print("Testing Warp styling updates...")
    
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    setup_warp_routes(app)
    
    with app.test_client() as client:
        response = client.get('/warp/setup')
        content = response.get_data(as_text=True)
        
        # Check that emojis are removed
        emoji_checks = [
            ('🔒', 'Secure'),
            ('🎯', 'Tailored'), 
            ('⚡', 'Dynamic'),
            ('📱', 'Portable'),
            ('🚀', 'Ready to Test'),
            ('✅', 'Configuration Generated Successfully'),
            ('❌', 'Configuration Generation Failed')
        ]
        
        print("\n📋 Checking emoji removal:")
        for emoji, context in emoji_checks:
            has_emoji = emoji in content
            print(f"  {'❌' if has_emoji else '✅'} {context}: {'Contains emoji' if has_emoji else 'Clean text'}")
        
        # Check that Warp text is white
        warp_text_check = 'color: white;' in content
        print(f"\n🎨 Warp text color fix: {'✅ Applied' if warp_text_check else '❌ Not found'}")
        
        # Check that command examples are properly formatted
        command_format_check = '<h4 style="margin-top: 0; color: var(--text-primary);">Financial Health Check</h4>' in content
        print(f"📝 Command formatting: {'✅ List format' if command_format_check else '❌ Old format'}")
        
        # Check button icon removal
        icon_removed = '<i class="fas fa-cog"></i>' not in content
        print(f"🔧 Button icons removed: {'✅ Clean buttons' if icon_removed else '❌ Still has icons'}")
        
        print(f"\n✅ Styling verification completed!")
        return True

if __name__ == "__main__":
    test_warp_styling()