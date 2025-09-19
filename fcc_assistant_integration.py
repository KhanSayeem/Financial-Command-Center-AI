"""
Financial Command Center Assistant Integration
Adds assistant functionality to existing FCC web application
"""

import openai
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify, render_template
import logging

# Create blueprint for assistant routes
assistant_bp = Blueprint('assistant', __name__, url_prefix='/assistant')

# Logger
logger = logging.getLogger(__name__)

class FCCAssistantIntegration:
    def __init__(self, app, openai_api_key=None, model_type="openai"):
        """
        Initialize FCC Assistant Integration.
        
        Args:
            app: Flask application instance
            openai_api_key: OpenAI API key (optional, will use env var if not provided)
            model_type: Type of model to use ("openai" or "llama32")
        """
        self.app = app
        self.model_type = model_type.lower()
        
        if self.model_type == "openai":
            # Try to get API key from stored config first, then from parameter, then from env var
            self.api_key = self._get_stored_api_key() or openai_api_key or os.getenv('OPENAI_API_KEY')
            
            logger.info(f"API key loaded: {bool(self.api_key)}")
            if self.api_key:
                logger.info("API key found, initializing OpenAI client")
                try:
                    self.client = openai.OpenAI(api_key=self.api_key)
                    logger.info("OpenAI client initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize OpenAI client: {e}")
                    self.client = None
            else:
                logger.warning("OpenAI API key not found. Assistant will run in mock mode.")
                self.client = None
            
            self.assistant = None
        else:
            # For Llama 3.2, we'll use the local LLM adapter
            try:
                from adapters.local_llm_mcp_adapter import LocalLLMMCPAdapter
                self.llm_adapter = LocalLLMMCPAdapter()
                logger.info("Llama 3.2 adapter initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Llama 3.2 adapter: {e}")
                self.llm_adapter = None
        
        self.threads = {}  # Store conversation threads
    
    def _get_stored_api_key(self):
        """Get stored OpenAI API key from chatgpt config."""
        try:
            from pathlib import Path
            config_path = Path(__file__).parent / 'secure_config' / 'chatgpt_config.json'
            logger.info(f"Looking for config at: {config_path}")
            if config_path.exists():
                config_data = json.loads(config_path.read_text())
                api_key = config_data.get('openai_api_key')
                logger.info(f"API key found in config: {bool(api_key)}")
                return api_key
        except Exception as e:
            logger.error(f"Failed to read stored API key: {e}")
        return None
        

    def _send_openai_message(self, message_content: str, thread_id: str = None):
        """Send a message using OpenAI."""
        # In mock mode, return sample responses
        logger.info(f"Checking if using mock mode - client: {bool(self.client)}, api_key: {bool(self.api_key)}")
        if not self.client or not self.api_key:
            logger.info("Using mock response")
            response = self._get_mock_response(message_content)
            return jsonify({
                "success": True,
                "response": response,
                "thread_id": thread_id or "mock_thread"
            })
        
        # Get or create thread
        if not thread_id:
            logger.info("Creating new thread")
            thread = self.client.beta.threads.create()
            thread_id = thread.id
        
        # Add message to thread
        logger.info(f"Adding message to thread {thread_id}")
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_content
        )
        
        # Run the assistant
        logger.info(f"Creating run for assistant {self.assistant.id} with thread {thread_id}")
        try:
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant.id
            )
            logger.info(f"Run created with ID: {run.id}, status: {run.status}")
        except Exception as e:
            logger.error(f"Failed to create run: {e}")
            return jsonify({
                "success": False,
                "message": f"Failed to create run: {str(e)}"
            }), 500
        
        # Wait for completion (in production, use streaming or polling)
        import time
        timeout = 30
        start_time = time.time()
        
        while run.status in ["queued", "in_progress"] and (time.time() - start_time) < timeout:
            time.sleep(1)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            logger.info(f"Run status: {run.status}")
        
        # Handle required actions (tool calls)
        if run.status == "requires_action":
            logger.info("Run requires action, handling tool calls")
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            tool_outputs = []
            
            for tool_call in tool_calls:
                logger.info(f"Handling tool call: {tool_call.function.name}")
                output = self.handle_tool_call(tool_call)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(output)
                })
            
            # Submit tool outputs
            try:
                logger.info(f"Submitting tool outputs for run {run.id}")
                self.client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                # After submission, retrieve the run status
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                logger.info(f"Run status after tool outputs submission: {run.status}")
            except Exception as e:
                logger.error(f"Failed to submit tool outputs: {e}")
                return jsonify({
                    "success": False,
                    "message": f"Failed to submit tool outputs: {str(e)}"
                }), 500
        
        logger.info(f"Final run status: {run.status}")
        
        if run.status == "completed":
            # Get messages
            logger.info("Run completed, retrieving messages")
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id
            )
            
            # Find assistant response
            assistant_response = None
            for message in messages.data:
                if message.role == "assistant":
                    assistant_response = message.content[0].text.value
                    break
            
            logger.info(f"Assistant response: {assistant_response}")
            
            return jsonify({
                "success": True,
                "response": assistant_response or "No response from assistant",
                "thread_id": thread_id
            })
        else:
            # Get more details about the failure
            logger.error(f"Assistant run failed with status: {run.status}")
            logger.error(f"Run details: {run}")
            if hasattr(run, 'last_error') and run.last_error:
                logger.error(f"Run last error: {run.last_error}")
            
            return jsonify({
                "success": False,
                "message": f"Assistant run failed: {run.status}",
                "details": {
                    "status": run.status,
                    "last_error": getattr(run, 'last_error', None)
                }
            }), 500

    def _send_llama32_message(self, message_content: str, thread_id: str = None):
        """Send a message using Llama 3.2."""
        try:
            # Check if Llama 3.2 adapter is available
            if not self.llm_adapter:
                logger.error("Llama 3.2 adapter not available")
                return jsonify({
                    "success": False,
                    "message": "Llama 3.2 adapter not available"
                }), 500
            
            # Process the query through the Llama 3.2 adapter
            result = self.llm_adapter.process_query(message_content)
            
            if result["success"]:
                return jsonify({
                    "success": True,
                    "response": result["response"],
                    "turns_used": result.get("turns_used", 0)
                })
            else:
                logger.error(f"Llama 3.2 processing failed: {result.get('error')}")
                return jsonify({
                    "success": False,
                    "message": f"Llama 3.2 processing failed: {result.get('error')}"
                }), 500
                
        except Exception as e:
            logger.error(f"Failed to send Llama 3.2 message: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Failed to process message with Llama 3.2"
            }), 500
        
    
    def handle_tool_call(self, tool_call) -> Dict[str, Any]:
        """
        Handle tool calls by connecting to the FCC system.
        
        Args:
            tool_call: OpenAI tool call object
            
        Returns:
            Tool call result from FCC system
        """
        try:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            
            logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
            
            # Route tool calls to appropriate FCC endpoints
            if tool_name == "get_financial_health":
                result = self._get_financial_health()
                logger.info(f"Tool {tool_name} result: {result}")
                return result
                
            elif tool_name == "get_cash_position":
                result = self._get_cash_position()
                logger.info(f"Tool {tool_name} result: {result}")
                return result
                
            elif tool_name == "get_profit_loss_statement":
                result = self._get_profit_loss_statement(arguments)
                logger.info(f"Tool {tool_name} result: {result}")
                return result
                
            elif tool_name == "process_payment":
                result = self._process_payment(arguments)
                logger.info(f"Tool {tool_name} result: {result}")
                return result
                
            elif tool_name == "get_overdue_invoices":
                result = self._get_overdue_invoices(arguments)
                logger.info(f"Tool {tool_name} result: {result}")
                return result
                
            elif tool_name == "get_accounts_receivable_aging":
                result = self._get_accounts_receivable_aging(arguments)
                logger.info(f"Tool {tool_name} result: {result}")
                return result
                
            elif tool_name == "get_top_customers":
                result = self._get_top_customers(arguments)
                logger.info(f"Tool {tool_name} result: {result}")
                return result
                
            elif tool_name == "get_expense_breakdown":
                result = self._get_expense_breakdown(arguments)
                logger.info(f"Tool {tool_name} result: {result}")
                return result
                
            else:
                error_result = {
                    "error": f"Unknown tool: {tool_name}",
                    "isError": True,
                    "details": f"The tool '{tool_name}' is not supported by the Financial Command Center."
                }
                logger.error(f"Unknown tool: {tool_name}")
                return error_result
                
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return {
                "error": f"Tool execution failed: {str(e)}",
                "isError": True,
                "details": str(e)
            }
    
    def _get_assistant_tools(self) -> List[Dict[str, Any]]:
        """Define assistant tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_financial_health",
                    "description": "Get overall financial health score and system status",
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
                    "description": "Get current cash position across all bank accounts",
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
                    "description": "Generate profit and loss statement for a period",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period": {
                                "type": "string",
                                "description": "Time period",
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
    
    def _get_assistant_instructions(self) -> str:
        """Get assistant instructions."""
        return """You are a professional financial assistant for executives. 
        You have access to real-time financial data from the company's systems.
        
        Guidelines:
        1. Use precise, professional language
        2. Provide specific numbers with currency symbols
        3. Include relevant context and trends
        4. Flag any concerning financial metrics
        5. Suggest actionable insights when appropriate
        6. Format monetary amounts clearly
        7. Use bullet points for lists
        8. Keep responses concise but comprehensive
        """
    
    def _get_mock_response(self, query: str) -> str:
        """Get mock response for demonstration."""
        query_lower = query.lower()
        
        if "health" in query_lower or "score" in query_lower:
            return """**Financial Health Report**

