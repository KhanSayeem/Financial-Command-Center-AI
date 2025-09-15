# 🚀 Adding Financial Command Center MCP Servers to Warp

Since Warp is looking for files in its own directory, here are the two ways to add your MCP servers:

## Option 1: Add Individual Servers (Recommended)

Add each server individually in Warp's MCP settings:

### 1. **Stripe Integration (Warp)**
```json
{
  "command": "python",
  "args": ["C:\\Users\\Hi\\Documents\\GitHub\\Stripe Playground\\Financial-Command-Center-AI\\stripe_mcp_warp.py"],
  "env": {
    "STRIPE_API_KEY": "sk_test_your_stripe_api_key_here",
    "STRIPE_API_VERSION": "2024-06-20",
    "STRIPE_DEFAULT_CURRENCY": "usd",
    "MCP_STRIPE_PROD": "false"
  }
}
```

### 2. **Plaid Integration (Warp)**
```json
{
  "command": "python",
  "args": ["C:\\Users\\Hi\\Documents\\GitHub\\Stripe Playground\\Financial-Command-Center-AI\\plaid_mcp_warp.py"],
  "env": {
    "PLAID_CLIENT_ID": "your_plaid_client_id_here",
    "PLAID_SECRET": "your_plaid_secret_here",
    "PLAID_ENV": "sandbox"
  }
}
```

### 3. **Xero Integration (Warp)**
```json
{
  "command": "python",
  "args": ["C:\\Users\\Hi\\Documents\\GitHub\\Stripe Playground\\Financial-Command-Center-AI\\xero_mcp_warp.py"],
  "env": {
    "XERO_CLIENT_ID": "your_xero_client_id_here",
    "XERO_CLIENT_SECRET": "your_xero_client_secret_here"
  }
}
```

### 4. **Financial Command Center (Warp)**
```json
{
  "command": "python",
  "args": ["C:\\Users\\Hi\\Documents\\GitHub\\Stripe Playground\\Financial-Command-Center-AI\\mcp_server_warp.py"],
  "env": {
    "FCC_SERVER_URL": "https://127.0.0.1:8000",
    "FCC_API_KEY": "claude-desktop-integration",
    "STRIPE_API_KEY": "sk_test_your_stripe_api_key_here",
    "PLAID_CLIENT_ID": "your_plaid_client_id_here",
    "PLAID_SECRET": "your_plaid_secret_here",
    "PLAID_ENV": "sandbox",
    "XERO_CLIENT_ID": "your_xero_client_id_here",
    "XERO_CLIENT_SECRET": "your_xero_client_secret_here"
  }
}
```

### 5. **Compliance Suite (Warp)**
```json
{
  "command": "python",
  "args": ["C:\\Users\\Hi\\Documents\\GitHub\\Stripe Playground\\Financial-Command-Center-AI\\compliance_mcp_warp.py"],
  "env": {
    "PLAID_CLIENT_ID": "your_plaid_client_id_here",
    "PLAID_SECRET": "your_plaid_secret_here",
    "PLAID_ENV": "sandbox",
    "STRIPE_API_KEY": "sk_test_your_stripe_api_key_here"
  }
}
```

## Option 2: Copy Files to Warp Directory

If Warp insists on looking in its own directory, copy the files there:

```powershell
# Copy all Warp MCP servers to Warp's directory
Copy-Item "C:\Users\Hi\Documents\GitHub\Stripe Playground\Financial-Command-Center-AI\*_warp.py" "C:\Users\Hi\AppData\Local\Programs\Warp\"
```

Then use the simpler config:
```json
{
  "mcpServers": {
    "stripe-integration-warp": {
      "command": "python",
      "args": ["stripe_mcp_warp.py"],
      "env": {
        "STRIPE_API_KEY": "sk_test_your_stripe_api_key_here"
      }
    }
  }
}
```

## Option 3: Manual Steps in Warp

1. Open Warp
2. Go to Settings → MCP Servers
3. Click "Add Server"
4. Give it a name (e.g., "Stripe Integration Warp")
5. Paste the JSON configuration from Option 1
6. Click "Start" to test the connection
7. Repeat for each server

## 🔧 Troubleshooting

**If servers fail to start:**
- Verify Python is in your PATH: `python --version`
- Test server manually: `python stripe_mcp_warp.py` 
- Check environment variables are set: run `.\set_env_vars.ps1`
- Check file paths are correct and files exist

**Expected Results:**
- ✅ **Stripe**: 20 payment processing tools
- ✅ **Plaid**: 11 banking and transaction tools  
- ✅ **Xero**: 12 accounting and invoice tools
- ✅ **Financial Command Center**: 6 dashboard tools
- ✅ **Compliance**: 8 monitoring and audit tools

**Total: 57 financial tools available in Warp!** 🎉