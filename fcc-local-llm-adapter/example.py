"""
Example usage of the Local LLM MCP Adapter
"""
import os
from dotenv import load_dotenv
from adapters.local_llm_mcp_adapter import local_llm_mcp_adapter

# Load environment variables
load_dotenv()

def main():
    # Example 1: Simple query
    print("=== Example 1: Simple Query ===")
    result = local_llm_mcp_adapter.process_query("What is the financial health of my business?")
    if result["success"]:
        print("Response:", result["response"])
        print("Turns used:", result["turns_used"])
    else:
        print("Error:", result["error"])
    
    print("\n" + "="*50 + "\n")
    
    # Example 2: Query with tool calling
    print("=== Example 2: Query with Tool Calling ===")
    result = local_llm_mcp_adapter.process_query("Show me the list of contacts in my Xero account")
    if result["success"]:
        print("Response:", result["response"])
        print("Turns used:", result["turns_used"])
    else:
        print("Error:", result["error"])
    
    print("\n" + "="*50 + "\n")
    
    # Example 3: Streaming response
    print("=== Example 3: Streaming Response ===")
    print("Streaming response for: 'Generate a financial dashboard report'")
    for chunk in local_llm_mcp_adapter.stream_process_query("Generate a financial dashboard report"):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "tool_response":
            print(f"\n[Tool Response: {chunk['tool']}]")
        elif chunk["type"] == "error":
            print(f"\n[Error: {chunk['error']}]")
            break
        elif chunk["type"] == "end":
            print(f"\n[Completed in {chunk['turns_used']} turns]")
            break

if __name__ == "__main__":
    main()