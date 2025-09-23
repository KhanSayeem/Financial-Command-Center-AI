# Financial Command Center AI - Warp MCP Integration

This directory contains **Warp-compatible MCP (Model Context Protocol) servers** for the Financial Command Center AI project. These servers provide seamless integration with Warp's AI terminal for financial management, payment processing, banking, accounting, and compliance operations.

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   pip install mcp fastmcp stripe plaid-python xero-python httpx python-jose
   ```

2. **Set Environment Variables**
   ```bash
   # Required
   export STRIPE_API_KEY="sk_test_your_stripe_key"
   export PLAID_CLIENT_ID="your_plaid_client_id"
   export PLAID_SECRET="your_plaid_secret"
   export XERO_CLIENT_ID="your_xero_client_id"
   export XERO_CLIENT_SECRET="your_xero_client_secret"
   
   # Optional
   export FCC_SERVER_URL="https://127.0.0.1:8000"
   export FCC_API_KEY="claude-desktop-integration"
   export PLAID_ENV="sandbox"
   ```

3. **Test the Servers**
   ```bash
   python tests/manual/test_warp_mcp.py
   ```

4. **Configure Warp**
   - Use `warp_mcp_config.json` for automatic server discovery
   - Or configure individual servers in Warp's MCP settings

## 📁 Warp MCP Servers

### 1. **Financial Command Center (Warp)** - `mcp_server_warp.py`
Main financial dashboard and health monitoring server.

**Tools Available:**
- `get_financial_health` - Overall financial health and system status
- `get_invoices` - Retrieve invoices with optional filtering
- `get_contacts` - Get customer/supplier contact information
- `get_financial_dashboard` - Comprehensive financial dashboard data
- `get_cash_flow` - Current cash flow information and trends
- `ping` - Health check

### 2. **Stripe Integration (Warp)** - `stripe_mcp_warp.py`
Complete Stripe payment processing, subscriptions, customers, and webhooks.

**Tools Available:**
- `process_payment` - Create and process PaymentIntents
- `check_payment_status` - Retrieve PaymentIntent status
- `process_refund` - Create full or partial refunds
- `capture_payment_intent` - Capture authorized payments
- `cancel_payment_intent` - Cancel pending payments
- `create_customer` - Create Stripe customers
- `create_setup_intent` - Save payment methods for future use
- `list_payment_methods` - List customer payment methods
- `create_product` / `create_price` - Product and pricing management
- `create_checkout_session` - Hosted checkout sessions
- `create_subscription` / `cancel_subscription` - Subscription management
- `list_payments` - Recent payment history
- `verify_webhook` - Webhook signature verification
- `ping` - Health check

### 3. **Plaid Integration (Warp)** - `plaid_mcp_warp.py`
Bank account connections, transactions, balances, and financial data.

**Tools Available:**
- `link_token_create` - Create Link tokens for account connection
- `sandbox_public_token_create` - Create sandbox tokens for testing
- `item_public_token_exchange` - Exchange public tokens for access tokens
- `accounts_and_balances` - Get account balances and details
- `transactions_get` - Fetch transaction history
- `auth_get` - Get bank account and routing numbers
- `identity_get` - Get account holder identity information
- `list_items` - Show connected bank accounts
- `remove_item` - Disconnect bank accounts
- `whoami` - Environment and configuration info
- `ping` - Health check

### 4. **Xero Integration (Warp)** - `xero_mcp_warp.py`
Xero accounting integration for invoices, contacts, and financial reports.

**Tools Available:**
- `xero_whoami` - Current tenant and authentication status
- `xero_set_tenant` - Set the active Xero tenant ID
- `xero_list_contacts` - List contacts with filtering
- `xero_create_contact` - Create new contacts
- `xero_find_contact` - Search for contacts by name
- `xero_list_invoices` - List invoices with advanced filtering
- `xero_get_invoice_pdf` - Download invoice PDFs
- `xero_delete_draft_invoice` - Delete draft invoices
- `xero_export_invoices_csv` - Export invoices to CSV
- `xero_org_info` - Organization information
- `xero_dashboard` - Multi-platform financial dashboard
- `ping` - Health check

### 5. **Compliance Suite (Warp)** - `compliance_mcp_warp.py`
Financial compliance monitoring, transaction scanning, blacklists, and audit logs.

**Tools Available:**
- `info` - Compliance suite status and configuration
- `config_set` - Update compliance settings
- `blacklist_add` - Add merchants to blacklist
- `blacklist_list` - View current blacklist entries
- `scan_plaid_transactions` - Scan transactions for compliance issues
- `audit_log_tail` - View recent audit events
- `stripe_payment_intent_status` - Check Stripe payment status
- `ping` - Health check

## ⚙️ Configuration

### Warp MCP Configuration (`warp_mcp_config.json`)
The unified configuration file allows Warp to automatically discover and manage all MCP servers:

```json
{
  "name": "Financial Command Center AI - Warp MCP Suite",
  "servers": {
    "financial-command-center-warp": { ... },
    "stripe-integration-warp": { ... },
    "plaid-integration-warp": { ... },
    "xero-mcp-warp": { ... },
    "compliance-suite-warp": { ... }
  }
}
```

### Environment Variables
All servers support environment-based configuration:

**Required:**
- `STRIPE_API_KEY` - Stripe API key (test or live)
- `PLAID_CLIENT_ID` - Plaid client ID
- `PLAID_SECRET` - Plaid secret key
- `XERO_CLIENT_ID` - Xero OAuth2 client ID
- `XERO_CLIENT_SECRET` - Xero OAuth2 client secret

**Optional:**
- `FCC_SERVER_URL` - Financial Command Center URL
- `FCC_API_KEY` - FCC API key
- `STRIPE_API_VERSION` - Stripe API version
- `PLAID_ENV` - Plaid environment (sandbox/development/production)

## 🔧 Testing

### Automated Testing
Run the comprehensive test suite:
```bash
python tests/manual/test_warp_mcp.py
```

This tests:
- Server initialization and protocol compliance
- Tool discovery and availability
- Basic functionality (ping tests)
- Environment variable configuration
- Error handling and timeouts

### Manual Testing
Test individual servers:
```bash
# Test Stripe MCP
python stripe_mcp_warp.py

