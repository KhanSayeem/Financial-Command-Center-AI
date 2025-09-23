from pathlib import Path
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)

sys.path.insert(0, str(REPO_ROOT))

# simple_automation_test.py
# Quick test for automation tools

def test_basic_functionality():
    """Test basic automation functionality"""
    print("Testing Financial Automation & Workflows")
    print("=" * 50)

    # Test 1: Configuration Manager
    try:
        from automation_config_manager import AutomationConfigManager
        manager = AutomationConfigManager()
        config = manager.get_config_summary()
        print("[PASS] Configuration Manager: WORKING")
        print(f"   - Modules configured: {len(config.get('automation_modules', {}))}")
        print(f"   - Email configured: {config.get('email_configured', False)}")
    except Exception as e:
        print(f"[FAIL] Configuration Manager: FAILED - {e}")

    # Test 2: Warp Integration
    try:
        from automation_mcp_warp import quick_automation_dashboard, warp_format_response
        dashboard = quick_automation_dashboard()

        test_response = {"ok": True, "reminders_sent": 3}
        formatted = warp_format_response(test_response, "Test")

        print("[PASS] Warp Integration: WORKING")
        print(f"   - Dashboard keys: {list(dashboard.keys())[:3]}")
        print(f"   - Sample format: {formatted[:60]}...")
    except Exception as e:
        print(f"[FAIL] Warp Integration: FAILED - {e}")

    # Test 3: Automation Engine quick health
    try:
        from automation_mcp import automation_health_snapshot
        health = automation_health_snapshot()
        print("[PASS] Automation MCP: WORKING")
        print(f"   - Last run: {health.get('last_run')}")
        print(f"   - Pending jobs: {health.get('pending_jobs')}")
    except Exception as e:
        print(f"[FAIL] Automation MCP: FAILED - {e}")


if __name__ == "__main__":
    test_basic_functionality()
