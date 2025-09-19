"""
Financial Command Center Llama 3.2 Integration
Adds Llama 3.2 support to existing FCC assistant framework
"""

import json
import os
import requests
import logging
from datetime import datetime
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify, render_template
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create blueprint for assistant routes
assistant_bp = Blueprint('assistant', __name__, url_prefix='/assistant')

# Logger
logger = logging.getLogger(__name__)

class FCCLlama32Integration:
    def __init__(self, app, llama_base_url=None, llama_model=None):
        """
        Initialize FCC Llama 3.2 Integration.
        
        Args:
            app: Flask application instance
            llama_base_url: Llama 3.2 API base URL (optional, will use env var if not provided)
            llama_model: Llama 3.2 model name (optional, will use env var if not provided)
        """
        self.app = app
        self.base_url = llama_base_url or os.getenv('LLAMA_BASE_URL', 'http://localhost:11434/v1')
        self.model = llama_model or os.getenv('LLAMA_MODEL', 'llama3.2')
        
        logger.info(f"Llama 3.2 integration initialized with base_url: {self.base_url}, model: {self.model}")
        
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
            """Send a message to the Llama 3.2 assistant."""
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
                # In mock mode or if Llama 3.2 is not available, return sample responses
                if not self.client_available:
                    logger.info("Using mock response")
                    response = self._get_mock_response(message_content)
                    return jsonify({
                        "success": True,
                        "response": response,
                        "thread_id": thread_id or "mock_thread"
                    })
                
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
                
                # Prepare messages for Llama 3.2
                messages = self.threads[session_id]['messages'].copy()
                
                # Add system message with instructions
                system_message = {
                    "role": "system",
                    "content": self._get_assistant_instructions()
                }
                messages.insert(0, system_message)
                
                # Call Llama 3.2
                logger.info(f"Calling Llama 3.2 with messages: {messages}")
                response = self._call_llama32(messages)
                
                if "error" in response:
                    logger.error(f"Llama 3.2 call failed: {response['error']}")
                    return jsonify({
                        "success": False,
                        "message": f"Llama 3.2 call failed: {response['error']}"
                    }), 500
                
                # Extract response content
                assistant_response = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Add assistant response to thread
                self.threads[session_id]['messages'].append({
                    "role": "assistant",
                    "content": assistant_response
                })
                
                logger.info(f"Assistant response: {assistant_response}")
                
                return jsonify({
                    "success": True,
                    "response": assistant_response,
                    "thread_id": thread_id
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
        
        # Register blueprint
        self.app.register_blueprint(assistant_bp)
        logger.info("FCC Llama 3.2 Assistant routes registered successfully")

    def _call_llama32(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Call Llama 3.2 API with messages.
        
        Args:
            messages: List of messages in the conversation
            
        Returns:
            Response from Llama 3.2 API
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,  # Longer timeout for local LLM processing
                verify=False  # Disable SSL verification for self-signed certificates
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Llama 3.2 API returned status {response.status_code}",
                    "details": response.text
                }
        except Exception as e:
            return {
                "error": str(e)
            }

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