"""
Example usage of the FCC-OpenAI adapter.
"""

import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.openai_mcp_adapter import openai_mcp_adapter

def main():
    """Example usage of the adapter."""
    print("FCC-OpenAI Adapter Example")
    print("=" * 40)
    
    # Example 1: Simple query
    print("\n1. Simple Financial Query:")
    query1 = "What is our current financial health score?"
    result1 = openai_mcp_adapter.process_query(query1)
    
    if result1['success']:
        print(f"Response: {result1['response']}")
    else:
        print(f"Error: {result1['error']}")
    
    # Example 2: Complex analysis request
    print("\n2. Complex Analysis Request:")
    query2 = """I need to understand our cash flow situation. 
    Please analyze our recent transactions and provide insights on:
    1. Current cash position
    2. Monthly cash flow trends
    3. Largest expense categories
    4. Recommendations for improvement"""
    
    result2 = openai_mcp_adapter.process_query(query2)
    
    if result2['success']:
        print(f"Response: {result2['response']}")
    else:
        print(f"Error: {result2['error']}")

if __name__ == "__main__":
    main()