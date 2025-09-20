"""
Financial Command Center Assistant Integration
Adds assistant functionality to existing FCC web application
"""

import openai
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from flask import Blueprint, request, jsonify, render_template
import logging

# Create blueprint for assistant routes
assistant_bp = Blueprint('assistant', __name__, url_prefix='/assistant')

# Logger
logger = logging.getLogger(__name__)

class FCCAssistantIntegration:
    def __init__(self, app, openai_api_key=None, model_type="gemini"):
        """Initialize FCC Assistant Integration."""
        self.app = app
        self.client = None
        self.assistant = None
        self.api_key = None
        self.gemini_client = None
        self.gemini_model = None
        self.gemini_model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        self.model_type = None
        self.model_ready = False
        self.model_status = ""
        self.threads = {}
        self.mcp_financial_module = None
        self.mcp_xero_module = None
        self.mcp_plaid_module = None
        self.mcp_stripe_module = None
        self.mcp_compliance_module = None
        self.mcp_context_available = False
        self.mcp_context_cache = {}
        self._gemini_tools = None
        self.mcp_router = None
        self.mcp_env = {}
        self.gemini_mcp_adapter = None

        self._initialize_mcp_support()

        requested_model = (model_type or os.getenv('ASSISTANT_MODEL_TYPE', 'gemini')).lower()
        success, message = self.set_model_type(requested_model, openai_api_key=openai_api_key)
        if not success and requested_model != 'gemini':
            logger.info('Primary model configuration failed, falling back to Gemini')
            success, message = self.set_model_type('gemini', openai_api_key=openai_api_key)

        if not success:
            logger.warning(f"Assistant initialized without active model: {message}")

    def set_model_type(self, model_type: str, openai_api_key: Optional[str] = None) -> Tuple[bool, str]:
        """Configure the assistant for the requested model type."""
        desired_type = (model_type or 'openai').lower()
        logger.info(f"Attempting to configure assistant for model: {desired_type}")

        if desired_type == "gemini":
            success, message = self._configure_gemini()
        elif desired_type == "openai":
            success, message = self._configure_openai(openai_api_key)
        else:
            success = False
            message = f"Unsupported model type: {desired_type}"

        if success:
            self.model_type = desired_type
        self.model_ready = success
        self.model_status = message

        if success:
            logger.info(message)
        else:
            logger.error(message)

        return success, message

    def _initialize_mcp_support(self):
        """Load MCP helpers and tool metadata for Gemini/OpenAI adapters."""
        try:
            adapter_root = Path(__file__).resolve().parent / 'fcc-openai-adapter'
            if adapter_root.exists() and str(adapter_root) not in sys.path:
                sys.path.insert(0, str(adapter_root))
        except Exception as exc:
            logger.debug(f"Unable to prepare MCP adapter path: {exc}")

        if not os.getenv('OPENAI_API_KEY'):
            os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY_PLACEHOLDER', 'placeholder-openai-key-for-mcp')

        self.mcp_context_available = False
        self.mcp_env = getattr(self, 'mcp_env', {}) or {}
        self.mcp_router = None
        self._gemini_tools = None

        try:
            from models.tool_schemas import all_tools as openai_tool_schemas  # type: ignore
            from utils.mcp_router import MCPRouter as MCPRouterClass  # type: ignore
        except Exception as exc:
            logger.warning(f"MCP support unavailable (tool import failed): {exc}")
            return

        self._gemini_tools = self._convert_openai_tools_for_gemini(openai_tool_schemas)
        if not self._gemini_tools:
            logger.warning("No MCP tool declarations available; skipping Gemini tool calling support.")
            return

        try:
            self._prepare_mcp_environment()
        except Exception as exc:
            logger.warning(f"Failed to prepare MCP environment: {exc}")
            return

        try:
            self.mcp_router = MCPRouterClass()
            self.mcp_context_available = True
            logger.info("MCP router initialized for assistant integration.")
        except Exception as exc:
            logger.warning(f"Unable to initialize MCP router: {exc}")
            self.mcp_router = None
            self.mcp_context_available = False

    def _prepare_mcp_environment(self):
        """Apply stored credentials so MCP servers can authenticate."""
        env_updates: Dict[str, Any] = {}

        try:
            from setup_wizard import ConfigurationManager  # type: ignore
            config_manager = ConfigurationManager()
            stored_config = config_manager.load_config() or {}
        except Exception as exc:
            logger.debug(f"Setup wizard configuration unavailable: {exc}")
            stored_config = {}

        stripe_config = stored_config.get('stripe', {}) if isinstance(stored_config.get('stripe'), dict) else {}
        xero_config = stored_config.get('xero', {}) if isinstance(stored_config.get('xero'), dict) else {}
        plaid_config = stored_config.get('plaid', {}) if isinstance(stored_config.get('plaid'), dict) else {}

        if stripe_config and not stripe_config.get('skipped'):
            env_updates.setdefault('STRIPE_API_KEY', stripe_config.get('api_key'))
            env_updates.setdefault('STRIPE_API_VERSION', stripe_config.get('api_version'))
            env_updates.setdefault('STRIPE_DEFAULT_CURRENCY', stripe_config.get('default_currency'))
            if stripe_config.get('mode'):
                env_updates.setdefault('MCP_STRIPE_PROD', 'true' if stripe_config.get('mode') == 'live' else 'false')

        if xero_config and not xero_config.get('skipped'):
            env_updates.setdefault('XERO_CLIENT_ID', xero_config.get('client_id'))
            env_updates.setdefault('XERO_CLIENT_SECRET', xero_config.get('client_secret'))

        if plaid_config and not plaid_config.get('skipped'):
            env_updates.setdefault('PLAID_CLIENT_ID', plaid_config.get('client_id'))
            env_updates.setdefault('PLAID_SECRET', plaid_config.get('secret'))
            env_updates.setdefault('PLAID_ENV', plaid_config.get('environment'))

        port = self.app.config.get('PORT', int(os.getenv('FCC_PORT', '8000'))) if self.app else int(os.getenv('FCC_PORT', '8000'))
        default_server_url = f"https://localhost:{port}"
        env_updates.setdefault('FCC_SERVER_URL', os.getenv('FCC_SERVER_URL', default_server_url))
        env_updates.setdefault('MCP_SERVER_URL', os.getenv('MCP_SERVER_URL', default_server_url))

        existing_api_key = os.getenv('FCC_API_KEY')
        if existing_api_key:
            env_updates['FCC_API_KEY'] = existing_api_key
        else:
            try:
                from auth.security import SecurityManager  # type: ignore
                security_manager = SecurityManager()
                auth_entries = security_manager._load_json(security_manager.auth_file)  # type: ignore[attr-defined]
                assistant_key = None
                for key_value, meta in (auth_entries or {}).items():
                    if meta.get('client_name') == 'Gemini Assistant' and meta.get('active', True):
                        assistant_key = key_value
                        break
                if not assistant_key:
                    assistant_key = security_manager.generate_api_key('Gemini Assistant', permissions=['read'])
                env_updates['FCC_API_KEY'] = assistant_key
            except Exception as exc:
                logger.debug(f"Could not ensure FCC API key for MCP access: {exc}")

        for key, value in env_updates.items():
            if value and not os.environ.get(key):
                os.environ[key] = str(value)

        self.mcp_env = {k: v for k, v in env_updates.items() if v}

    def _convert_openai_tools_for_gemini(self, openai_tools: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """Transform OpenAI-style tool specs into Gemini function declarations."""
        declarations: List[Dict[str, Any]] = []
        for tool in openai_tools or []:
            function_payload = tool.get('function') if isinstance(tool, dict) else None
            if not function_payload:
                continue
            name = function_payload.get('name')
            if not name:
                continue
            params = function_payload.get('parameters') or {"type": "object", "properties": {}}
            declarations.append({
                "name": name,
                "description": function_payload.get('description', ''),
                "parameters": params
            })
        if not declarations:
            return None
        return [{"function_declarations": declarations}]

    def _get_gemini_thread(self, thread_id: Optional[str]) -> Tuple[str, List[Dict[str, Any]]]:
        """Return a thread identifier and existing Gemini history."""
        thread_id = thread_id or f"gemini_thread_{datetime.now().timestamp()}"
        entry = self.threads.setdefault(thread_id, {"history": []})
        history = entry.get('history', [])
        if history is None:
            history = []
            entry['history'] = history
        return thread_id, history

    def _extract_gemini_text(self, response) -> str:
        """Best-effort extraction of text from a Gemini response object."""
        if not response:
            return 'Gemini returned an empty response.'
        text_value = getattr(response, 'text', '') or ''
        if text_value:
            return text_value.strip()
        collected: List[str] = []
        try:
            for candidate in getattr(response, 'candidates', []) or []:
                content = getattr(candidate, 'content', None)
                if not content:
                    continue
                parts = getattr(content, 'parts', []) or []
                for part in parts:
                    part_text = getattr(part, 'text', None)
                    if part_text:
                        collected.append(part_text)
        except Exception:
            logger.debug('Unable to parse Gemini response structure for text extraction', exc_info=True)
        return '\n'.join(collected).strip() or 'Gemini returned an empty response.'

    def _configure_gemini(self) -> Tuple[bool, str]:
        """Initialize Gemini client using stored configuration or environment variables."""
        gemini_api_key = self._get_stored_api_key('gemini') or os.getenv('GEMINI_API_KEY')

        if not gemini_api_key:
            return False, "Gemini API key not configured. Set GEMINI_API_KEY in your environment or setup wizard."

        try:
            import google.generativeai as genai
        except ImportError:
            return False, "google-generativeai package not installed. Install it to enable Gemini support."

        try:
            genai.configure(api_key=gemini_api_key)
            model_name = os.getenv('GEMINI_MODEL', self.gemini_model_name)
            model = genai.GenerativeModel(model_name)
        except Exception as exc:
            logger.exception("Failed to initialize Gemini client")
            return False, f"Failed to initialize Gemini client: {exc}"

        self.gemini_client = genai
        self.gemini_model = model
        self.gemini_model_name = model_name
        self.api_key = None
        self.client = None
        self.assistant = None
        return True, f"Connected to Google Gemini ({self.gemini_model_name})."

    def _configure_openai(self, openai_api_key: Optional[str] = None) -> Tuple[bool, str]:
        """Initialize OpenAI client using stored configuration or environment variables."""
        api_key = self._get_stored_api_key('openai') or openai_api_key or os.getenv('OPENAI_API_KEY')

        if not api_key:
            return False, "OpenAI API key not configured. Set OPENAI_API_KEY in your environment or setup wizard."

        try:
            client = openai.OpenAI(api_key=api_key)
        except Exception as exc:
            logger.exception("Failed to initialize OpenAI client")
            return False, f"Failed to initialize OpenAI client: {exc}"

        self.api_key = api_key
        self.client = client
        self.assistant = None
        self.gemini_client = None
        self.gemini_model = None
        self.gemini_mcp_adapter = None
        return True, "Connected to OpenAI (GPT-4o)."

    def _get_stored_api_key(self, provider: str = 'openai') -> Optional[str]:
        """Get stored API key for the requested provider from secure config."""
        try:
            from pathlib import Path
            config_path = Path(__file__).parent / 'secure_config' / 'chatgpt_config.json'
            logger.info(f"Looking for config at: {config_path}")
            if config_path.exists():
                config_data = json.loads(config_path.read_text())
                if provider == 'gemini':
                    api_key = config_data.get('gemini_api_key')
                else:
                    api_key = config_data.get('openai_api_key')
                logger.info(f"API key found in config for {provider}: {bool(api_key)}")
                return api_key
        except Exception as e:
            logger.error(f"Failed to read stored API key: {e}")
        return None

    def _send_gemini_message(self, message_content: str, thread_id: str = None):
        """Send a message using Gemini."""
        try:
            if not self.gemini_client or not self.gemini_model:
                logger.error("Gemini client not available")
                return jsonify({
                    "success": False,
                    "message": "Gemini client not available"
                }), 500

            response = self.gemini_model.generate_content(message_content)

            reply_text = getattr(response, 'text', '') or ''
            if not reply_text:
                try:
                    candidates = getattr(response, 'candidates', []) or []
                    collected_parts = []
                    for candidate in candidates:
                        content = getattr(candidate, 'content', None)
                        if content:
                            parts = getattr(content, 'parts', []) or []
                            for part in parts:
                                part_text = getattr(part, 'text', '')
                                if part_text:
                                    collected_parts.append(part_text)
                    if collected_parts:
                        reply_text = '\n'.join(collected_parts)
                except Exception:
                    logger.debug('Unable to parse Gemini response structure', exc_info=True)

            if not reply_text:
                reply_text = 'Gemini returned an empty response.'

            return jsonify({
                "success": True,
                "response": reply_text,
                "thread_id": thread_id or "gemini_thread"
            })

        except Exception as e:
            logger.error(f"Failed to send Gemini message: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Failed to process message with Gemini"
            }), 500

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


