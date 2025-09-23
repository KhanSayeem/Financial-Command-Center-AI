#!/usr/bin/env python3
"""
Test that all feature card icons are properly displayed
"""
import sys
sys.path.append('.')

from warp_integration import setup_warp_routes
from flask import Flask

def test_feature_icons():
    """Test that all feature cards have valid FontAwesome icons"""
    print("Testing feature card icons...")
    
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    setup_warp_routes(app)
    
    with app.test_client() as client:
        response = client.get('/warp/setup')
        content = response.get_data(as_text=True)
        
        # Expected feature cards and their icons
        feature_icons = [
            ('fa-robot', 'Natural Language'),
            ('fa-link', 'Command Chaining'),
            ('fa-chart-pie', 'Live Insights'),
            ('fa-cogs', 'Custom Workflows')
        ]
        
        print("\nChecking feature card icons:")
        all_icons_found = True
        
        for icon_class, feature_name in feature_icons:
            if icon_class in content:
                print(f"  ✅ {feature_name}: {icon_class}")
            else:
                print(f"  ❌ {feature_name}: {icon_class} - MISSING")
                all_icons_found = False
        
        # Check main service feature cards too
        service_icons = [
            ('fa-chart-line', 'Financial Command Center'),
            ('fa-stripe', 'Stripe Payments'),  # This might be fab fa-stripe
            ('fa-university', 'Plaid Banking'),
            ('fa-calculator', 'Xero Accounting'),
            ('fa-shield-alt', 'Compliance Suite')
        ]
        
        print("\nChecking service feature card icons:")
        for icon_class, service_name in service_icons:
            if icon_class in content or f"fab {icon_class}" in content:
                print(f"  ✅ {service_name}: {icon_class}")
            else:
                print(f"  ❌ {service_name}: {icon_class} - CHECK NEEDED")
        
        print(f"\n{'✅ All feature icons properly configured!' if all_icons_found else '❌ Some icons need attention'}")
        return all_icons_found

if __name__ == "__main__":
    test_feature_icons()