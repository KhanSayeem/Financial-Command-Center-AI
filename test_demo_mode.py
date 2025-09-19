"""
Comprehensive test to verify why the dashboard shows demo mode
"""
import sys
import os
import json
from pathlib import Path

def test_demo_mode_status():
    """Test the demo mode status and related configurations"""
    print("Testing demo mode status and configuration...")
    print("=" * 50)
    
    try:
        # Add current directory to path
        sys.path.insert(0, '.')
        
        # Import the app components
        from app_with_setup_wizard import XERO_AVAILABLE, xero, api_client
        from demo_mode import DemoModeManager
        
        print("1. Xero Status:")
        print(f"   XERO_AVAILABLE: {XERO_AVAILABLE}")
        print(f"   Xero client initialized: {'YES' if xero else 'NO'}")
        print(f"   API client initialized: {'YES' if api_client else 'NO'}")
        
        print("\n2. Demo Mode Manager:")
        demo_manager = DemoModeManager()
        current_mode = demo_manager.get_mode()
        is_demo = demo_manager.is_demo
        print(f"   Current mode: {current_mode}")
        print(f"   Is demo mode: {is_demo}")
        
        print("\n3. Mode File:")
        mode_file = Path('secure_config/app_mode.json')
        if mode_file.exists():
            mode_data = json.loads(mode_file.read_text())
            print(f"   Mode file content: {mode_data}")
        else:
            print(f"   Mode file not found")
            
        print("\n4. Environment Variables:")
        app_mode_env = os.getenv('APP_MODE')
        demo_mode_env = os.getenv('DEMO_MODE')
        print(f"   APP_MODE env: {app_mode_env}")
        print(f"   DEMO_MODE env: {demo_mode_env}")
        
        print("\n5. Integration Status:")
        from setup_wizard import get_integration_status
        integration_status = get_integration_status()
        print(f"   Integration status: {integration_status}")
        
        # Determine if there's a mismatch
        print("\n" + "=" * 50)
        print("ANALYSIS:")
        
        if current_mode == 'live' and XERO_AVAILABLE and xero and api_client:
            print("✓ Everything is properly configured for live mode")
            print("✓ Xero is available and initialized")
            print("✓ Demo mode is disabled")
            print("\nIf you're still seeing demo mode indicators, it might be:")
            print("1. A UI caching issue - try refreshing the page")
            print("2. A session-specific demo mode flag")
            print("3. A template that's hardcoded to show demo indicators")
        else:
            print("! There's a configuration issue:")
            if current_mode != 'live':
                print("  - App mode is not set to 'live'")
            if not XERO_AVAILABLE:
                print("  - XERO_AVAILABLE is False")
            if not xero:
                print("  - Xero client is not initialized")
            if not api_client:
                print("  - API client is not initialized")
                
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_demo_mode_status()