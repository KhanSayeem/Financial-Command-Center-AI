#!/usr/bin/env python3
"""
Generate a sample Warp configuration to test the generator
"""
import json
import os

def generate_sample_warp_config():
    """Generate sample Warp configuration"""
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = os.path.join(current_dir, ".venv", "Scripts", "python.exe")
    
    sample_config = {
        "name": "Financial Command Center AI - Warp MCP Suite",
        "version": "1.0.0",
        "description": "Complete suite of Warp-compatible MCP servers for financial management, payment processing, banking, accounting, and compliance",
        "author": "Financial Command Center AI",
        "servers": {
            "financial-command-center-warp": {
                "name": "Financial Command Center (Warp)",
                "description": "Main financial dashboard and health monitoring",
                "command": python_exe,
                "args": [os.path.join(current_dir, "mcp_server_warp.py")],
                "working_directory": None,
                "env": {
                    "FCC_SERVER_URL": "https://localhost:8000",
                    "FCC_API_KEY": "claude-desktop-integration"
                },
                "capabilities": ["tools"],
                "tools": [
                    "get_financial_health",
                    "get_invoices", 
                    "get_contacts",
                    "get_financial_dashboard",
                    "get_cash_flow",
                    "ping"
                ]
            },
            "stripe-integration-warp": {
                "name": "Stripe Integration (Warp)",
                "description": "Complete Stripe payment processing, subscriptions, customers, and webhooks",
                "command": python_exe,
                "args": [os.path.join(current_dir, "stripe_mcp_warp.py")],
                "working_directory": None,
                "env": {
                    "STRIPE_API_KEY": "sk_test_your_stripe_key_here",
                    "STRIPE_API_VERSION": "2024-06-20",
                    "STRIPE_DEFAULT_CURRENCY": "usd",
                    "MCP_STRIPE_PROD": "false"
                },
                "capabilities": ["tools"],
                "tools": [
                    "process_payment", "check_payment_status", "process_refund",
                    "capture_payment_intent", "cancel_payment_intent", "create_customer",
                    "create_setup_intent", "list_payment_methods", "attach_payment_method",
                    "detach_payment_method", "create_product", "create_price",
                    "create_checkout_session", "create_subscription", "cancel_subscription",
                    "list_payments", "retrieve_charge", "retrieve_refund", "verify_webhook", "ping"
                ]
            },
            "plaid-integration-warp": {
                "name": "Plaid Integration (Warp)",
                "description": "Bank account connections, transactions, balances, and financial data",
                "command": python_exe,
                "args": [os.path.join(current_dir, "plaid_mcp_warp.py")],
                "working_directory": None,
                "env": {
                    "PLAID_CLIENT_ID": "your_plaid_client_id",
                    "PLAID_SECRET": "your_plaid_secret",
                    "PLAID_ENV": "sandbox"
                },
                "capabilities": ["tools"],
                "tools": [
                    "link_token_create", "sandbox_public_token_create", "item_public_token_exchange",
                    "accounts_and_balances", "list_items", "transactions_get", "auth_get",
                    "identity_get", "remove_item", "whoami", "ping"
                ]
            },
            "xero-mcp-warp": {
                "name": "Xero Integration (Warp)",
                "description": "Xero accounting integration for invoices, contacts, and financial reports",
                "command": python_exe,
                "args": [os.path.join(current_dir, "xero_mcp_warp.py")],
                "working_directory": None,
                "env": {
                    "XERO_CLIENT_ID": "your_xero_client_id",
                    "XERO_CLIENT_SECRET": "your_xero_client_secret"
                },
                "capabilities": ["tools"],
                "tools": [
                    "xero_whoami", "xero_set_tenant", "xero_list_contacts", "xero_create_contact",
                    "xero_get_invoice_pdf", "xero_org_info", "xero_find_contact", "xero_list_invoices",
                    "xero_delete_draft_invoice", "xero_export_invoices_csv", "xero_dashboard", "ping"
                ]
            },
            "compliance-suite-warp": {
                "name": "Compliance Suite (Warp)",
                "description": "Financial compliance monitoring, transaction scanning, blacklists, and audit logs",
                "command": python_exe,
                "args": [os.path.join(current_dir, "compliance_mcp_warp.py")],
                "working_directory": None,
                "env": {
                    "PLAID_CLIENT_ID": "your_plaid_client_id",
                    "PLAID_SECRET": "your_plaid_secret",
                    "PLAID_ENV": "sandbox",
                    "STRIPE_API_KEY": "sk_test_your_stripe_key_here"
                },
                "capabilities": ["tools"],
                "tools": [
                    "info", "config_set", "blacklist_add", "blacklist_list",
                    "scan_plaid_transactions", "audit_log_tail", "stripe_payment_intent_status", "ping"
                ]
            }
        },
        "environment_variables": {
            "required": ["STRIPE_API_KEY", "PLAID_CLIENT_ID", "PLAID_SECRET", "XERO_CLIENT_ID", "XERO_CLIENT_SECRET"],
            "optional": ["FCC_SERVER_URL", "FCC_API_KEY", "STRIPE_API_VERSION", "STRIPE_DEFAULT_CURRENCY", "MCP_STRIPE_PROD", "PLAID_ENV"],
            "descriptions": {
                "STRIPE_API_KEY": "Stripe API key (sk_test_... or sk_live_...)",
                "PLAID_CLIENT_ID": "Plaid client ID from Plaid dashboard",
                "PLAID_SECRET": "Plaid secret key from Plaid dashboard",
                "XERO_CLIENT_ID": "Xero OAuth2 client ID",
                "XERO_CLIENT_SECRET": "Xero OAuth2 client secret",
                "FCC_SERVER_URL": "Financial Command Center server URL (default: https://127.0.0.1:8000)",
                "FCC_API_KEY": "API key for Financial Command Center (default: claude-desktop-integration)",
                "STRIPE_API_VERSION": "Stripe API version (default: 2024-06-20)",
                "STRIPE_DEFAULT_CURRENCY": "Default currency for Stripe operations (default: usd)",
                "MCP_STRIPE_PROD": "Set to 'true' for production mode (default: false)",
                "PLAID_ENV": "Plaid environment: sandbox, development, or production (default: sandbox)"
            }
        },
        "setup_instructions": {
            "1": "Install dependencies: pip install mcp fastmcp stripe plaid-python xero-python httpx python-jose",
            "2": "Set required environment variables in your shell or .env file",
            "3": "For Xero: Complete OAuth2 setup and obtain tenant ID via Flask app",
            "4": "For Plaid: Create sandbox accounts and exchange public tokens",
            "5": "Start the Financial Command Center server (if using main MCP server)",
            "6": "Configure Warp to discover and connect to these MCP servers"
        },
        "warp_config": {
            "discovery_method": "file",
            "servers_directory": current_dir,
            "auto_start": True,
            "health_check_interval": 30,
            "restart_on_failure": True
        }
    }
    
    output_file = os.path.join(current_dir, "sample_warp_mcp_config_generated.json")
    with open(output_file, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print(f"✅ Sample Warp configuration generated: {output_file}")
    print(f"📊 Configuration includes {len(sample_config['servers'])} MCP servers")
    print(f"🔧 Python executable: {python_exe}")
    
    return output_file

if __name__ == "__main__":
    generate_sample_warp_config()