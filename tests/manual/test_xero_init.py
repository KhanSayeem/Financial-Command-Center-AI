"""
Test script to verify Xero client initialization
"""
import sys
import os

def test_xero_initialization():
    """Test if Xero client is properly initialized"""
    print("Testing Xero client initialization...")
    print("=" * 50)
    
    try:
        # Add current directory to path
        sys.path.insert(0, '.')
        
        # Import the app and check Xero status
        from app_with_setup_wizard import XERO_AVAILABLE, xero, api_client
        
        print(f"XERO_AVAILABLE: {XERO_AVAILABLE}")
        print(f"Xero client initialized: {'YES' if xero else 'NO'}")
        print(f"API client initialized: {'YES' if api_client else 'NO'}")
        
        if XERO_AVAILABLE and xero and api_client:
            print("\n✓ Xero is properly configured and available")
            print("✓ The assistant dashboard should show real data")
        else:
            print("\n! Xero is not properly initialized")
            print("! The assistant dashboard will show mock data")
            
            # Check why it's not available
            if not XERO_AVAILABLE:
                print("  - XERO_AVAILABLE is False")
            if not xero:
                print("  - Xero client is None")
            if not api_client:
                print("  - API client is None")
                
    except Exception as e:
        print(f"Error testing Xero initialization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_xero_initialization()