"""
Financial Command Center Llama 3.2 Integration
Adds Llama 3.2 support with MCP tool calling for natural language financial commands
"""

import json
import os
import requests
import logging
import sys
from datetime import datetime
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify, render_template
import urllib3

# Import MCP router for tool calling
try:
    # Add the local LLM adapter to the path
    adapter_path = os.path.join(os.path.dirname(__file__), 'fcc-local-llm-adapter')
    if adapter_path not in sys.path:
        sys.path.insert(0, adapter_path)

    # Import using importlib for better compatibility
    import importlib.util

    # Load mcp_router module
    router_spec = importlib.util.spec_from_file_location(
        "mcp_router",
        os.path.join(adapter_path, 'utils', 'mcp_router.py')
    )
    router_module = importlib.util.module_from_spec(router_spec)
    router_spec.loader.exec_module(router_module)
    MCPRouter = router_module.MCPRouter

    # Load tool_schemas module
    schemas_spec = importlib.util.spec_from_file_location(
        "tool_schemas",
        os.path.join(adapter_path, 'models', 'tool_schemas.py')
    )
    schemas_module = importlib.util.module_from_spec(schemas_spec)
    schemas_spec.loader.exec_module(schemas_module)
    all_tools = schemas_module.all_tools

    MCP_AVAILABLE = True
    print(f"MCP Router loaded successfully with {len(all_tools)} tools")

except Exception as e:
    print(f"Warning: MCP Router not available: {e}")
    MCP_AVAILABLE = False
    all_tools = []
    MCPRouter = None

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logger
logger = logging.getLogger(__name__)

# Create blueprint for assistant routes
assistant_bp = Blueprint('assistant', __name__, url_prefix='/assistant')

