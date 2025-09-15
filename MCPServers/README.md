# MCPServers Directory - Portable Warp MCP Integration

## 📁 What This Directory Contains

This `MCPServers` directory contains all the Warp-compatible MCP servers that work with your Financial Command Center AI project. These files are automatically included when users download your project, ensuring the Warp integration works out-of-the-box on any computer.

### 🔧 MCP Server Files:
- **`mcp_server_warp.py`** - Main Financial Command Center MCP server
- **`stripe_mcp_warp.py`** - Stripe payment processing integration
- **`plaid_mcp_warp.py`** - Plaid banking data integration  
- **`xero_mcp_warp.py`** - Xero accounting integration
- **`compliance_mcp_warp.py`** - Financial compliance monitoring
- **`xero_client.py`** - Xero API client helper
- **`xero_tenant_warp.json`** - Xero tenant configuration
- **`tokens/`** - Directory for OAuth tokens and credentials

## 🎯 Why This Approach Works

### ✅ **Portable for All Users**
- **No manual setup required** - All MCP servers are included in the project
- **Works on any computer** - Paths are dynamically generated based on user's download location
- **Cross-platform compatible** - Works on Windows, macOS, and Linux
- **No external dependencies** - Self-contained within the project

### ✅ **Consistent with Working Configuration**
Based on analysis of your working Warp configuration, this approach uses:
- **Simple `python` command** instead of complex virtual environment paths
- **Forward slash paths** for cross-platform compatibility
- **Null working directory** as expected by Warp
- **Project-relative paths** that work anywhere the project is downloaded

## 🚀 How It Works for End Users

### 1. **Download Project**
When users download the Financial Command Center AI project, they automatically get:
```
Financial-Command-Center-AI/
├── MCPServers/           ← All MCP servers included
│   ├── mcp_server_warp.py
│   ├── stripe_mcp_warp.py
│   ├── plaid_mcp_warp.py
│   ├── xero_mcp_warp.py
│   ├── compliance_mcp_warp.py
│   └── ...
├── warp_integration.py   ← Generates portable config
└── ...
```

### 2. **Generate Configuration**
The Warp setup wizard (`/warp/setup`) automatically generates paths like:
```json
{
  "mcpServers": {
    "compliance-suite-warp": {
      "command": "python",
      "args": ["[USER_PATH]/Financial-Command-Center-AI/MCPServers/compliance_mcp_warp.py"],
      "working_directory": null,
      "env": { ... }
    }
  }
}
```

### 3. **Works Everywhere**
Whether the user downloads to:
- `C:\Users\John\Downloads\Financial-Command-Center-AI\`
- `/home/jane/projects/Financial-Command-Center-AI/`
- `C:\Projects\MyFinance\Financial-Command-Center-AI\`

The configuration will always use the correct paths to their `MCPServers` directory.

## 🔧 Technical Implementation

### **Dynamic Path Generation**
```python
# Get user's project directory (works anywhere they downloaded it)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Create path to MCPServers within their download
mcp_servers_dir = os.path.join(current_dir, "MCPServers").replace('\\', '/')

# Generate server config
"args": [f"{mcp_servers_dir}/compliance_mcp_warp.py"]
```

### **Benefits Over Static Paths**
- ❌ **Static Path**: `"C:/MCPServers/script.py"` (only works if user has this exact directory)
- ✅ **Dynamic Path**: `"[USER_DOWNLOAD_PATH]/MCPServers/script.py"` (works wherever user downloads)

## 📋 File Validation

All MCP servers in this directory have been tested and validated:
- ✅ **Import successfully** without errors
- ✅ **Load required dependencies** (FastMCP, API clients)
- ✅ **Environment variable access** works correctly
- ✅ **Cross-platform compatibility** verified

## 🔐 Security Considerations

### **Credential Management**
- **Environment variables**: All API keys loaded from environment, not hardcoded
- **Token storage**: OAuth tokens stored in `tokens/` subdirectory
- **Configuration isolation**: Each MCP server manages its own credentials

### **Safe Defaults**
- **Sandbox mode**: Plaid integration defaults to sandbox environment
- **Test API keys**: Stripe integration uses test keys by default
- **Local storage**: All data stored locally, not transmitted to third parties

## 🎉 Result: Universal Compatibility

This approach ensures that **every user** who downloads the Financial Command Center AI project can:

1. **✅ Complete the setup wizard** with their API credentials
2. **✅ Visit `/warp/setup`** to generate their personalized config
3. **✅ Download a working `warp_mcp_config.json`** file
4. **✅ Add it to Warp Terminal** and have all 5 MCP servers work immediately
5. **✅ Use AI commands** like "Show me our financial health" right away

No matter where they downloaded the project or what their directory structure looks like! 🚀