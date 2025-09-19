"""
MCP Router for routing local LLM function calls to localhost MCP endpoints.
Handles self-signed SSL certificates and routes to appropriate MCP servers.
"""
import requests
import json
import urllib3
from typing import Dict, Any, List, Optional
from config.settings import MCP_SERVER_URL, SSL_VERIFY

# Disable SSL warnings for self-signed certificates
if not SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MCPRouter:
    def __init__(self, base_url: str = MCP_SERVER_URL, ssl_verify: bool = SSL_VERIFY):
        """
        Initialize the MCP Router.
        
        Args:
            base_url: Base URL for the MCP server
            ssl_verify: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.ssl_verify = ssl_verify
        self.session = requests.Session()
        self.session.verify = ssl_verify
        
        # Map tool names to their respective MCP server endpoints
        self.tool_to_server_map = {
            # Xero tools
            'xero_ping': 'xero_mcp_warp.py',
            'xero_whoami': 'xero_mcp_warp.py',
            'xero_set_tenant': 'xero_mcp_warp.py',
            'xero_list_contacts': 'xero_mcp_warp.py',
            'xero_create_contact': 'xero_mcp_warp.py',
            'xero_get_invoice_pdf': 'xero_mcp_warp.py',
            'xero_org_info': 'xero_mcp_warp.py',
            'xero_find_contact': 'xero_mcp_warp.py',
            'xero_list_invoices': 'xero_mcp_warp.py',
            'xero_delete_draft_invoice': 'xero_mcp_warp.py',
            'xero_export_invoices_csv': 'xero_mcp_warp.py',
            'xero_create_invoice': 'xero_mcp_warp.py',
            'xero_duplicate_invoice': 'xero_mcp_warp.py',
            'xero_send_invoice_email': 'xero_mcp_warp.py',
            'xero_authorise_invoice': 'xero_mcp_warp.py',
            'xero_create_payment': 'xero_mcp_warp.py',
            'xero_apply_payment_to_invoice': 'xero_mcp_warp.py',
            'xero_get_profit_loss': 'xero_mcp_warp.py',
            'xero_get_balance_sheet': 'xero_mcp_warp.py',
            'xero_get_aged_receivables': 'xero_mcp_warp.py',
            'xero_get_cash_flow_statement': 'xero_mcp_warp.py',
            'xero_bulk_create_invoices': 'xero_mcp_warp.py',
            'xero_export_chart_of_accounts': 'xero_mcp_warp.py',
            'xero_dashboard': 'xero_mcp_warp.py',
            'xero_process_stripe_payment_data': 'xero_mcp_warp.py',
            'xero_import_bank_feed': 'xero_mcp_warp.py',
            'xero_auto_categorize_transactions': 'xero_mcp_warp.py',
            
            # Financial Command Center tools
            'get_financial_health': 'mcp_server_warp.py',
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
        
        # Headers for MCP communication
        self.headers = {
            'Content-Type': 'application/json',
        }

    def route_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a tool call to the appropriate MCP server and return the result.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool call
            
        Returns:
            Result from the MCP server
        """
        # Determine which server to route to
        server_file = self.tool_to_server_map.get(tool_name)
        if not server_file:
            return {
                "error": f"Unknown tool: {tool_name}",
                "isError": True
            }
        
        # Construct the full URL for the specific MCP server
        server_url = f"{self.base_url}/{server_file}"
        
        # Create the MCP tool call request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            # Send the request to the MCP server
            response = self.session.post(
                server_url,
                headers=self.headers,
                data=json.dumps(mcp_request),
                timeout=30
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                return self._process_mcp_response(result)
            else:
                return {
                    "error": f"MCP server returned status {response.status_code}",
                    "isError": True,
                    "details": response.text
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "error": "Failed to connect to MCP server. Make sure the server is running.",
                "isError": True
            }
        except requests.exceptions.Timeout:
            return {
                "error": "Request to MCP server timed out",
                "isError": True
            }
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse MCP server response",
                "isError": True,
                "raw_response": response.text if 'response' in locals() else None
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "isError": True
            }

    def _process_mcp_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the response from the MCP server.
        
        Args:
            response: Raw response from the MCP server
            
        Returns:
            Processed response
        """
        # Check if it's an error response
        if "error" in response:
            return {
                "error": response["error"].get("message", "Unknown MCP error"),
                "isError": True,
                "details": response["error"]
            }
        
        # Extract the result
        if "result" in response:
            result = response["result"]
            
            # Handle structured content if present
            if "structuredContent" in result:
                return result["structuredContent"]
            
            # Handle content if present
            if "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    first_item = content[0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        try:
                            # Try to parse JSON text
                            return json.loads(first_item["text"])
                        except json.JSONDecodeError:
                            # Return as plain text
                            return {"text": first_item["text"]}
            
            # Return the raw result
            return result
        
        # Unexpected response format
        return {
            "error": "Unexpected MCP response format",
            "isError": True,
            "raw_response": response
        }

    def get_available_tools(self) -> List[str]:
        """
        Get a list of all available tools that can be routed.
        
        Returns:
            List of available tool names
        """
        return list(self.tool_to_server_map.keys())

# Global instance of the MCP router
mcp_router = MCPRouter()