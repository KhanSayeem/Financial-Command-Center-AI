"""
Local LLM MCP Adapter that works with Ollama or LM Studio and loops tool calls through MCPRouter until final response.
Includes max_turns safety mechanism.
"""
import json
import requests
from typing import List, Dict, Any, Optional
from config.settings import LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL, MAX_TURNS
from models.tool_schemas import all_tools
from utils.mcp_router import mcp_router

class LocalLLMMCPAdapter:
    def __init__(self, model: str = LLM_MODEL):
        """
        Initialize the Local LLM MCP Adapter.
        
        Args:
            model: Local LLM model to use (default: llama3.2)
        """
        self.model = model
        self.max_turns = MAX_TURNS
        self.base_url = LLM_BASE_URL
        
        # Set provider-specific settings
        if LLM_PROVIDER.lower() == "ollama":
            self.chat_endpoint = f"{self.base_url}/chat/completions"
        elif LLM_PROVIDER.lower() == "lmstudio":
            self.chat_endpoint = f"{self.base_url}/chat/completions"
        else:
            raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

    def _make_api_call(self, messages: List[Dict[str, str]], tools: List[Dict] = None) -> Dict[str, Any]:
        """
        Make an API call to the local LLM.
        
        Args:
            messages: Conversation messages
            tools: Tools available for function calling
            
        Returns:
            Response from the local LLM
        """
        # Use the model name as-is, Ollama will handle versioning
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        # Add tools if provided
        if tools:
            # Convert tools to the format expected by the local LLM
            converted_tools = []
            for tool in tools:
                if "function" in tool:
                    converted_tools.append({
                        "type": "function",
                        "function": tool["function"]
                    })
                else:
                    converted_tools.append(tool)
            payload["tools"] = converted_tools
            payload["tool_choice"] = "auto"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.chat_endpoint,
                headers=headers,
                json=payload,
                timeout=120  # Longer timeout for local LLM processing
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Local LLM API returned status {response.status_code}",
                    "details": response.text
                }
        except Exception as e:
            return {
                "error": str(e)
            }

    def process_query(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Process a query through the Local LLM MCP adapter with tool calling.
        
        Args:
            query: User query to process
            conversation_history: Previous conversation messages (optional)
            
        Returns:
            Final response from Local LLM after processing all tool calls
        """
        # Initialize conversation messages
        messages = conversation_history or []
        messages.append({"role": "user", "content": query})
        
        turn_count = 0
        
        while turn_count < self.max_turns:
            try:
                # Call Local LLM with tools
                response = self._make_api_call(messages, all_tools)
                
                # Check for errors
                if "error" in response:
                    return {
                        "success": False,
                        "error": response["error"],
                        "details": response.get("details"),
                        "messages": messages,
                        "turns_used": turn_count
                    }
                
                # Get the response message
                if "choices" in response and len(response["choices"]) > 0:
                    response_message = response["choices"][0]["message"]
                else:
                    return {
                        "success": False,
                        "error": "Invalid response from Local LLM",
                        "messages": messages,
                        "turns_used": turn_count
                    }
                
                messages.append(response_message)
                
                # Check if there are tool calls
                tool_calls = response_message.get("tool_calls")
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
                    # No more tool calls, return final response
                    return {
                        "success": True,
                        "response": response_message.get("content", ""),
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
                # Call Local LLM with tools (streaming)
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "tools": all_tools,
                    "tool_choice": "auto",
                    "stream": True
                }
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    self.chat_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=120,
                    stream=True
                )
                
                if response.status_code != 200:
                    yield {"type": "error", "error": f"Local LLM API returned status {response.status_code}"}
                    return
                
                # Collect the full response
                full_response = ""
                tool_calls = []
                current_tool_call = None
                
                # Process streaming response
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            data = decoded_line[6:]  # Remove "data: " prefix
                            if data == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    
                                    if "content" in delta and delta["content"]:
                                        full_response += delta["content"]
                                        yield {"type": "content", "content": delta["content"]}
                                    elif "tool_calls" in delta:
                                        # Handle tool calls in streaming response
                                        for tool_chunk in delta["tool_calls"]:
                                            if "index" in tool_chunk:
                                                index = tool_chunk["index"]
                                                if len(tool_calls) <= index:
                                                    tool_calls.append({
                                                        "id": "",
                                                        "type": "function",
                                                        "function": {"name": "", "arguments": ""}
                                                    })
                                                
                                                if "id" in tool_chunk:
                                                    tool_calls[index]["id"] = tool_chunk["id"]
                                                
                                                if "function" in tool_chunk:
                                                    func_chunk = tool_chunk["function"]
                                                    if "name" in func_chunk:
                                                        tool_calls[index]["function"]["name"] += func_chunk["name"]
                                                    if "arguments" in func_chunk:
                                                        tool_calls[index]["function"]["arguments"] += func_chunk["arguments"]
                            except json.JSONDecodeError:
                                continue
                
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
local_llm_mcp_adapter = LocalLLMMCPAdapter()