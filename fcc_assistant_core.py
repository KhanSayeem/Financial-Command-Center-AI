"""
Custom OpenAI Assistant for Financial Command Center AI
Connects to existing FCC-OpenAI adapter and provides executive-friendly interface
"""

import openai
import json
import os
import sys
from typing import Dict, Any, List, Optional
import requests
from datetime import datetime

# Add FCC-OpenAI adapter to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fcc-openai-adapter'))

class FinancialCommandCenterAssistant:
    def __init__(self, api_key: str = None, fcc_base_url: str = "https://localhost:8000"):
        """
        Initialize the Financial Command Center Assistant.
        
        Args:
            api_key: OpenAI API key (if None, will use environment variable)
            fcc_base_url: Base URL for Financial Command Center API
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
            
        self.fcc_base_url = fcc_base_url.rstrip('/')
        self.client = openai.OpenAI(api_key=self.api_key)
        self.assistant = None
        self.thread = None
        
        # FCC API client with SSL verification disabled for localhost
        self.fcc_session = requests.Session()
        self.fcc_session.verify = False  # For self-signed certificates in development
        
        # Disable SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def create_assistant(self) -> Dict[str, Any]:
        """
        Create the custom Financial Command Center Assistant with all FCC tools.
        
        Returns:
            Dictionary with assistant creation result
        """
        try:
            print("Creating Financial Command Center Assistant...")
            
            # Define all FCC tools that connect to your system
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_financial_health",
                        "description": "Get overall financial health score, cash position, and system status",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_cash_position",
                        "description": "Get current cash position across all bank accounts with detailed breakdown",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_profit_loss_statement",
                        "description": "Generate profit and loss statement for a specific period",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "period": {
                                    "type": "string",
                                    "description": "Time period (e.g., 'last_quarter', 'this_month', 'last_30_days', '2025-01-01 to 2025-03-31')",
                                    "enum": ["last_quarter", "this_month", "last_30_days", "last_90_days", "year_to_date", "custom"]
                                },
                                "start_date": {
                                    "type": "string",
                                    "description": "Start date in YYYY-MM-DD format (required for custom period)"
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End date in YYYY-MM-DD format (required for custom period)"
                                }
                            },
                            "required": []
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "process_payment",
                        "description": "Process a payment from a customer",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "customer_name": {
                                    "type": "string",
                                    "description": "Customer name or company"
                                },
                                "amount": {
                                    "type": "number",
                                    "description": "Payment amount in USD"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Payment description or invoice reference"
                                },
                                "payment_method": {
                                    "type": "string",
                                    "description": "Payment method",
                                    "enum": ["bank_transfer", "credit_card", "check", "ach"]
                                }
                            },
                            "required": ["customer_name", "amount"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_overdue_invoices",
                        "description": "Get list of overdue invoices with customer details and aging",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "days_overdue": {
                                    "type": "integer",
                                    "description": "Minimum days overdue (default: 30)",
                                    "minimum": 1,
                                    "maximum": 365
                                },
                                "min_amount": {
                                    "type": "number",
                                    "description": "Minimum invoice amount to include"
                                }
                            },
                            "required": []
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_accounts_receivable_aging",
                        "description": "Get aging report for accounts receivable",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "aging_periods": {
                                    "type": "array",
                                    "items": {
                                        "type": "integer"
                                    },
                                    "description": "Aging period thresholds in days (e.g., [30, 60, 90])",
                                    "default": [30, 60, 90]
                                }
                            },
                            "required": []
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_top_customers",
                        "description": "Get list of top customers by revenue",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "limit": {
                                    "type": "integer",
                                    "description": "Number of top customers to return (default: 10)",
                                    "minimum": 1,
                                    "maximum": 100
                                },
                                "period": {
                                    "type": "string",
                                    "description": "Period for calculating revenue",
                                    "enum": ["last_30_days", "last_quarter", "last_year", "year_to_date"],
                                    "default": "last_year"
                                }
                            },
                            "required": []
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_expense_breakdown",
                        "description": "Get detailed expense breakdown by category",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "period": {
                                    "type": "string",
                                    "description": "Time period for expense analysis",
                                    "enum": ["last_month", "last_quarter", "last_year", "year_to_date", "custom"]
                                },
                                "start_date": {
                                    "type": "string",
                                    "description": "Start date in YYYY-MM-DD format (required for custom period)"
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End date in YYYY-MM-DD format (required for custom period)"
                                }
                            },
                            "required": []
                        }
                    }
                }
            ]
            
            # Create the assistant with professional instructions
            self.assistant = self.client.beta.assistants.create(
                name="Financial Command Center Assistant",
                description="Professional financial assistant connected to Xero, Stripe, and Plaid",
                model="gpt-4o",
                tools=tools,
                instructions="""You are a senior financial analyst and executive advisor. 
                You have direct access to real-time financial data from Xero, Stripe, and Plaid.
                
                Communication Guidelines:
                - Use precise, professional business language
                - Always include specific currency amounts with proper formatting ($1,234.56)
                - Present data in clear, actionable formats
                - Highlight trends, anomalies, and key insights
                - Flag concerning metrics with appropriate urgency
                - Provide context and comparisons where relevant
                - Keep responses focused and executive-friendly
                - Use bullet points and clear sections for readability
                - Summarize complex data into key takeaways
                
                Financial Analysis Framework:
                - Cash Flow: Monitor inflows, outflows, and liquidity
                - Revenue Recognition: Track income timing and sources
                - Expense Management: Identify cost reduction opportunities
                - Customer Analysis: Highlight key accounts and churn risks
                - Collections: Monitor overdue accounts and aging
                - Financial Health: Evaluate overall stability and growth
                
                When responding to queries:
                1. First, determine what data is needed
                2. Use appropriate tools to fetch real financial data
                3. Analyze the data for trends and insights
                4. Present findings in professional, actionable format
                5. Include specific recommendations when appropriate
                6. Highlight any concerning metrics that require attention
                """
            )
            
            print(f"Assistant created successfully with ID: {self.assistant.id}")
            return {
                "success": True,
                "assistant_id": self.assistant.id,
                "message": "Financial Command Center Assistant created successfully"
            }
            
        except Exception as e:
            print(f"Failed to create assistant: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create Financial Command Center Assistant"
            }
    
    def handle_tool_call(self, tool_call) -> Dict[str, Any]:
        """
        Handle tool calls by connecting to the FCC system via your adapter.
        
        Args:
            tool_call: OpenAI tool call object
            
        Returns:
            Tool call result from FCC system
        """
        try:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            
            print(f"Executing tool: {tool_name} with arguments: {arguments}")
            
            # Route tool calls to appropriate FCC endpoints
            if tool_name == "get_financial_health":
                return self._get_financial_health()
                
            elif tool_name == "get_cash_position":
                return self._get_cash_position()
                
            elif tool_name == "get_profit_loss_statement":
                return self._get_profit_loss_statement(arguments)
                
            elif tool_name == "process_payment":
                return self._process_payment(arguments)
                
            elif tool_name == "get_overdue_invoices":
                return self._get_overdue_invoices(arguments)
                
            elif tool_name == "get_accounts_receivable_aging":
                return self._get_accounts_receivable_aging(arguments)
                
            elif tool_name == "get_top_customers":
                return self._get_top_customers(arguments)
                
            elif tool_name == "get_expense_breakdown":
                return self._get_expense_breakdown(arguments)
                
            else:
                return {
                    "error": f"Unknown tool: {tool_name}",
                    "isError": True,
                    "details": f"The tool '{tool_name}' is not supported by the Financial Command Center."
                }
                
        except Exception as e:
            print(f"Tool execution error: {str(e)}")
            return {
                "error": f"Tool execution failed: {str(e)}",
                "isError": True,
                "details": str(e)
            }
    
    def _get_financial_health(self) -> Dict[str, Any]:
        """Get financial health from FCC system."""
        try:
            # Try to get health data from FCC API
            response = self.fcc_session.get(f"{self.fcc_base_url}/api/dashboard")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "financial_health_score": data.get("score", 85),
                    "status": data.get("status", "healthy"),
                    "cash_position": data.get("cash_position", "$45,750.32"),
                    "monthly_inflow": data.get("monthly_inflow", "$89,500.00"),
                    "monthly_outflow": data.get("monthly_outflow", "$67,200.00"),
                    "next_30_days_projection": data.get("projection_30_days", "$68,300.00"),
                    "currency": data.get("currency", "USD")
                }
            else:
                # Fallback to mock data
                return {
                    "financial_health_score": 87,
                    "status": "healthy",
                    "cash_position": "$48,250.75",
                    "monthly_inflow": "$92,300.00",
                    "monthly_outflow": "$68,150.00",
                    "next_30_days_projection": "$72,400.75",
                    "currency": "USD",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "financial_health_score": 87,
                "status": "healthy",
                "cash_position": "$48,250.75",
                "monthly_inflow": "$92,300.00",
                "monthly_outflow": "$68,150.00",
                "next_30_days_projection": "$72,400.75",
                "currency": "USD",
                "timestamp": datetime.now().isoformat(),
                "source": "mock_data"
            }
    
    def _get_cash_position(self) -> Dict[str, Any]:
        """Get cash position details."""
        try:
            response = self.fcc_session.get(f"{self.fcc_base_url}/api/cash-flow")
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                # Fallback to mock data
                return {
                    "total_cash": "$48,250.75",
                    "bank_accounts": [
                        {"name": "Primary Operating Account", "balance": "$34,750.00", "currency": "USD"},
                        {"name": "Business Savings", "balance": "$13,500.75", "currency": "USD"}
                    ],
                    "currency": "USD",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "total_cash": "$48,250.75",
                "bank_accounts": [
                    {"name": "Primary Operating Account", "balance": "$34,750.00", "currency": "USD"},
                    {"name": "Business Savings", "balance": "$13,500.75", "currency": "USD"}
                ],
                "currency": "USD",
                "timestamp": datetime.now().isoformat(),
                "source": "mock_data"
            }
    
    def _get_profit_loss_statement(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get profit and loss statement."""
        period = arguments.get("period", "last_quarter")
        
        # Mock data for demonstration
        return {
            "period": period,
            "statement_date": datetime.now().isoformat(),
            "revenue": {
                "total": 245000.00,
                "breakdown": [
                    {"category": "Product Sales", "amount": 185000.00},
                    {"category": "Service Revenue", "amount": 60000.00}
                ]
            },
            "expenses": {
                "total": 187500.00,
                "breakdown": [
                    {"category": "Cost of Goods Sold", "amount": 95000.00},
                    {"category": "Operating Expenses", "amount": 65000.00},
                    {"category": "Marketing", "amount": 15000.00},
                    {"category": "Salaries", "amount": 12500.00}
                ]
            },
            "net_profit": 57500.00,
            "profit_margin": "23.5%",
            "currency": "USD"
        }
    
    def _process_payment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Process a payment."""
        customer_name = arguments.get("customer_name", "Unknown Customer")
        amount = arguments.get("amount", 0)
        description = arguments.get("description", "")
        payment_method = arguments.get("payment_method", "bank_transfer")
        
        # Mock successful payment processing
        return {
            "status": "success",
            "payment_id": f"pay_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "customer": customer_name,
            "amount": amount,
            "currency": "USD",
            "payment_method": payment_method,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "confirmation": f"Payment of ${amount:,.2f} from {customer_name} processed successfully via {payment_method}"
        }
    
    def _get_overdue_invoices(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get overdue invoices."""
        days_overdue = arguments.get("days_overdue", 30)
        min_amount = arguments.get("min_amount", 0)
        
        # Mock data
        return {
            "total_overdue_invoices": 3,
            "total_overdue_amount": 12450.00,
            "currency": "USD",
            "invoices": [
                {
                    "invoice_number": "INV-0015",
                    "customer": "ABC Corporation",
                    "amount": 5200.00,
                    "due_date": "2025-08-15",
                    "days_overdue": 45,
                    "currency": "USD"
                },
                {
                    "invoice_number": "INV-0012",
                    "customer": "XYZ Ltd",
                    "amount": 3750.00,
                    "due_date": "2025-08-22",
                    "days_overdue": 38,
                    "currency": "USD"
                },
                {
                    "invoice_number": "INV-0008",
                    "customer": "Global Partners",
                    "amount": 3500.00,
                    "due_date": "2025-08-28",
                    "days_overdue": 32,
                    "currency": "USD"
                }
            ]
        }
    
    def _get_accounts_receivable_aging(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get accounts receivable aging report."""
        aging_periods = arguments.get("aging_periods", [30, 60, 90])
        
        # Mock data
        return {
            "report_date": datetime.now().isoformat(),
            "currency": "USD",
            "aging_buckets": [
                {"period": "0-30 days", "count": 15, "amount": 25000.00},
                {"period": "31-60 days", "count": 8, "amount": 18500.00},
                {"period": "61-90 days", "count": 3, "amount": 7250.00},
                {"period": "90+ days", "count": 2, "amount": 5200.00}
            ],
            "total_accounts_receivable": 55950.00
        }
    
    def _get_top_customers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get top customers by revenue."""
        limit = arguments.get("limit", 10)
        period = arguments.get("period", "last_year")
        
        # Mock data
        return {
            "period": period,
            "customers": [
                {"name": "ABC Corporation", "revenue": 45000.00, "currency": "USD"},
                {"name": "XYZ Ltd", "revenue": 38500.00, "currency": "USD"},
                {"name": "Global Partners", "revenue": 32000.00, "currency": "USD"},
                {"name": "Tech Solutions Inc", "revenue": 28500.00, "currency": "USD"},
                {"name": "Innovation Labs", "revenue": 22500.00, "currency": "USD"}
            ]
        }
    
    def _get_expense_breakdown(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get expense breakdown by category."""
        period = arguments.get("period", "last_quarter")
        
        # Mock data
        return {
            "period": period,
            "total_expenses": 187500.00,
            "currency": "USD",
            "expense_categories": [
                {"category": "Cost of Goods Sold", "amount": 95000.00, "percentage": 50.7},
                {"category": "Salaries & Benefits", "amount": 45000.00, "percentage": 24.0},
                {"category": "Office Rent", "amount": 15000.00, "percentage": 8.0},
                {"category": "Marketing", "amount": 12500.00, "percentage": 6.7},
                {"category": "Utilities", "amount": 8000.00, "percentage": 4.3},
                {"category": "Software Subscriptions", "amount": 7500.00, "percentage": 4.0},
                {"category": "Travel & Entertainment", "amount": 4500.00, "percentage": 2.4}
            ]
        }

def main():
    """Main function to demonstrate the assistant creation."""
    print("Financial Command Center Assistant Setup")
    print("=" * 50)
    
    try:
        # Initialize the assistant
        assistant = FinancialCommandCenterAssistant()
        
        # Create the assistant
        result = assistant.create_assistant()
        
        if result["success"]:
            print("\nSuccess! Your Financial Command Center Assistant is ready.")
            print(f"Assistant ID: {result['assistant_id']}")
            print("\nNext steps:")
            print("1. Integrate with your FCC-OpenAI adapter endpoints")
            print("2. Connect to real financial data sources")
            print("3. Deploy the web UI for executive access")
            print("4. Test with sample executive queries")
        else:
            print(f"\nError creating assistant: {result['message']}")
            
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main()