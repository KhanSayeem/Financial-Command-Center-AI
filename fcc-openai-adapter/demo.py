"""
Main demo script showing how to use the FCC-OpenAI adapter.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adapters.openai_mcp_adapter import openai_mcp_adapter
from demos.demo_enterprise_commands import demo_commands

def run_demo():
    """Run a demo of the FCC-OpenAI adapter."""
    print("FCC-OpenAI Adapter Demo")
    print("=" * 50)
    
    # Show available demo commands
    print("\nAvailable Demo Commands:")
    for i, cmd in enumerate(demo_commands, 1):
        print(f"{i}. {cmd['name']}")
        print(f"   {cmd['description']}\n")
    
    # Run the first demo command as an example
    if demo_commands:
        print("Running demo: Portfolio Company Financial Health Assessment")
        print("-" * 50)
        
        result = openai_mcp_adapter.process_query(demo_commands[0]['prompt'])
        
        if result['success']:
            print("Response:")
            print(result['response'])
            print(f"\nTurns used: {result['turns_used']}")
        else:
            print(f"Error: {result['error']}")

if __name__ == "__main__":
    run_demo()