"""
Demo of high-value prompts for PE firms and SaaS CFOs using the Local LLM MCP Adapter
"""
import sys
import os
from dotenv import load_dotenv
from adapters.local_llm_mcp_adapter import local_llm_mcp_adapter

# Load environment variables
load_dotenv()

def run_demo():
    """Run a demo of enterprise financial commands"""
    print("Financial Command Center AI - Local LLM Demo")
    print("=" * 50)
    print("High-value prompts for PE firms and SaaS CFOs\n")
    
    # Demo commands for PE firms
    pe_commands = [
        "Analyze the revenue trends for the past 12 months and identify any seasonal patterns",
        "What is our current cash position and projected runway?",
        "Identify our top 5 customers by revenue and calculate their percentage of total revenue",
        "Calculate the monthly recurring revenue (MRR) and churn rate for our SaaS business",
        "Generate a comprehensive financial dashboard with key metrics"
    ]
    
    # Demo commands for SaaS CFOs
    saas_commands = [
        "Calculate our current LTV:CAC ratio and how it has changed over the past quarter",
        "Show me the accounts receivable aging report and identify any overdue invoices",
        "What is our current burn rate and how does it compare to our projections?",
        "Generate a profit and loss statement for the current quarter",
        "Analyze our expenses by category and identify areas where we can reduce costs"
    ]
    
    print("PE Firm Commands:")
    print("-" * 20)
    for i, command in enumerate(pe_commands, 1):
        print(f"{i}. {command}")
        
        # Process the command
        result = local_llm_mcp_adapter.process_query(command)
        if result["success"]:
            print(f"Response: {result['response'][:200]}..." if len(result['response']) > 200 else f"Response: {result['response']}")
            print(f"Turns used: {result['turns_used']}\n")
        else:
            print(f"Error: {result['error']}\n")
    
    print("\nSaaS CFO Commands:")
    print("-" * 20)
    for i, command in enumerate(saas_commands, 1):
        print(f"{i}. {command}")
        
        # Process the command
        result = local_llm_mcp_adapter.process_query(command)
        if result["success"]:
            print(f"Response: {result['response'][:200]}..." if len(result['response']) > 200 else f"Response: {result['response']}")
            print(f"Turns used: {result['turns_used']}\n")
        else:
            print(f"Error: {result['error']}\n")

if __name__ == "__main__":
    run_demo()