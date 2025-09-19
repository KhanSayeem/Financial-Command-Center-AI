# FCC-Local-LLM-Adapter

This adapter connects local LLMs (Ollama or LM Studio) to the Financial Command Center AI's MCP servers, enabling natural language financial analysis and operations without requiring API keys or internet connectivity.

## Features

- Routes local LLM tool calls to appropriate localhost MCP endpoints
- Handles self-signed SSL certificates for development
- Implements safety mechanisms with max turn limits
- Supports streaming responses
- Works with all FCC-AI MCP servers (Xero, Stripe, Plaid, Compliance, etc.)
- Compatible with both Ollama and LM Studio

## Setup

1. Install a local LLM provider:
   - **Ollama**: Download from [ollama.com](https://ollama.com)
   - **LM Studio**: Download from [lmstudio.ai](https://lmstudio.ai)

2. Pull or download a language model:
   - For Ollama: `ollama pull llama3.2`
   - For LM Studio: Use the interface to download a model

3. Start the local LLM server:
   - For Ollama: The server starts automatically when installed
   - For LM Studio: Start the local server within the application

4. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

5. Configure environment variables in `.env`:
   - `LLM_PROVIDER`: Either "ollama" or "lmstudio" (default: "ollama")
   - `LLM_BASE_URL`: URL of your local LLM server (default: "http://localhost:11434/v1" for Ollama)
   - `LLM_MODEL`: The model to use (default: "llama3.2")
   - `MCP_SERVER_URL`: URL of your MCP server (default: https://127.0.0.1:8000)

## Usage

```python
from adapters.local_llm_mcp_adapter import local_llm_mcp_adapter

# Process a query with tool calling
result = local_llm_mcp_adapter.process_query("Show me our current financial health score")
print(result['response'])
```

## Components

- `models/tool_schemas.py`: Tool schemas matching FCC-AI's MCP methods
- `utils/mcp_router.py`: Routes local LLM function calls to MCP endpoints
- `adapters/local_llm_mcp_adapter.py`: Main adapter with safety mechanisms
- `config/settings.py`: Configuration settings

## MCP Servers Supported

- Xero Integration
- Stripe Payments
- Plaid Banking
- Compliance Suite
- Financial Command Center
- Automation Workflows

## Benefits

- **No API keys required**: Works entirely locally
- **No internet connectivity needed**: All processing happens on your machine
- **Privacy focused**: Data never leaves your local environment
- **Cost effective**: No per-request charges
- **Consistent with existing setup**: Uses the same MCP server URLs (https://127.0.0.1:8000)