**Overall Score: 87/100** (Healthy)

Key Metrics:
- Cash Position: $48,250.75
- Monthly Inflow: $92,300.00
- Monthly Outflow: $68,150.00
- 30-Day Projection: $72,400.75

Status: All systems operational. No immediate concerns detected."""
        
        elif "cash" in query_lower or "position" in query_lower:
            return """**Current Cash Position: $48,250.75**

**Breakdown by Account:**
- Primary Operating Account: $34,750.00
- Business Savings: $13,500.75

**Trend Analysis:**
- Up 5.2% from last month
- Consistent positive cash flow maintained
- Adequate reserves for operational needs"""
        
        elif "profit" in query_lower or "loss" in query_lower:
            return """**Profit and Loss Statement (Last Quarter)**

Revenue: $245,000.00
Expenses: $187,500.00
Net Profit: $57,500.00
Profit Margin: 23.5%

**Key Insights:**
- 12% increase in revenue vs. previous quarter
- Controlled expense growth at 8%
- Strong profit margin performance"""
        
        elif "overdue" in query_lower or "invoice" in query_lower:
            return """**Overdue Invoices Summary**

Total Overdue Amount: $12,450.00
Number of Invoices: 3

**Top Overdue Invoices:**
1. ABC Corporation: $5,200.00 (45 days overdue)
2. XYZ Ltd: $3,750.00 (38 days overdue)
3. Global Partners: $3,500.00 (32 days overdue)

