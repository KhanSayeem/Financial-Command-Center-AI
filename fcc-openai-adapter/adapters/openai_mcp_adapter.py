"""
OpenAI MCP Adapter using OpenAI SDK that loops tool calls through MCPRouter until final response.
Includes max_turns safety mechanism.
"""

import openai
import json
from typing import List, Dict, Any, Optional
from config.settings import OPENAI_API_KEY, MAX_TURNS
from models.tool_schemas import all_tools
from utils.mcp_router import mcp_router

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

class OpenAIMCPAdapter:
    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize the OpenAI MCP Adapter.
        
        Args:
            model: OpenAI model to use (default: gpt-4o)
        """
        self.model = model
        self.max_turns = MAX_TURNS

    def process_query(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Process a query through the OpenAI MCP adapter with tool calling.
        
        Args:
            query: User query to process
            conversation_history: Previous conversation messages (optional)
            
        Returns:
            Final response from OpenAI after processing all tool calls
        """
        # Initialize conversation messages
        messages = conversation_history or []
        messages.append({"role": "user", "content": query})
        
        turn_count = 0
        
        while turn_count < self.max_turns:
            try:
                # Call OpenAI with tools
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=all_tools,
                    tool_choice="auto"
                )
                
                # Get the response message
                response_message = response.choices[0].message
                messages.append(response_message)
                
                # Check if there are tool calls
                tool_calls = getattr(response_message, 'tool_calls', None)
                if tool_calls:
                    # Process each tool call
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Route the tool call through MCP router
                        tool_response = mcp_router.route_tool_call(function_name, function_args)
                        
                        # Add tool response to messages
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(tool_response)
                        })
                    
                    # Increment turn count
                    turn_count += 1
                else:
                    # No more tool calls, return final response
                    return {
                        "success": True,
                        "response": response_message.content,
                        "messages": messages,
                        "turns_used": turn_count
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "messages": messages,
                    "turns_used": turn_count
                }
        
        # Max turns reached
        return {
            "success": False,
            "error": f"Max turns ({self.max_turns}) reached. Conversation may be stuck in a loop.",
            "messages": messages,
            "turns_used": turn_count
        }

    def stream_process_query(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None):
        """
        Process a query with streaming response.
        
        Args:
            query: User query to process
            conversation_history: Previous conversation messages (optional)
            
        Yields:
            Chunks of the response as they are generated
        """
        # Initialize conversation messages
        messages = conversation_history or []
        messages.append({"role": "user", "content": query})
        
        turn_count = 0
        
        while turn_count < self.max_turns:
            try:
                # Call OpenAI with tools (streaming)
                stream = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=all_tools,
                    tool_choice="auto",
                    stream=True
                )
                
                # Collect the full response
                full_response = ""
                tool_calls = []
                current_tool_call = None
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        yield {"type": "content", "content": chunk.choices[0].delta.content}
                    elif chunk.choices[0].delta.tool_calls:
                        # Handle tool calls in streaming response
                        for tool_chunk in chunk.choices[0].delta.tool_calls:
                            if tool_chunk.id:
                                # New tool call
                                current_tool_call = {
                                    "id": tool_chunk.id,
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                }
                                tool_calls.append(current_tool_call)
                            elif tool_chunk.function:
                                # Update current tool call
                                if current_tool_call:
                                    if tool_chunk.function.name:
                                        current_tool_call["function"]["name"] += tool_chunk.function.name
                                    if tool_chunk.function.arguments:
                                        current_tool_call["function"]["arguments"] += tool_chunk.function.arguments
                
                # Add assistant message to conversation
                messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "tool_calls": tool_calls if tool_calls else None
                })
                
                # Check if there are tool calls to process
                if tool_calls:
                    # Process each tool call
                    for tool_call in tool_calls:
                        function_name = tool_call["function"]["name"]
                        try:
                            function_args = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            function_args = {}
                        
                        # Route the tool call through MCP router
                        tool_response = mcp_router.route_tool_call(function_name, function_args)
                        
                        # Yield tool response
                        yield {"type": "tool_response", "tool": function_name, "response": tool_response}
                        
                        # Add tool response to messages
                        messages.append({
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(tool_response)
                        })
                    
                    # Increment turn count
                    turn_count += 1
                else:
                    # No more tool calls, end the conversation
                    yield {"type": "end", "turns_used": turn_count}
                    return
                    
            except Exception as e:
                yield {"type": "error", "error": str(e)}
                return
        
        # Max turns reached
        yield {
            "type": "error",
            "error": f"Max turns ({self.max_turns}) reached. Conversation may be stuck in a loop."
        }

# Global instance of the adapter
openai_mcp_adapter = OpenAIMCPAdapter()