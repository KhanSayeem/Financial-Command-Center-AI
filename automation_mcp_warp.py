# automation_mcp_warp.py
# Warp-compatible version of automation & workflows MCP
# Provides the same functionality but adapted for Warp terminal integration

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import date, timedelta, datetime

# Use the core automation module
from automation_mcp import (
    app as core_app,
    _get_automation_config,
    _save_json,
    _load_json,
    AUTOMATION_CONFIG_FILE,
    AUTOMATION_STORE_FILE,
    ROOT
)

def warp_format_response(data: Dict[str, Any], title: str = "") -> str:
    """Format response for Warp terminal with nice styling"""
    if not data.get("ok", False):
        return f"[ERROR] {data.get('error', 'Unknown error')}"

    output = []
    if title:
        output.append(f"## {title}")
        output.append("")

    # Format different response types
    if "reminders_sent" in data:
        output.append(f"**Payment Reminders Sent**: {data['reminders_sent']}")
        if data.get("next_run"):
            output.append(f"**Next Run**: {data['next_run']}")

    elif "suggestions" in data:
        output.append(f"**ML Categorization Results**")
        output.append(f"   - Suggestions: {data['suggestions']}")
        output.append(f"   - Auto-applied: {data['auto_applied']}")
        output.append(f"   - Confidence threshold: {data.get('confidence_threshold', 'N/A')}")

    elif "alert_triggered" in data:
        if data["alert_triggered"]:
            output.append(f"**LOW BALANCE ALERT**")
            output.append(f"   - Current: ${data['current_balance']:,.2f}")
            output.append(f"   - Threshold: ${data['threshold']:,.2f}")
            output.append(f"   - Recipients notified: {data.get('recipients_notified', 0)}")
        else:
            output.append(f"**Balance OK**: ${data['current_balance']:,.2f} (threshold: ${data['threshold']:,.2f})")

    elif "total_transactions" in data and "alerts_triggered" in data:
        output.append(f"**Transaction Monitoring**")
        output.append(f"   - Transactions checked: {data['total_transactions']}")
        output.append(f"   - Alerts triggered: {data['alerts_triggered']}")

        if data.get("alerts"):
            output.append(f"   - Alert details:")
            for alert in data["alerts"][:3]:  # Show first 3 alerts
                if alert["type"] == "large_transaction":
                    output.append(f"     - Large transaction: ${alert['amount']:,.2f} at {alert['merchant']}")
                elif alert["type"] == "payment_received":
                    output.append(f"     - Payment received: ${alert['amount']:,.2f} from {alert['merchant']}")

    elif "status" in data:
        status = data["status"]
        output.append(f"**Automation Status**")
        output.append(f"   - Scheduler running: {'YES' if status.get('scheduler_running') else 'NO'}")

        modules = status.get("automation_modules", {})
        output.append(f"   - Active modules:")
        for module, enabled in modules.items():
            status_text = "ENABLED" if enabled else "DISABLED"
            output.append(f"     - {module.replace('_', ' ').title()}: {status_text}")

    # Add file references if present
    if "results_file" in data:
        output.append(f"**Results saved**: `{Path(data['results_file']).name}`")

    return "\n".join(output)

# Warp-friendly wrapper functions
def warp_auto_send_payment_reminders():
    """Send payment reminders with Warp-formatted output"""
    from automation_mcp import auto_send_payment_reminders
    result = auto_send_payment_reminders()
    return warp_format_response(result, "Payment Reminders")

def warp_auto_categorize_expenses(key: str, days: int = 7):
    """Categorize expenses with ML and format for Warp"""
    from automation_mcp import auto_categorize_expenses
    result = auto_categorize_expenses(key=key, days=days)
    return warp_format_response(result, "AI Expense Categorization")

def warp_setup_low_balance_alerts(threshold: float, enabled: bool = True, recipients: List[str] = None):
    """Setup balance alerts with Warp formatting"""
    from automation_mcp import setup_low_balance_alerts
    result = setup_low_balance_alerts(threshold=threshold, enabled=enabled, recipients=recipients)
    return warp_format_response(result, "Low Balance Alerts")

def warp_monitor_transactions(key: str, hours: int = 24):
    """Monitor transactions with Warp formatting"""
    from automation_mcp import monitor_transactions
    result = monitor_transactions(key=key, hours=hours)
    return warp_format_response(result, "Transaction Monitoring")

def warp_get_automation_status():
    """Get automation status with Warp formatting"""
    from automation_mcp import get_automation_status
    result = get_automation_status()
    return warp_format_response(result, "Automation System Status")

def warp_check_balance_alerts(key: str):
    """Check balance alerts with Warp formatting"""
    from automation_mcp import check_balance_alerts
    result = check_balance_alerts(key=key)
    return warp_format_response(result, "Balance Check")

