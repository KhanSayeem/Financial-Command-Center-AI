"""
MCP Router for routing GPT-4o function calls to MCP tools directly.
Routes tool calls to the appropriate MCP modules and executes them.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import importlib.util
import logging

logger = logging.getLogger(__name__)

class MCPRouter:
    def __init__(self):
        """
        Initialize the MCP Router to call MCP tools directly.
        """
        self.xero_mcp = None
        self._load_mcp_modules()

    def _load_mcp_modules(self):
        """Load MCP modules directly."""
        try:
            # Get the project root directory
            project_root = Path(__file__).parents[2]  # Go up from fcc-openai-adapter/utils/
            xero_mcp_path = project_root / "xero_mcp_warp.py"

            if xero_mcp_path.exists():
                # Load the xero_mcp_warp module
                spec = importlib.util.spec_from_file_location("xero_mcp_warp", xero_mcp_path)
                if spec and spec.loader:
                    xero_mcp_module = importlib.util.module_from_spec(spec)
                    sys.modules["xero_mcp_warp"] = xero_mcp_module
                    spec.loader.exec_module(xero_mcp_module)
                    self.xero_mcp = xero_mcp_module
                    logger.info("Successfully loaded Xero MCP module")
                else:
                    logger.error("Failed to create module spec for xero_mcp_warp")
            else:
                logger.error(f"Xero MCP module not found at {xero_mcp_path}")

        except Exception as e:
            logger.error(f"Failed to load MCP modules: {e}")

        # Map tool names to their respective MCP function names
        self.tool_to_function_map = {
            # Xero tools - mapping to actual function names in xero_mcp_warp.py
            'xero_ping': 'ping',
            'xero_whoami': 'xero_whoami',
            'xero_set_tenant': 'xero_set_tenant',
            'xero_list_contacts': 'xero_list_contacts',
            'xero_create_contact': 'xero_create_contact',
            'xero_get_invoice_pdf': 'xero_get_invoice_pdf',
            'xero_org_info': 'xero_org_info',
            'xero_find_contact': 'xero_find_contact',
            'xero_list_invoices': 'xero_list_invoices',
            'xero_delete_draft_invoice': 'xero_delete_draft_invoice',
            'xero_export_invoices_csv': 'xero_export_invoices_csv',
            'xero_create_invoice': 'xero_create_invoice',
            'xero_duplicate_invoice': 'xero_duplicate_invoice',
            'xero_send_invoice_email': 'xero_send_invoice_email',
            'xero_authorise_invoice': 'xero_authorise_invoice',
            'xero_create_payment': 'xero_create_payment',
            'xero_apply_payment_to_invoice': 'xero_apply_payment_to_invoice',
            'xero_get_profit_loss': 'xero_get_profit_loss',
            'xero_get_balance_sheet': 'xero_get_balance_sheet',
            'xero_get_aged_receivables': 'xero_get_aged_receivables',
            'xero_get_cash_flow_statement': 'xero_get_cash_flow_statement',
            'xero_bulk_create_invoices': 'xero_bulk_create_invoices',
            'xero_export_chart_of_accounts': 'xero_export_chart_of_accounts',
            'xero_dashboard': 'xero_dashboard',
            'xero_process_stripe_payment_data': 'xero_process_stripe_payment_data',
            'xero_import_bank_feed': 'xero_import_bank_feed',
            'xero_auto_categorize_transactions': 'xero_auto_categorize_transactions',

            # Financial Command Center tools (these may need to be implemented)
            'get_financial_health': 'get_financial_health',
            'get_invoices': 'mcp_server_warp.py',
            'get_contacts': 'mcp_server_warp.py',
            'get_financial_dashboard': 'mcp_server_warp.py',
            'get_cash_flow': 'mcp_server_warp.py',
            'get_financial_ratios': 'mcp_server_warp.py',
            'forecast_revenue': 'mcp_server_warp.py',
            'analyze_expenses': 'mcp_server_warp.py',
            'generate_financial_report': 'mcp_server_warp.py',
            
            # Stripe tools
            'process_payment': 'stripe_mcp_warp.py',
            'check_payment_status': 'stripe_mcp_warp.py',
            'create_customer': 'stripe_mcp_warp.py',
            'list_customers': 'stripe_mcp_warp.py',
            'create_product': 'stripe_mcp_warp.py',
            'list_products': 'stripe_mcp_warp.py',
            'create_subscription': 'stripe_mcp_warp.py',
            'cancel_subscription': 'stripe_mcp_warp.py',
            
            # Plaid tools
            'plaid_whoami': 'plaid_mcp_warp.py',
            'plaid_list_items': 'plaid_mcp_warp.py',
            'plaid_get_accounts': 'plaid_mcp_warp.py',
            'plaid_get_transactions': 'plaid_mcp_warp.py',
            'plaid_get_balance': 'plaid_mcp_warp.py',
            'plaid_get_identity': 'plaid_mcp_warp.py',
            'plaid_get_income': 'plaid_mcp_warp.py',
            'plaid_get_liabilities': 'plaid_mcp_warp.py',
            
            # Compliance tools
            'compliance_info': 'compliance_mcp_warp.py',
            'compliance_blacklist_list': 'compliance_mcp_warp.py',
            'compliance_check_entity': 'compliance_mcp_warp.py',
            'compliance_screen_transaction': 'compliance_mcp_warp.py',
            'compliance_generate_report': 'compliance_mcp_warp.py',
            
            # Automation tools
            'automation_list_workflows': 'automation_mcp_warp.py',
            'automation_run_workflow': 'automation_mcp_warp.py',
            'automation_get_workflow_status': 'automation_mcp_warp.py',
            'automation_schedule_workflow': 'automation_mcp_warp.py',
        }
        

    def route_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a tool call to the appropriate MCP function and return the result.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool call

        Returns:
            Result from the MCP function
        """
        # Get the function name for this tool
        function_name = self.tool_to_function_map.get(tool_name)
        if not function_name:
            return {
                "error": f"Unknown tool: {tool_name}",
                "isError": True
            }

        try:
            # Most tools are Xero tools
            if tool_name.startswith('xero_') and self.xero_mcp:
                # Get the function from the xero_mcp module
                if hasattr(self.xero_mcp, function_name):
                    func = getattr(self.xero_mcp, function_name)
                    # Call the function with the provided arguments
                    if arguments:
                        result = func(**arguments)
                    else:
                        result = func()
                    return result
                else:
                    return {
                        "error": f"Function '{function_name}' not found in Xero MCP module",
                        "isError": True
                    }
            else:
                return {
                    "error": f"No MCP module available for tool: {tool_name}",
                    "isError": True
                }

        except Exception as e:
            logger.exception(f"Error calling MCP function {function_name}")
            return {
                "error": f"Error calling {function_name}: {str(e)}",
                "isError": True
            }


    def get_available_tools(self) -> List[str]:
        """
        Get a list of all available tools that can be routed.
        
        Returns:
            List of available tool names
        """
        return list(self.tool_to_function_map.keys())

# Global instance of the MCP router
mcp_router = MCPRouter()