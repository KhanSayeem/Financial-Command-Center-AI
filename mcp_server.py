#!/usr/bin/env python3
"""
MCP Server for Financial Command Center AI
This is a proper MCP (Model Context Protocol) server that Claude Desktop can connect to.
"""
import asyncio
import json
import sys
import logging
from typing import Any, Dict, List
import httpx
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinancialCommandCenterMCP:
    def __init__(self):
        self.server_url = os.getenv('FCC_SERVER_URL', 'https://localhost:8000')
        self.api_key = os.getenv('FCC_API_KEY', 'claude-desktop-integration')
        self.client = None
        
    async def setup_client(self):
        """Setup HTTP client with SSL verification disabled for localhost"""
        self.client = httpx.AsyncClient(
            verify=False,  # Disable SSL verification for localhost
            timeout=30.0,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
    
    async def call_api(self, endpoint: str, method: str = 'GET', data: Dict = None):
        """Make API call to Financial Command Center"""
        try:
            if not self.client:
                await self.setup_client()
            
            url = f"{self.server_url}{endpoint}"
            logger.info(f"Calling {method} {url}")
            
            if method == 'GET':
                response = await self.client.get(url)
            elif method == 'POST':
                response = await self.client.post(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.ConnectError as e:
            logger.error(f"Connection failed to {self.server_url}: {e}")
            return {
                "error": f"Cannot connect to Financial Command Center at {self.server_url}. Make sure the server is running.",
                "status": "connection_failed"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            return {
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "status": "http_error"
            }
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return {
                "error": str(e),
                "status": "unknown_error"
            }
    
    async def get_financial_health(self):
        """Get overall financial health and system status"""
        return await self.call_api('/health')
    
    async def get_invoices(self, filters: Dict = None):
        """Get invoices with optional filtering"""
        endpoint = '/api/invoices'
        if filters:
            # Convert filters to query parameters
            params = '&'.join([f"{k}={v}" for k, v in filters.items()])
            endpoint += f"?{params}"
        return await self.call_api(endpoint)
    
    async def get_contacts(self, search_term: str = None):
        """Get customer/supplier contacts"""
        endpoint = '/api/contacts'
        if search_term:
            endpoint += f"?search={search_term}"
        return await self.call_api(endpoint)
    
    async def get_financial_dashboard(self):
        """Get financial dashboard data"""
        return await self.call_api('/api/dashboard')
    
    async def get_cash_flow(self):
        """Get cash flow information"""
        return await self.call_api('/api/cash-flow')
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests"""
        try:
            method = request.get('method')
            params = request.get('params', {})
            
            if method == 'tools/list':
                return {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "result": {
                        "tools": [
                            {
                                "name": "get_financial_health",
                                "description": "Get overall financial health and system status",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            },
                            {
                                "name": "get_invoices",
                                "description": "Retrieve invoices with optional filtering",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string", "description": "Invoice status filter"},
                                        "amount_min": {"type": "number", "description": "Minimum amount filter"},
                                        "customer": {"type": "string", "description": "Customer name filter"}
                                    },
                                    "required": []
                                }
                            },
                            {
                                "name": "get_contacts",
                                "description": "Get customer/supplier contact information",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "search_term": {"type": "string", "description": "Search term for contact lookup"}
                                    },
                                    "required": []
                                }
                            },
                            {
                                "name": "get_cash_flow",
                                "description": "Get current cash flow information and trends",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            },
                            {
                                "name": "get_financial_dashboard", 
                                "description": "Get comprehensive financial dashboard data",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            }
                        ]
                    }
                }
            
            elif method == 'tools/call':
                tool_name = params.get('name')
                tool_arguments = params.get('arguments', {})
                
                if tool_name == 'get_financial_health':
                    result = await self.get_financial_health()
                elif tool_name == 'get_invoices':
                    result = await self.get_invoices(tool_arguments)
                elif tool_name == 'get_contacts':
                    search_term = tool_arguments.get('search_term')
                    result = await self.get_contacts(search_term)
                elif tool_name == 'get_cash_flow':
                    result = await self.get_cash_flow()
                elif tool_name == 'get_financial_dashboard':
                    result = await self.get_financial_dashboard()
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")
                
                return {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }
            
            elif method == 'initialize':
                return {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "prompts": {},
                            "resources": {}
                        },
                        "serverInfo": {
                            "name": "financial-command-center",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == 'prompts/list':
                return {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "result": {
                        "prompts": []
                    }
                }
            
            elif method == 'resources/list':
                return {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "result": {
                        "resources": []
                    }
                }
            
            elif method == 'notifications/initialized':
                # This is a notification, no response needed
                logger.info("Received initialized notification")
                return None  # No response for notifications
            
            else:
                logger.warning(f"Unknown method: {method}")
                raise ValueError(f"Unknown method: {method}")
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Financial Command Center MCP Server...")
        
        try:
            while True:
                # Read JSON-RPC request from stdin
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                try:
                    request = json.loads(line.strip())
                    logger.info(f"Received request: {request.get('method')}")
                    
                    response = await self.handle_request(request)
                    
                    # Only send response if it's not None (notifications don't need responses)
                    if response is not None:
                        print(json.dumps(response), flush=True)
                        logger.info(f"Sent response for request ID: {request.get('id')}")
                    else:
                        logger.info(f"No response needed for notification: {request.get('method')}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32603,
                            "message": str(e)
                        }
                    }
                    print(json.dumps(error_response), flush=True)
        
        finally:
            if self.client:
                await self.client.aclose()
            logger.info("MCP Server shutdown complete")

async def main():
    """Main entry point"""
    server = FinancialCommandCenterMCP()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())