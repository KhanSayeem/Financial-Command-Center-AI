# Financial Automation & Workflows

A comprehensive automation system for your Financial Command Center AI that provides smart automation, ML-powered categorization, real-time alerts, and intelligent workflows.

## Features

### Smart Automation
- **auto_send_payment_reminders()**: Automatically send overdue invoice alerts
- **auto_categorize_expenses()**: ML-powered expense categorization
- **schedule_recurring_invoice_creation()**: Subscription-like invoicing automation
- **auto_reconcile_payments()**: Match payments to invoices automatically

### Notifications & Alerts
- **setup_low_balance_alerts()**: Cash flow warnings
- **setup_large_transaction_alerts()**: Unusual activity monitoring
- **setup_payment_received_notifications()**: Real-time payment alerts

### Additional Features
- Advanced fraud detection patterns
- Cash flow forecasting
- Customer payment behavior analysis
- Revenue anomaly detection
- Tax compliance reporting
- Comprehensive audit trails

## Quick Start

### 1. Install Dependencies
```bash
pip install scikit-learn pandas numpy schedule
```

### 2. Set Environment Variables
```bash
# Required for Plaid integration
set PLAID_CLIENT_ID=your_plaid_client_id
set PLAID_SECRET=your_plaid_secret
set PLAID_ENV=sandbox

# Optional integrations
set STRIPE_API_KEY=your_stripe_key
set XERO_CLIENT_ID=your_xero_client_id
```

### 3. Configure Automation
```bash
# Launch GUI configuration tool
python automation_config_manager.py --gui

# Or use CLI
python automation_config_manager.py --summary
```

### 4. Test the System
```bash
# Run comprehensive tests
python scripts/utilities/simple_automation_test.py

# View Warp dashboard
python automation_mcp_warp.py dashboard
```

### 5. Start Automation
```bash
# Start the automation scheduler
python automation_mcp_warp.py start
```

## Warp Terminal Integration

The system includes specialized Warp terminal integration for beautiful command-line interfaces:

```bash
# Dashboard overview
python automation_mcp_warp.py dashboard

# Check system status
python automation_mcp_warp.py status

# Setup wizard
python automation_mcp_warp.py setup

# Send payment reminders
python automation_mcp_warp.py reminders

# Check balance alerts
python automation_mcp_warp.py balance <account_key>

# Monitor transactions
python automation_mcp_warp.py monitor <account_key> [hours]

# Categorize expenses with AI
python automation_mcp_warp.py categorize <account_key> [days]

# Start/stop automation
python automation_mcp_warp.py start
python automation_mcp_warp.py stop
```

## Configuration

### Email Settings
Configure SMTP settings for notifications:
```json
{
  "email_settings": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your-email@gmail.com",
    "sender_password": "your-app-password",
    "recipients": ["notify@yourcompany.com"]
  }
}
```

### Alert Thresholds
```json
{
  "alerts": {
    "low_balance_threshold": 1000.0,
    "large_transaction_threshold": 5000.0,
    "payment_received_minimum": 0.0
  }
}
```

### Automation Schedule
```json
{
  "automation_schedule": {
    "payment_reminders": "09:00",
    "expense_categorization": "10:00",
    "recurring_invoices": "08:00",
    "balance_checks": "hourly"
  }
}
```

## Architecture

### Core Components

1. **automation_mcp.py**: Main automation engine with FastMCP tools
2. **automation_mcp_warp.py**: Warp terminal integration layer
3. **automation_config_manager.py**: Configuration management with GUI
4. **test_automation_workflows.py**: Comprehensive test suite

### MCP Integration

The automation system integrates seamlessly with your existing MCP infrastructure:
- Uses FastMCP for tool definitions
- Compatible with existing Plaid, Stripe, and Xero MCPs
- Follows established patterns for configuration and data storage

### ML Components

Machine learning features require additional dependencies:
- **scikit-learn**: For expense categorization
- **pandas**: For data processing
- **numpy**: For mathematical operations

### Security Features

- Secure configuration storage
- Audit logging for all operations
- Optional email encryption
- API key rotation support
- Data retention policies

## Testing

### Run All Tests
```bash
python tests/manual/test_automation_workflows.py
```

### Run Simple Tests
```bash
python scripts/utilities/simple_automation_test.py
```

### Manual Testing
```bash
# Test configuration
python automation_config_manager.py --validate

# Test individual components
python automation_mcp_warp.py status
```

## Troubleshooting

### Common Issues

1. **Email Import Errors**:
   - Solution: Email functionality is optional and will gracefully degrade

2. **ML Dependencies Missing**:
   - Solution: `pip install scikit-learn pandas numpy`

3. **Schedule Library Missing**:
   - Solution: `pip install schedule`

4. **Environment Variables Not Set**:
   - Solution: Set required Plaid credentials

### Logs and Debugging

- Automation logs: `automation/scheduler_log.jsonl`
- Notification logs: `automation/notification_log.jsonl`
- Audit logs: `audit/audit_log.jsonl`

## Advanced Usage

### Custom ML Training
```python
# Add custom training data for expense categorization
training_data = [
    ("Your Custom Merchant", "Your Custom Category"),
    # Add more training examples
]
```

### Custom Alert Rules
```python
# Define custom alert conditions
def custom_alert_rule(transaction):
    # Your custom logic here
    return should_alert
```

### Webhook Integration
```python
# Set up webhooks for real-time processing
from automation_mcp import monitor_transactions

# Process incoming webhook data
def handle_webhook(data):
    result = monitor_transactions(data['account_key'])
    return result
```

## Integration Examples

### With Existing Plaid MCP
```python
from plaid_mcp import get_transactions
from automation_mcp import auto_categorize_expenses

# Get transactions and categorize
transactions = get_transactions("account_key")
categorization = auto_categorize_expenses("account_key", days=30)
```

### With Stripe MCP
```python
from stripe_mcp import get_payments
from automation_mcp import auto_reconcile_payments

# Reconcile Stripe payments with bank transactions
reconciliation = auto_reconcile_payments("account_key")
```

### With Xero MCP
```python
from xero_mcp import get_invoices
from automation_mcp import auto_send_payment_reminders

# Send reminders for overdue Xero invoices
reminders = auto_send_payment_reminders()
```

## Contributing

1. Follow the existing code patterns
2. Add comprehensive tests for new features
3. Update configuration schemas as needed
4. Maintain backward compatibility
5. Document all new automation tools

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review log files for error details
3. Test with simple automation first
4. Verify environment variable configuration

---

## Summary

The Financial Automation & Workflows system provides:
- Complete automation of financial processes
- ML-powered intelligence for categorization
- Real-time monitoring and alerts
- Beautiful Warp terminal integration
- Comprehensive configuration management
- Robust testing and validation

Start with the simple test, configure your settings, and gradually enable more advanced features as needed.