# Quick automation commands for Warp terminal
def quick_automation_dashboard():
    """Display a quick automation dashboard"""
    try:
        config = _get_automation_config()

        output = []
        output.append("# Financial Automation Dashboard")
        output.append("")

        # Status overview
        output.append("## System Status")
        modules = [
            ("Payment Reminders", config["payment_reminders"]["enabled"]),
            ("Expense Categorization", config["expense_categorization"]["enabled"]),
            ("Recurring Invoices", config["recurring_invoices"]["enabled"]),
            ("Low Balance Alerts", config["alerts"].get("low_balance_enabled", True)),
            ("Transaction Monitoring", config["alerts"].get("large_transaction_enabled", True))
        ]

        for name, enabled in modules:
            status = "ENABLED" if enabled else "DISABLED"
            output.append(f"- {name}: {status}")

        output.append("")

        # Key thresholds
        output.append("## Alert Thresholds")
        output.append(f"- Low Balance: ${config['alerts']['low_balance_threshold']:,.2f}")
        output.append(f"- Large Transaction: ${config['alerts']['large_transaction_threshold']:,.2f}")

        output.append("")

        # Quick actions
        output.append("## Quick Actions")
        output.append("```bash")
        output.append("# Send payment reminders")
        output.append("python automation_mcp_warp.py reminders")
        output.append("")
        output.append("# Check balance alerts")
        output.append("python automation_mcp_warp.py balance <account_key>")
        output.append("")
        output.append("# Monitor recent transactions")
        output.append("python automation_mcp_warp.py monitor <account_key>")
        output.append("")
        output.append("# Categorize expenses with AI")
        output.append("python automation_mcp_warp.py categorize <account_key>")
        output.append("```")

        return "\n".join(output)

    except Exception as e:
        return f"[ERROR] Error loading dashboard: {str(e)}"

def quick_setup_wizard():
    """Interactive setup wizard for automation"""
    output = []
    output.append("# Automation Setup Wizard")
    output.append("")
    output.append("## Step 1: Email Configuration")
    output.append("Set your email settings for notifications:")
    output.append("```json")
    output.append('{')
    output.append('  "smtp_server": "smtp.gmail.com",')
    output.append('  "smtp_port": 587,')
    output.append('  "sender_email": "your-email@gmail.com",')
    output.append('  "sender_password": "your-app-password",')
    output.append('  "recipients": ["notify@yourcompany.com"]')
    output.append('}')
    output.append("```")
    output.append("")

    output.append("## Step 2: Alert Thresholds")
    output.append("Configure your alert thresholds:")
    output.append("- **Low Balance**: Amount that triggers cash flow warnings")
    output.append("- **Large Transaction**: Amount that triggers unusual activity alerts")
    output.append("")

    output.append("## Step 3: Integration Setup")
    output.append("Ensure you have the required environment variables:")
    output.append("```bash")
    output.append("export PLAID_CLIENT_ID=your_plaid_client_id")
    output.append("export PLAID_SECRET=your_plaid_secret")
    output.append("export PLAID_ENV=sandbox  # or production")
    output.append("")
    output.append("# Optional:")
    output.append("export STRIPE_API_KEY=your_stripe_key")
    output.append("export XERO_CLIENT_ID=your_xero_client_id")
    output.append("```")
    output.append("")

    output.append("## Step 4: Start Automation")
    output.append("```bash")
    output.append("python automation_mcp_warp.py start")
    output.append("```")

    return "\n".join(output)

# Command line interface for Warp
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(quick_automation_dashboard())
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "dashboard":
        print(quick_automation_dashboard())

    elif command == "setup":
        print(quick_setup_wizard())

    elif command == "reminders":
        print(warp_auto_send_payment_reminders())

    elif command == "status":
        print(warp_get_automation_status())

    elif command == "balance":
        if len(sys.argv) < 3:
            print("[ERROR] Please provide account key")
            print("Usage: python automation_mcp_warp.py balance <account_key>")
        else:
            print(warp_check_balance_alerts(sys.argv[2]))

    elif command == "monitor":
        if len(sys.argv) < 3:
            print("[ERROR] Please provide account key")
            print("Usage: python automation_mcp_warp.py monitor <account_key> [hours]")
        else:
            hours = int(sys.argv[3]) if len(sys.argv) > 3 else 24
            print(warp_monitor_transactions(sys.argv[2], hours))

    elif command == "categorize":
        if len(sys.argv) < 3:
            print("[ERROR] Please provide account key")
            print("Usage: python automation_mcp_warp.py categorize <account_key> [days]")
        else:
            days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
            print(warp_auto_categorize_expenses(sys.argv[2], days))

    elif command == "start":
        from automation_mcp import start_automation_scheduler
        result = start_automation_scheduler()
        print(warp_format_response(result, "Starting Automation"))

    elif command == "stop":
        from automation_mcp import stop_automation_scheduler
        result = stop_automation_scheduler()
        print(warp_format_response(result, "Stopping Automation"))

    else:
        print(f"[ERROR] Unknown command: {command}")
        print("")
        print("Available commands:")
        print("- dashboard - Show automation overview")
        print("- setup - Show setup wizard")
        print("- status - Show system status")
        print("- reminders - Send payment reminders")
        print("- balance <key> - Check balance alerts")
        print("- monitor <key> [hours] - Monitor transactions")
        print("- categorize <key> [days] - Categorize expenses")
        print("- start - Start automation scheduler")
        print("- stop - Stop automation scheduler")