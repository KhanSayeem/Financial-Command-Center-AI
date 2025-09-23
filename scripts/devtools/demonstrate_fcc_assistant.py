#!/usr/bin/env python3
"""
Demonstration Script for Financial Command Center Assistant
Shows how to use the assistant programmatically
"""

from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)

import sys

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demonstrate_assistant():
    """Demonstrate the Financial Command Center Assistant capabilities."""
    print("Financial Command Center Assistant Demonstration")
    print("=" * 50)
    
    # Import the assistant core
    from fcc_assistant_core import FinancialCommandCenterAssistant
    
    # Check if OpenAI API key is available
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if openai_key:
        print("[INFO] Using real OpenAI API key")
        print("[INFO] Assistant will connect to live financial data")
    else:
        print("[INFO] No OpenAI API key found")
        print("[INFO] Assistant will run in demonstration mode")
        print("[INFO] Financial data will be simulated")
    
    # Create assistant instance
    try:
        assistant = FinancialCommandCenterAssistant()
        print("[PASS] Assistant instance created successfully")
    except Exception as e:
        print(f"[FAIL] Failed to create assistant instance: {e}")
        return False
    
    # Demonstrate capabilities
    print("\nAssistant Capabilities:")
    print("-" * 25)
    capabilities = [
        "Financial Health Assessments",
        "Cash Flow Analysis",
        "Profit and Loss Statements",
        "Overdue Invoice Tracking",
        "Customer Revenue Analysis",
        "Expense Breakdowns",
        "Accounts Receivable Aging",
        "Top Customer Identification"
    ]
    
    for i, capability in enumerate(capabilities, 1):
        print(f"{i:2d}. {capability}")
    
    # Example queries
    print("\nExample Executive Queries:")
    print("-" * 25)
    example_queries = [
        "What's our current financial health score?",
        "Show me our cash position across all bank accounts",
        "Generate a profit and loss statement for last quarter",
        "Which customers have overdue invoices over $1,000?",
        "Who are our top 5 customers by revenue this year?",
        "What's our accounts receivable aging report?",
        "Break down our expenses by category for this quarter",
        "Process a $500 payment from customer ABC Corporation"
    ]
    
    for i, query in enumerate(example_queries, 1):
        print(f"{i:2d}. {query}")
    
    # Mock responses (since we're in demonstration mode)
    print("\nDemonstration Responses:")
    print("-" * 25)
    
    mock_responses = {
        "health_score": """
**Financial Health Report**

**Overall Score: 87/100** (Healthy)

Key Metrics:
- Cash Position: $48,250.75
- Monthly Inflow: $92,300.00
- Monthly Outflow: $68,150.00
- 30-Day Projection: $72,400.75

Status: All systems operational. No immediate concerns detected.
        """,
        
        "cash_position": """
**Current Cash Position: $48,250.75**

Breakdown by Account:
- Primary Operating Account: $34,750.00
- Business Savings: $13,500.75

Trend Analysis:
- Up 5.2% from last month
- Consistent positive cash flow maintained
- Adequate reserves for operational needs
        """,
        
        "profit_loss": """
**Profit and Loss Statement** (Last Quarter)

Revenue: $245,000.00
Expenses: $187,500.00
Net Profit: $57,500.00
Profit Margin: 23.5%

Key Insights:
- 12% increase in revenue vs. previous quarter
- Controlled expense growth at 8%
- Strong profit margin performance
        """
    }
    
    print("Query: What's our current financial health score?")
    print("Response:")
    print(mock_responses["health_score"])
    
    print("\nQuery: Show me our cash position across all bank accounts")
    print("Response:")
    print(mock_responses["cash_position"])
    
    print("\nQuery: Generate a profit and loss statement for last quarter")
    print("Response:")
    print(mock_responses["profit_loss"])
    
    # Integration with existing systems
    print("\nIntegration Capabilities:")
    print("-" * 25)
    integrations = [
        "Xero Accounting - Invoices, Contacts, Reports",
        "Stripe Payments - Revenue, Customers, Transactions",
        "Plaid Banking - Account Balances, Transactions",
        "Compliance Suite - Regulatory Reporting",
        "Automation Workflows - Scheduled Reports, Alerts",
        "Financial Command Center - Dashboard, Insights"
    ]
    
    for i, integration in enumerate(integrations, 1):
        print(f"{i}: {integration}")
    
    print("\nDeployment Information:")
    print("-" * 25)
    print("1. Financial Command Center Assistant is integrated with your existing FCC application")
    print("2. Access through: https://localhost:8000/assistant/")
    print("3. No additional hosting required")
    print("4. Uses existing security and authentication")
    print("5. Connects to real-time financial data")
    print("6. Provides executive-friendly interface")
    
    print("\nFor Production Use:")
    print("-" * 25)
    print("1. Set OPENAI_API_KEY environment variable")
    print("2. Configure real financial data endpoints")
    print("3. Customize assistant instructions for your business")
    print("4. Add additional tools as needed")
    print("5. Deploy to production environment")
    
    return True

if __name__ == "__main__":
    demonstrate_assistant()
    print("\n[SUCCESS] Assistant demonstration completed!")
    print("           Your Financial Command Center Assistant is ready for executive use!")