# Test Plaid MCP  
python plaid_mcp_warp.py

# Test Xero MCP
python xero_mcp_warp.py
```

## 🛠️ Development

### Key Differences from Standard MCP Servers
The Warp-compatible versions use:
- **FastMCP framework** instead of custom JSON-RPC handling
- **Simplified tool definitions** with @app.tool() decorators
- **Synchronous tool execution** with asyncio wrappers where needed
- **Unified naming convention** with "-warp" suffix
- **Separate data stores** to avoid conflicts with existing servers

### File Structure
```
├── mcp_server_warp.py          # Main financial dashboard
├── stripe_mcp_warp.py          # Stripe payment processing
├── plaid_mcp_warp.py           # Plaid banking integration
├── xero_mcp_warp.py            # Xero accounting integration
├── compliance_mcp_warp.py      # Compliance monitoring
├── warp_mcp_config.json        # Unified configuration
├── test_warp_mcp.py            # Test suite
└── WARP_MCP_README.md          # This documentation
```

### Data Isolation
Each Warp server uses separate data files:
- `plaid_store_warp.json`
- `compliance_store_warp.json`
- `xero_tenant_warp.json`
- `exports_warp/` directory
- `reports_warp/` directory
- `audit_warp/` directory

## 🔒 Security

### Best Practices
1. **Environment Variables** - Store all API keys securely
2. **SSL Verification** - Enabled by default (disabled for localhost development)
3. **Webhook Verification** - Proper signature validation for all webhooks
4. **Audit Logging** - All compliance actions are logged
5. **Data Privacy** - Sensitive data is not logged or cached

### Production Considerations
- Set `MCP_STRIPE_PROD=true` for production Stripe operations
- Use production API keys and endpoints
- Enable SSL verification for all external calls
- Implement proper access controls and monitoring
- Regular audit log reviews and rotation

## 🚨 Troubleshooting

### Common Issues

**Server fails to start:**
- Check Python dependencies: `pip list | grep -E "(mcp|stripe|plaid|xero)"`
- Verify environment variables are set
- Check file permissions and paths

**API connection errors:**
- Verify API keys are valid and not expired
- Check network connectivity
- Ensure correct API endpoints (sandbox vs production)

**Warp integration issues:**
- Confirm MCP protocol version compatibility
- Check Warp's MCP configuration
- Verify server discovery method
- Review Warp error logs

### Debug Mode
Enable verbose logging:
```bash
export MCP_DEBUG=true
python stripe_mcp_warp.py
```

## 📈 Monitoring

### Health Checks
All servers include `ping` tools for monitoring:
```bash
# Check server health via MCP call
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {"name": "ping", "arguments": {}},
  "id": 1
}
```

### Audit Trails
Compliance server maintains detailed audit logs:
- All configuration changes
- Transaction scans and results
- Blacklist modifications
- System access patterns

## 🔄 Updates and Maintenance

### Updating Servers
1. Test updates in development environment
2. Run `test_warp_mcp.py` to verify compatibility
3. Update version numbers in configuration
4. Deploy with proper backup and rollback procedures

### Dependency Updates
Monitor and update dependencies regularly:
```bash
pip list --outdated
pip install --upgrade stripe plaid-python xero-python
```

## 📞 Support

### Getting Help
1. Run diagnostic tests: `python tests/manual/test_warp_mcp.py`
2. Check server logs and error messages
3. Verify environment configuration
4. Review API documentation for external services

### Contributing
When modifying Warp MCP servers:
1. Maintain compatibility with existing tools
2. Add appropriate error handling
3. Update tests and documentation
4. Follow the established naming conventions
5. Test with actual Warp integration

---

**Note**: These Warp-compatible MCP servers are designed to work alongside your existing MCP servers without conflicts. The "-warp" suffix and separate data stores ensure complete isolation.