**Recommendation:** Contact these customers to expedite payment collection."""
        
        else:
            return f"""I understand you're asking about: "{query}"

I'm your Financial Command Center Assistant. I can help you with:
- Financial health assessments
- Cash flow analysis
- Profit and loss statements
- Overdue invoice tracking
- Revenue analysis
- Expense breakdowns

What specific financial information would you like to explore?"""

    def _update_env_file(self, key: str, value: str):
        """Update environment variable in .env file."""
        env_file = ".env"
        lines = []
        
        # Read existing file or create new one
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                lines = f.readlines()
        
        # Check if key already exists
        key_found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                key_found = True
                break
        
        # If not found, add it
        if not key_found:
            lines.append(f"{key}={value}\n")
        
        # Write back to file
        with open(env_file, "w") as f:
            f.writelines(lines)

    def _get_financial_health(self) -> Dict[str, Any]:
        """Get financial health from FCC system."""
        try:
            # Try to get health data from FCC API
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.get("https://localhost:8000/api/dashboard", verify=False)
            
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
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.get("https://localhost:8000/api/cash-flow", verify=False)
            
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

# Global assistant instance for routes
assistant_instance = None

@assistant_bp.route('/')
def assistant_dashboard():
    """Assistant dashboard page."""
    from ui.helpers import build_nav
    return render_template('assistant/dashboard.html', nav_items=build_nav('assistant'))

@assistant_bp.route('/chat')
def assistant_chat():
    """Assistant chat interface."""
    from ui.helpers import build_nav
    return render_template('assistant/chat.html', nav_items=build_nav('assistant'))

@assistant_bp.route('/api/create-assistant', methods=['POST'])
def create_assistant():
    """Create the OpenAI assistant."""
    if not assistant_instance or not assistant_instance.api_key:
        return jsonify({
            "success": False,
            "message": "OpenAI API key not configured"
        }), 400

    try:
        # Define assistant tools
        tools = assistant_instance._get_assistant_tools()

        # Create assistant
        assistant_instance.assistant = assistant_instance.client.beta.assistants.create(
            name="Financial Command Center Assistant",
            description="AI-powered financial assistant for executives",
            model="gpt-4o-mini",
            tools=tools,
            instructions=assistant_instance._get_assistant_instructions()
        )

        logger.info(f"Assistant created with ID: {assistant_instance.assistant.id}")

        return jsonify({
            "success": True,
            "assistant_id": assistant_instance.assistant.id,
            "message": "Assistant created successfully"
        })

    except Exception as e:
        logger.error(f"Failed to create assistant: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to create assistant"
        }), 500

@assistant_bp.route('/api/create-thread', methods=['POST'])
def create_thread():
    """Create a new conversation thread."""
    try:
        if assistant_instance and assistant_instance.client:
            thread = assistant_instance.client.beta.threads.create()
            thread_id = thread.id
        else:
            thread_id = f"mock_thread_{datetime.now().timestamp()}"

        # Store thread (in production, use proper session management)
        session_id = request.sid if hasattr(request, 'sid') else 'default'
        if assistant_instance:
            assistant_instance.threads[session_id] = thread_id

        return jsonify({
            "success": True,
            "thread_id": thread_id,
            "message": "Conversation thread created"
        })

    except Exception as e:
        logger.error(f"Failed to create thread: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to create conversation thread"
        }), 500

@assistant_bp.route('/api/send-message', methods=['POST'])
def send_message():
    """Send a message to the assistant."""
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({
            "success": False,
            "message": "Message content required"
        }), 400

    message_content = data.get('message', '')
    thread_id = data.get('thread_id')

    logger.info(f"Sending message: {message_content} with thread_id: {thread_id}")

    try:
        if not assistant_instance:
            return jsonify({
                "success": False,
                "message": "Assistant not configured"
            }), 500

        # Handle different model types
        if assistant_instance.model_type == "openai":
            return assistant_instance._send_openai_message(message_content, thread_id)
        elif assistant_instance.model_type == "llama32":
            return assistant_instance._send_llama32_message(message_content, thread_id)
        else:
            # In mock mode, return sample responses
            logger.info("Using mock response")
            response = assistant_instance._get_mock_response(message_content)
            return jsonify({
                "success": True,
                "response": response,
                "thread_id": thread_id or "mock_thread"
            })

    except Exception as e:
        logger.error(f"Failed to send message: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to process message"
        }), 500

@assistant_bp.route('/api/examples')
def get_examples():
    """Get example queries."""
    examples = [
        {
            "category": "Financial Health",
            "queries": [
                "What's our current financial health score?",
                "How's our cash position looking this month?",
                "Are there any concerning financial metrics I should know about?"
            ]
        },
        {
            "category": "Cash Flow",
            "queries": [
                "What's our current cash position across all accounts?",
                "Show me our cash flow projection for the next 30 days",
                "Which customers owe us the most money right now?"
            ]
        },
        {
            "category": "Revenue & Profitability",
            "queries": [
                "Generate a profit and loss statement for last quarter",
                "Who are our top 5 customers by revenue this year?",
                "What's our gross profit margin compared to last quarter?"
            ]
        }
    ]

    return jsonify({
        "success": True,
        "examples": examples
    })

@assistant_bp.route('/api/get-model-config', methods=['GET'])
def get_model_config():
    """Get current model configuration."""
    model_type = os.getenv('ASSISTANT_MODEL_TYPE', 'openai').lower()
    return jsonify({
        "success": True,
        "model_type": model_type,
        "available_models": ["openai", "llama32"]
    })

@assistant_bp.route('/api/set-model-config', methods=['POST'])
def set_model_config():
    """Set model configuration."""
    data = request.get_json()
    model_type = data.get('model_type', 'openai').lower()

    if model_type not in ['openai', 'llama32']:
        return jsonify({
            "success": False,
            "message": "Invalid model type. Must be 'openai' or 'llama32'"
        }), 400

    # Update environment variable
    os.environ['ASSISTANT_MODEL_TYPE'] = model_type

    # Also update the .env file to persist the setting
    try:
        if assistant_instance:
            assistant_instance._update_env_file('ASSISTANT_MODEL_TYPE', model_type)
    except Exception as e:
        logger.warning(f"Failed to update .env file: {e}")

    return jsonify({
        "success": True,
        "message": f"Model switched to {model_type}",
        "model_type": model_type
    })

def setup_assistant_routes(app):
    """Setup assistant routes in the Flask application."""
    global assistant_instance
    try:
        # Determine model type from environment variable
        model_type = os.getenv('ASSISTANT_MODEL_TYPE', 'openai').lower()

        # Initialize assistant integration
        assistant_instance = FCCAssistantIntegration(app, model_type=model_type)

        # Register blueprint
        app.register_blueprint(assistant_bp)
        logger.info("FCC Assistant routes registered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to setup assistant routes: {e}")
        return False