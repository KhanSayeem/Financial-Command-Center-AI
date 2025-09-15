#!/usr/bin/env python3
"""
Warp-compatible MCP Server for Financial Command Center AI
This is a Warp-compatible version of the Financial Command Center MCP server.
"""
import asyncio
import json
import sys
import logging
from typing import Any, Dict, List, Optional
import httpx
import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create FastMCP app for Warp compatibility
app = FastMCP("financial-command-center-warp")

class FinancialCommandCenterClient:
    def __init__(self):
        self.server_url = os.getenv('FCC_SERVER_URL', 'https://127.0.0.1:8000')
        self.api_key = os.getenv('FCC_API_KEY', 'claude-desktop-integration')
        self.client = None
        
    async def setup_client(self):
        """Setup HTTP client with SSL verification disabled for localhost"""
        if not self.client:
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

# Global client instance
fcc_client = FinancialCommandCenterClient()

@app.tool()
def get_financial_health() -> Dict[str, Any]:
    """Get overall financial health and system status"""
    async def _get_health():
        return await fcc_client.call_api('/health')
    
    return asyncio.run(_get_health())

@app.tool()
def get_invoices(status: Optional[str] = None, amount_min: Optional[float] = None, customer: Optional[str] = None) -> Dict[str, Any]:
    """Get invoices with optional filtering"""
    async def _get_invoices():
        filters = {}
        if status:
            filters['status'] = status
        if amount_min is not None:
            filters['amount_min'] = amount_min
        if customer:
            filters['customer'] = customer
            
        endpoint = '/api/invoices'
        if filters:
            params = '&'.join([f"{k}={v}" for k, v in filters.items()])
            endpoint += f"?{params}"
        return await fcc_client.call_api(endpoint)
    
    return asyncio.run(_get_invoices())

@app.tool()
def get_contacts(search_term: Optional[str] = None) -> Dict[str, Any]:
    """Get customer/supplier contacts"""
    async def _get_contacts():
        endpoint = '/api/contacts'
        if search_term:
            endpoint += f"?search={search_term}"
        return await fcc_client.call_api(endpoint)
    
    return asyncio.run(_get_contacts())

@app.tool()
def get_financial_dashboard() -> Dict[str, Any]:
    """Get financial dashboard data"""
    async def _get_dashboard():
        return await fcc_client.call_api('/api/dashboard')
    
    return asyncio.run(_get_dashboard())

@app.tool()
def get_cash_flow() -> Dict[str, Any]:
    """Get cash flow information"""
    async def _get_cash_flow():
        return await fcc_client.call_api('/api/cash-flow')
    
    return asyncio.run(_get_cash_flow())

@app.tool()
def ping() -> Dict[str, Any]:
    """Test connectivity to the Financial Command Center server"""
    return {
        "server": "financial-command-center-warp",
        "timestamp": datetime.now().isoformat(),
        "status": "ready",
        "environment_check": {
            "fcc_server_url": os.getenv('FCC_SERVER_URL', 'https://127.0.0.1:8000'),
            "fcc_api_key_set": bool(os.getenv('FCC_API_KEY'))
        }
    }

if __name__ == "__main__":
    app.run()