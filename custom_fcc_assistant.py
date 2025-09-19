#!/usr/bin/env python3
"""
Custom OpenAI Assistant for Financial Command Center AI
This assistant connects to your local FCC system and provides natural language financial analysis.
"""

import openai
import json
import os
from typing import Dict, Any, List

class FinancialCommandCenterAssistant:
    def __init__(self):
        """Initialize the assistant with OpenAI client"""
        # Get OpenAI API key from environment variables
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.assistant = None
        self.thread = None
        
    def create_assistant(self):
        """Create the custom Financial Command Center Assistant"""
        print("Creating Financial Command Center Assistant...")
        
        # Define the tools that connect to your FCC system
        tools = [
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
                    "name": "get_profit_loss",
                    "description": "Generate profit and loss statement for a period",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period": {
                                "type": "string",
                                "description": "Time period (e.g., 'last_quarter', 'this_month', 'last_30_days')"
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
                            "customer": {
                                "type": "string",
                                "description": "Customer name or ID"
                            },
                            "amount": {
                                "type": "number",
                                "description": "Payment amount"
                            },
                            "description": {
                                "type": "string",
                                "description": "Payment description"
                            }
                        },
                        "required": ["customer", "amount"]
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
                                "description": "Minimum days overdue (default: 30)"
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
        
        # Create the assistant
        self.assistant = self.client.beta.assistants.create(
            name="Financial Command Center Assistant",
            description="Your personal financial assistant connected to Xero, Stripe, and Plaid",
            model="gpt-4o",
            tools=tools,
            instructions="""You are a professional financial assistant for executives. 
            You have access to real-time financial data from Xero, Stripe, and Plaid.
            
            Guidelines:
            1. Always use precise, professional language
            2. Provide specific numbers with currency symbols
            3. Include relevant context and trends
            4. Flag any concerning financial metrics
            5. Suggest actionable insights when appropriate
            6. Format monetary amounts clearly ($1,234.56)
            7. Use bullet points for lists of items
            8. Keep responses concise but comprehensive
            
            When users ask about financial matters:
            - Use the appropriate tool to get real data
            - Present the information clearly
            - Add your professional analysis
            - Highlight key takeaways
            """
        )
        
        print(f"✅ Assistant created with ID: {self.assistant.id}")
        return self.assistant
    
    def create_thread(self):
        """Create a conversation thread"""
        self.thread = self.client.beta.threads.create()
        print(f"✅ Thread created with ID: {self.thread.id}")
        return self.thread
    
    def add_message(self, content: str):
        """Add a message to the thread"""
        if not self.thread:
            self.create_thread()
            
        message = self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=content
        )
        print(f"✅ Message added: {content[:50]}...")
        return message
    
    def run_assistant(self):
        """Run the assistant on the thread"""
        if not self.thread or not self.assistant:
            raise ValueError("Thread and Assistant must be created first")
            
        print("🏃 Running assistant...")
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id
        )
        
        # Wait for completion
        while run.status in ["queued", "in_progress"]:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=run.id
            )
            print(f"⏳ Run status: {run.status}")
            
        if run.status == "completed":
            print("✅ Run completed successfully")
            return self.get_latest_response()
        else:
            print(f"❌ Run failed with status: {run.status}")
            return f"Assistant run failed: {run.status}"
    
    def get_latest_response(self):
        """Get the latest response from the thread"""
        messages = self.client.beta.threads.messages.list(
            thread_id=self.thread.id
        )
        
        # Get the most recent message (should be the assistant's response)
        latest_message = messages.data[0]
        if latest_message.role == "assistant":
            content = latest_message.content[0].text.value
            return content
        return "No response found"
    
    def handle_tool_call(self, tool_call):
        """Handle tool calls by connecting to your FCC system"""
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Tool called: {tool_name} with args: {arguments}")
        
        # Here you would connect to your FCC-OpenAI adapter
        # For now, I'll provide mock responses that match your system's capabilities
        
        if tool_name == "get_financial_health":
            return {
                "financial_health_score": 85,
                "status": "healthy",
                "cash_position": "$45,750.32",
                "monthly_inflow": "$89,500.00",
                "monthly_outflow": "$67,200.00",
                "next_30_days_projection": "$68,300.00"
            }
            
        elif tool_name == "get_cash_position":
            return {
                "total_cash": "$45,750.32",
                "bank_accounts": [
                    {"name": "Primary Operating", "balance": "$32,500.00"},
                    {"name": "Savings Reserve", "balance": "$13,250.32"}
                ],
                "currency": "USD"
            }
            
        elif tool_name == "get_profit_loss":
            period = arguments.get("period", "last_quarter")
            return {
                "period": period,
                "revenue": "$245,000.00",
                "expenses": "$187,500.00",
                "net_profit": "$57,500.00",
                "profit_margin": "23.5%"
            }
            
        elif tool_name == "process_payment":
            customer = arguments.get("customer")
            amount = arguments.get("amount")
            return {
                "status": "success",
                "payment_id": "pay_123456789",
                "customer": customer,
                "amount": f"${amount:,.2f}",
                "confirmation": f"Payment of ${amount:,.2f} from {customer} processed successfully"
            }
            
        elif tool_name == "get_overdue_invoices":
            days = arguments.get("days_overdue", 30)
            return {
                "total_overdue": 3,
                "total_amount": "$12,450.00",
                "invoices": [
                    {"customer": "ABC Corporation", "amount": "$5,200.00", "days_overdue": 45},
                    {"customer": "XYZ Ltd", "amount": "$3,750.00", "days_overdue": 38},
                    {"customer": "Global Partners", "amount": "$3,500.00", "days_overdue": 32}
                ]
            }
            
        else:
            return {"error": f"Unknown tool: {tool_name}"}

def main():
    """Main function to demonstrate the assistant"""
    print("🚀 Starting Financial Command Center Assistant")
    print("=" * 50)
    
    # Initialize the assistant
    fcc_assistant = FinancialCommandCenterAssistant()
    
    # Create the assistant
    assistant = fcc_assistant.create_assistant()
    
    # Create a conversation thread
    thread = fcc_assistant.create_thread()
    
    # Example interactions
    examples = [
        "What's our current financial health score?",
        "What's our cash position across all accounts?",
        "Show me a profit and loss statement for last quarter",
        "Process a $500 payment from customer ABC Corporation",
        "Show me invoices over $1,000 that are more than 30 days overdue"
    ]
    
    print("\n📝 Example Interactions:")
    print("-" * 30)
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example}")
        fcc_assistant.add_message(example)
        # In a real implementation, you would handle the tool calls here
        print("   (In demo mode - would connect to FCC system)")
    
    print("\n✅ Assistant setup complete!")
    print("\n🔧 Next steps:")
    print("1. Integrate with your FCC-OpenAI adapter")
    print("2. Connect to real financial data sources")
    print("3. Deploy for executive use")
    print("4. Monitor usage and refine prompts")

if __name__ == "__main__":
    main()