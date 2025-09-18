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
    def __init__(self, app, openai_api_key=None):
        """
        Initialize FCC Assistant Integration.
        
        Args:
            app: Flask application instance
            openai_api_key: OpenAI API key (optional, will use env var if not provided)
        """
        self.app = app
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            logger.warning("OpenAI API key not found. Assistant will run in mock mode.")
            self.client = None
        else:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        
        self.assistant = None
        self.threads = {}  # Store conversation threads
        
    def setup_routes(self):
        """Setup assistant routes in the Flask application."""
        logger.info("Setting up FCC Assistant routes...")
        
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
            if not self.api_key:
                return jsonify({
                    "success": False,
                    "message": "OpenAI API key not configured"
                }), 400
            
            try:
                # Define assistant tools
                tools = self._get_assistant_tools()
                
                # Create assistant
                self.assistant = self.client.beta.assistants.create(
                    name="Financial Command Center Assistant",
                    description="AI-powered financial assistant for executives",
                    model="gpt-4o",
                    tools=tools,
                    instructions=self._get_assistant_instructions()
                )
                
                logger.info(f"Assistant created with ID: {self.assistant.id}")
                
                return jsonify({
                    "success": True,
                    "assistant_id": self.assistant.id,
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
                if self.client:
                    thread = self.client.beta.threads.create()
                    thread_id = thread.id
                else:
                    thread_id = f"mock_thread_{datetime.now().timestamp()}"
                
                # Store thread (in production, use proper session management)
                session_id = request.sid if hasattr(request, 'sid') else 'default'
                self.threads[session_id] = thread_id
                
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
            
            try:
                # In mock mode, return sample responses
                if not self.client or not self.api_key:
                    response = self._get_mock_response(message_content)
                    return jsonify({
                        "success": True,
                        "response": response,
                        "thread_id": thread_id or "mock_thread"
                    })
                
                # Get or create thread
                if not thread_id:
                    thread = self.client.beta.threads.create()
                    thread_id = thread.id
                
                # Add message to thread
                self.client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=message_content
                )
                
                # Run the assistant
                run = self.client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=self.assistant.id
                )
                
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
                
                if run.status == "completed":
                    # Get messages
                    messages = self.client.beta.threads.messages.list(
                        thread_id=thread_id
                    )
                    
                    # Find assistant response
                    assistant_response = None
                    for message in messages.data:
                        if message.role == "assistant":
                            assistant_response = message.content[0].text.value
                            break
                    
                    return jsonify({
                        "success": True,
                        "response": assistant_response or "No response from assistant",
                        "thread_id": thread_id
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": f"Assistant run failed: {run.status}"
                    }), 500
                    
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
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
        logger.info("FCC Assistant routes registered successfully")
    
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
                                "enum": ["last_quarter", "this_month", "last_30_days", "last_90_days", "year_to_date"]
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_overdue_invoices",
                    "description": "Get list of overdue invoices",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days_overdue": {
                                "type": "integer",
                                "description": "Minimum days overdue",
                                "default": 30
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

def setup_assistant_routes(app):
    """Setup assistant routes in the Flask application."""
    try:
        # Initialize assistant integration
        assistant = FCCAssistantIntegration(app)
        assistant.setup_routes()
        return True
    except Exception as e:
        logger.error(f"Failed to setup assistant routes: {e}")
        return False