class FCCLlama32Integration:
    def __init__(self, app, llama_base_url=None, llama_model=None):
        """
        Initialize FCC Llama 3.2 Integration with MCP tool support.

        Args:
            app: Flask application instance
            llama_base_url: Llama 3.2 API base URL (optional, will use env var if not provided)
            llama_model: Llama 3.2 model name (optional, will use env var if not provided)
        """
        self.app = app
        self.base_url = llama_base_url or os.getenv('LLAMA_BASE_URL', 'http://localhost:11434/v1')
        self.model = llama_model or os.getenv('LLAMA_MODEL', 'llama3.2')
        self.max_turns = 5  # Maximum conversation turns to prevent loops

        logger.info(f"Llama 3.2 integration initialized with base_url: {self.base_url}, model: {self.model}")

        # Initialize MCP router if available
        if MCP_AVAILABLE:
            try:
                self.mcp_router = MCPRouter()
                logger.info("MCP Router initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize MCP Router: {e}")
                self.mcp_router = None
        else:
            self.mcp_router = None

        # Test connection to Llama 3.2
        self.client_available = self._test_connection()

        if not self.client_available:
            logger.warning("Llama 3.2 not available. Assistant will run in mock mode.")

        self.threads = {}  # Store conversation threads

    def _test_connection(self) -> bool:
        """Test connection to Llama 3.2 server."""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=5)
            if response.status_code == 200:
                models = response.json().get("data", [])
                model_names = [model["id"] for model in models]
                if self.model in model_names or f"{self.model}:latest" in model_names:
                    logger.info(f"Llama 3.2 model '{self.model}' is available")
                    return True
                else:
                    logger.warning(f"Llama 3.2 model '{self.model}' not found in available models: {model_names}")
                    return False
            else:
                logger.error(f"Llama 3.2 server returned status code {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Llama 3.2 at {self.base_url}")
            return False
        except Exception as e:
            logger.error(f"Error testing Llama 3.2 connection: {e}")
            return False

    def setup_routes(self):
        """Setup assistant routes in the Flask application."""
        logger.info("Setting up FCC Llama 3.2 Assistant routes...")
        
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

        @assistant_bp.route('/api/create-thread', methods=['POST'])
        def create_thread():
            """Create a new conversation thread."""
            try:
                # For Llama 3.2, we'll manage threads locally
                thread_id = f"llama_thread_{datetime.now().timestamp()}"
                
                # Store thread (in production, use proper session management)
                session_id = request.sid if hasattr(request, 'sid') else 'default'
                self.threads[session_id] = {
                    'thread_id': thread_id,
                    'messages': []
                }
                
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
            """Send a message to the Llama 3.2 assistant with MCP tool calling support."""
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
                # If Llama 3.2 is not available, return error instead of mock
                if not self.client_available:
                    return jsonify({
                        "success": False,
                        "message": "Llama 3.2 service is not available. Please ensure Ollama/LM Studio is running with llama3.2 model loaded."
                    }), 503

                # Get or create thread
                session_id = request.sid if hasattr(request, 'sid') else 'default'
                if session_id not in self.threads or (thread_id and self.threads[session_id]['thread_id'] != thread_id):
                    # Create new thread
                    thread_id = f"llama_thread_{datetime.now().timestamp()}"
                    self.threads[session_id] = {
                        'thread_id': thread_id,
                        'messages': []
                    }
                else:
                    thread_id = self.threads[session_id]['thread_id']

                # Add user message to thread
                self.threads[session_id]['messages'].append({
                    "role": "user",
                    "content": message_content
                })

                # Process message with MCP tool calling
                response_result = self._process_with_mcp_tools(session_id)

                if not response_result["success"]:
                    return jsonify({
                        "success": False,
                        "message": response_result.get("error", "Failed to process message")
                    }), 500

                return jsonify({
                    "success": True,
                    "response": response_result["response"],
                    "thread_id": thread_id,
                    "turns_used": response_result.get("turns_used", 0)
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

        @assistant_bp.route('/api/model-config')
        def get_model_config():
            """Get current model configuration."""
            return jsonify({
                "success": True,
                "model_type": "llama32",
                "message": "Llama 3.2 model active"
            })

        @assistant_bp.route('/api/set-model-config', methods=['POST'])
        def set_model_config():
            """Set model configuration (Llama 3.2 mode only)."""
            data = request.get_json()
            model_type = data.get('model_type', 'llama32').lower()

            if model_type != 'llama32':
                return jsonify({
                    "success": False,
                    "message": "This integration only supports Llama 3.2. To switch to OpenAI, restart the app with ASSISTANT_MODEL_TYPE=openai"
                }), 400

            return jsonify({
                "success": True,
                "message": "Llama 3.2 model is active",
                "model_type": "llama32"
            })

        # Register blueprint
        self.app.register_blueprint(assistant_bp)
        logger.info("FCC Llama 3.2 Assistant routes registered successfully")

    def _process_with_mcp_tools(self, session_id: str) -> Dict[str, Any]:
        """
        Process the conversation with MCP tool calling support.

        Args:
            session_id: Session ID for the conversation thread

        Returns:
            Final response after processing all tool calls
        """
        messages = self.threads[session_id]['messages'].copy()

        # Add system message with instructions
        system_message = {
            "role": "system",
            "content": self._get_assistant_instructions()
        }
        messages.insert(0, system_message)

        turn_count = 0

        while turn_count < self.max_turns:
            try:
                # Call Llama 3.2 with MCP tools (or without tools if there are issues)
                tools = all_tools if self.mcp_router else []

                # For the first attempt, try without tools for faster response
                # In production, you can remove this logic
                if turn_count == 0 and len(messages) <= 2:  # Simple queries
                    logger.info("Using simplified mode for faster response")
                    response = self._call_llama32_with_tools(messages, [])
                else:
                    response = self._call_llama32_with_tools(messages, tools)

                if "error" in response:
                    return {
                        "success": False,
                        "error": response["error"],
                        "turns_used": turn_count
                    }

                # Get response message
                if "choices" in response and len(response["choices"]) > 0:
                    response_message = response["choices"][0]["message"]
                else:
                    return {
                        "success": False,
                        "error": "Invalid response from Llama 3.2",
                        "turns_used": turn_count
                    }

                # Check if there are tool calls
                tool_calls = response_message.get("tool_calls")
                if tool_calls and self.mcp_router:
                    logger.info(f"Processing {len(tool_calls)} tool calls")

                    # Add assistant message with tool calls
                    messages.append(response_message)

                    # Process each tool call
                    for tool_call in tool_calls:
                        function_name = tool_call["function"]["name"]
                        try:
                            function_args = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            function_args = {}

                        logger.info(f"Calling tool: {function_name} with args: {function_args}")

                        # Route the tool call through MCP router
                        tool_response = self.mcp_router.route_tool_call(function_name, function_args)

                        # Add tool response to messages
                        messages.append({
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(tool_response)
                        })

                    # Increment turn count and continue
                    turn_count += 1
                else:
                    # No more tool calls, return final response
                    assistant_response = response_message.get("content", "")

                    # Update thread with final assistant response
                    self.threads[session_id]['messages'].append({
                        "role": "assistant",
                        "content": assistant_response
                    })

                    return {
                        "success": True,
                        "response": assistant_response,
                        "turns_used": turn_count
                    }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "turns_used": turn_count
                }

        # Max turns reached
        return {
            "success": False,
            "error": f"Max turns ({self.max_turns}) reached. Conversation may be stuck in a loop.",
            "turns_used": turn_count
        }

    def _call_llama32_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict] = None) -> Dict[str, Any]:
        """
        Call Llama 3.2 API with messages and optional tools.

        Args:
            messages: List of messages in the conversation
            tools: List of tools available for function calling

        Returns:
            Response from Llama 3.2 API
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048
            }

            # Add tools if provided
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,  # Increased timeout for slower models
                verify=False  # Disable SSL verification for self-signed certificates
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Llama 3.2 API returned status {response.status_code}",
                    "details": response.text
                }
        except requests.exceptions.Timeout:
            return {
                "error": "Llama 3.2 request timed out. The model may be slow or overloaded. Try a simpler query or check if Ollama is running properly."
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": "Cannot connect to Llama 3.2. Please ensure Ollama is running on http://localhost:11434"
            }
        except Exception as e:
            return {
                "error": f"Llama 3.2 error: {str(e)}"
            }

    def _call_llama32(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Legacy method for backward compatibility."""
        return self._call_llama32_with_tools(messages)

    def _get_assistant_instructions(self) -> str:
        """Get assistant instructions."""
        return """You are a professional financial assistant for executives with access to real-time financial data through MCP (Model Context Protocol) tools.

You have direct access to the following financial systems:
- **Xero**: Accounting data, invoices, contacts, profit/loss statements, balance sheets
- **Stripe**: Payment processing, customer data, transaction history
- **Plaid**: Bank account information, transaction data, cash flow analysis
- **Compliance**: Regulatory compliance tools and reporting

When a user asks about financial information, you should:
1. **Use the appropriate MCP tools** to fetch real, up-to-date data instead of making assumptions
2. **Analyze the actual data** returned by the tools
3. **Present findings professionally** with specific numbers and currency symbols
4. **Highlight trends and insights** based on the real data
5. **Flag concerning metrics** that require attention
6. **Provide actionable recommendations** based on the actual financial position

Communication Guidelines:
- Use precise, professional business language
- Always include specific currency amounts with proper formatting ($1,234.56)
- Present data in clear, actionable formats using bullet points and sections
- Highlight trends, anomalies, and key insights from the real data
- Flag concerning metrics with appropriate urgency levels
- Provide context and comparisons where relevant
- Keep responses focused and executive-friendly
- Summarize complex data into key takeaways

Example natural language commands you can process:
- "What's our current cash position?" → Use Plaid/Xero tools to get real bank balances
- "Show me overdue invoices over $1,000" → Use Xero tools to query actual invoice data
- "Who are our top customers this quarter?" → Use Stripe/Xero tools for real revenue data
- "Generate a profit and loss statement" → Use Xero tools for actual P&L data
- "Process a payment from [customer]" → Use Stripe tools for real payment processing

Always use tools when available to provide accurate, real-time financial information rather than generic responses."""


def setup_llama32_routes(app):
    """Setup Llama 3.2 assistant routes in the Flask application."""
    try:
        # Initialize Llama 3.2 integration
        assistant = FCCLlama32Integration(app)
        assistant.setup_routes()
        return True
    except Exception as e:
        logger.error(f"Failed to setup Llama 3.2 assistant routes: {e}")
        return False