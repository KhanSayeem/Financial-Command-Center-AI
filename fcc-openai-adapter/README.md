# FCC-OpenAI Adapter

This adapter connects OpenAI's GPT-4o to the Financial Command Center AI's MCP servers, enabling natural language financial analysis and operations.

## Features

- Routes OpenAI tool calls to appropriate localhost MCP endpoints
- Handles self-signed SSL certificates for development
- Implements safety mechanisms with max turn limits
- Supports streaming responses
- Works with all FCC-AI MCP servers (Xero, Stripe, Plaid, Compliance, etc.)

## Setup

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env`:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `MCP_SERVER_URL`: URL of your MCP server (default: https://localhost:8000)

## Usage

```python
from adapters.openai_mcp_adapter import openai_mcp_adapter

# Process a query with tool calling
result = openai_mcp_adapter.process_query("Show me our current financial health score")
print(result['response'])
```

## Components

- `models/tool_schemas.py`: Tool schemas matching FCC-AI's MCP methods
- `utils/mcp_router.py`: Routes GPT-4o function calls to MCP endpoints
- `adapters/openai_mcp_adapter.py`: Main adapter with safety mechanisms
- `demos/demo_enterprise_commands.py`: High-value prompts for PE firms and SaaS CFOs

## MCP Servers Supported

- Xero Integration
- Stripe Payments
- Plaid Banking
- Compliance Suite
- Financial Command Center
- Automation Workflows