class GeminiMCPAdapter:
    """Gemini helper that loops function calls through the MCP router."""

    def __init__(
        self,
        genai_module,
        model_name: str,
        router,
        tools: Optional[List[Dict[str, Any]]],
        logger: Optional[logging.Logger] = None,
        max_turns: int = 6,
    ) -> None:
        self.genai = genai_module
        self.model_name = model_name
        self.router = router
        self.tools = tools or []
        self.logger = logger or logging.getLogger(__name__)
        self.max_turns = max_turns
        self.tool_config = {"function_calling_config": {"mode": "AUTO"}}
        self.model = genai_module.GenerativeModel(model_name, tools=self.tools)

    def process_query(self, prompt: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        contents = self._copy_history(conversation_history)
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        for turn in range(self.max_turns):
            response = self.model.generate_content(
                contents,
                tools=self.tools,
                tool_config=self.tool_config,
            )

            candidate = (response.candidates or [None])[0]
            if not candidate or not getattr(candidate, 'content', None):
                return {
                    "success": False,
                    "error": "Gemini returned no content.",
                    "history": contents,
                }

            parts = list(getattr(candidate.content, 'parts', []) or [])
            contents.append({"role": "model", "parts": parts})

            tool_calls = []
            text_segments: List[str] = []
            for part in parts:
                function_call = getattr(part, 'function_call', None)
                if function_call:
                    tool_calls.append(function_call)
                    continue
                text_value = getattr(part, 'text', None)
                if text_value:
                    text_segments.append(text_value)

            if tool_calls:
                for function_call in tool_calls:
                    name = getattr(function_call, 'name', '')
                    if not name:
                        continue
                    arguments = self._coerce_arguments(function_call)
                    self.logger.info("Gemini invoking MCP tool %s", name)
                    try:
                        result = self.router.route_tool_call(name, arguments)
                    except Exception as exc:
                        self.logger.exception("MCP tool %s raised an error", name)
                        result = {"error": str(exc), "isError": True}

                    contents.append({
                        "role": "tool",
                        "parts": [{
                            "function_response": {
                                "name": name,
                                "response": result,
                            }
                        }],
                    })
                continue

            if text_segments:
                return {
                    "success": True,
                    "response": "\n".join(text_segments).strip(),
                    "history": contents,
                }

            finish_reason = getattr(candidate, 'finish_reason', None)
            if finish_reason and str(finish_reason).lower() == 'stop':
                return {
                    "success": True,
                    "response": '',
                    "history": contents,
                }

        return {
            "success": False,
            "error": "Max tool-calling iterations reached without final response.",
            "history": contents,
        }

    def _copy_history(self, history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        copied: List[Dict[str, Any]] = []
        for message in history or []:
            role = message.get('role') if isinstance(message, dict) else None
            parts = list(message.get('parts', [])) if isinstance(message, dict) else []
            copied.append({"role": role, "parts": parts})
        return copied

    def _coerce_arguments(self, function_call) -> Dict[str, Any]:
        raw_args = getattr(function_call, 'args', {}) or {}
        try:
            if hasattr(raw_args, 'to_dict'):
                raw_args = raw_args.to_dict()
            elif hasattr(raw_args, 'as_dict'):
                raw_args = raw_args.as_dict()
            elif isinstance(raw_args, str):
                raw_args = json.loads(raw_args)
            elif not isinstance(raw_args, dict):
                raw_args = dict(raw_args)
        except Exception:
            try:
                raw_args = json.loads(str(raw_args))
            except Exception:
                raw_args = {}
        return raw_args if isinstance(raw_args, dict) else {}


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
        if assistant_instance.model_type == "gemini":
            return assistant_instance._send_gemini_message(message_content, thread_id)
        elif assistant_instance.model_type == "openai":
            return assistant_instance._send_openai_message(message_content, thread_id)
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
    active_type = os.getenv('ASSISTANT_MODEL_TYPE', 'gemini').lower()
    status_message = 'Assistant not configured yet.'
    model_ready = False

    if assistant_instance:
        active_type = (assistant_instance.model_type or active_type or 'gemini').lower()
        status_message = assistant_instance.model_status or status_message
        model_ready = bool(getattr(assistant_instance, 'model_ready', False))

    return jsonify({
        "success": True,
        "model_type": active_type,
        "available_models": ["gemini", "openai"],
        "model_ready": model_ready,
        "status_message": status_message
    })

@assistant_bp.route('/api/set-model-config', methods=['POST'])
def set_model_config():
    """Set model configuration."""
    data = request.get_json() or {}
    requested_type = data.get('model_type', 'gemini').lower()

    if requested_type not in ['gemini', 'openai']:
        return jsonify({
            "success": False,
            "message": "Invalid model type. Must be 'gemini' or 'openai'"
        }), 400

    previous_type = os.getenv('ASSISTANT_MODEL_TYPE', 'gemini').lower()
    status_message = 'Assistant not initialized on server.'
    model_ready = False
    success = False
    message = status_message

    if assistant_instance:
        success, message = assistant_instance.set_model_type(requested_type)
        status_message = assistant_instance.model_status or message
        model_ready = bool(getattr(assistant_instance, 'model_ready', False))
        active_type = assistant_instance.model_type or previous_type
    else:
        active_type = previous_type

    if success:
        os.environ['ASSISTANT_MODEL_TYPE'] = requested_type
        try:
            if assistant_instance:
                assistant_instance._update_env_file('ASSISTANT_MODEL_TYPE', requested_type)
        except Exception as exc:
            logger.warning(f"Failed to update .env file: {exc}")
        response_type = requested_type
    else:
        response_type = active_type

    response_payload = {
        "success": success,
        "message": message,
        "model_type": response_type,
        "model_ready": model_ready,
        "status_message": status_message
    }

    return jsonify(response_payload)

def setup_assistant_routes(app):
    """Setup assistant routes in the Flask application."""
    global assistant_instance
    try:
        model_type = os.getenv('ASSISTANT_MODEL_TYPE', 'gemini').lower()

        logger.info(f"Initializing assistant with model type: {model_type}")

        assistant_instance = FCCAssistantIntegration(app, model_type=model_type)

        app.register_blueprint(assistant_bp)
        logger.info("FCC Assistant routes registered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to setup assistant routes: {e}")
        return False

