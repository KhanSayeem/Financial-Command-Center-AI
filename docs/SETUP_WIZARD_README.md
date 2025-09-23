# Financial Command Center - Professional Setup Wizard

A complete professional setup wizard that replaces manual environment variable configuration with a secure, user-friendly web interface.

## Features

### Professional Setup Wizard
- **Clean, modern UI** with step-by-step configuration
- **Real-time API validation** - test connections before saving
- **Skip for Demo** options for each service
- **Progress tracking** with visual indicators
- **Responsive design** for desktop and mobile

### Enterprise Security
- **AES-256 encryption** for all stored credentials
- **Local encrypted storage** - no cloud dependencies
- **Secure key generation** with proper cryptographic standards
- **Protected file permissions** on credential storage

### Seamless Integration
- **Stripe Payment Processing** - full API validation
- **Xero Accounting Integration** - OAuth credential validation
- **Backward compatibility** with existing environment variables
- **Hot-swappable configuration** - no restart required

### Enhanced Dashboard
- **Integration status monitoring**
- **Configuration management**
- **API key management** with usage tracking
- **Health checks** with detailed service status

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements_setup_wizard.txt
```

### 2. Run the Application
```bash
# Windows: Use the one-click launcher
ultimate_cert_fix.cmd

# Mac/Linux: Run directly with Python
python app_with_setup_wizard.py
```

### 3. Complete Setup
1. Visit `https://127.0.0.1:8000/`
2. You'll be automatically redirected to the setup wizard
3. Configure Stripe and Xero (or skip for demo)
4. Test connections and save configuration
5. Start using your Financial Command Center!

## File Structure

```
Financial-Command-Center-AI/
├── app_with_setup_wizard.py      # Main application with setup wizard
├── setup_wizard.py               # Setup wizard backend logic
├── templates/
│   └── setup_wizard.html         # Professional setup wizard UI
├── secure_config/                # Auto-created encrypted config storage
│   ├── master.key                # Encryption key (keep secure!)
│   ├── config.enc                # Encrypted credentials
│   └── metadata.json             # Configuration metadata
└── requirements_setup_wizard.txt # All required dependencies
```

## Configuration Options

### Stripe Integration
- **API Key**: Your Stripe secret key (`sk_test_...` or `sk_live_...`)
- **Publishable Key**: Optional frontend key (`pk_test_...` or `pk_live_...`)
- **Real-time validation**: Tests connection and retrieves account info
- **Skip option**: Use demo mode without real Stripe integration

### Xero Integration  
- **Client ID**: From your Xero app configuration
- **Client Secret**: From your Xero app configuration
- **Format validation**: Ensures proper credential format
- **Skip option**: Use demo mode without real Xero integration

## Security Features

### Encryption
- **AES-256-GCM encryption** for credential storage
- **PBKDF2 key derivation** with secure random salts
- **Fernet encryption** (industry-standard symmetric encryption)
- **Secure key management** with protected file permissions

### Access Control
- **API key authentication** for all endpoints
- **Rate limiting** and request validation
- **Audit logging** for all configuration changes
- **Secure session management**

### Data Protection
- **Local-only storage** - no cloud dependencies
- **Encrypted at rest** - all credentials encrypted
- **Memory protection** - credentials cleared after use
- **Secure defaults** - fail-safe configuration

## API Endpoints

### Setup Wizard Endpoints
- `GET /setup` - Setup wizard interface
- `POST /api/setup/test-stripe` - Test Stripe connection
- `POST /api/setup/test-xero` - Test Xero configuration
- `POST /api/setup/save-config` - Save encrypted configuration
- `GET /api/setup/status` - Get configuration status

### Enhanced Application Endpoints
- `GET /` - Smart home page (redirects to setup if needed)
- `GET /health` - Enhanced health check with integration status
- `GET /admin/dashboard` - Configuration and monitoring dashboard
- `POST /api/stripe/payment` - Create payments (if Stripe configured)
- `GET /api/xero/contacts` - Get contacts (if Xero configured)
- `GET /login` - Xero OAuth (if configured)

## Admin Dashboard

The enhanced admin dashboard provides:

### Integration Status
- **Real-time service status** for all configured integrations
- **Configuration validation** with detailed error reporting  
- **Demo mode indicators** for skipped services
- **Connection health monitoring**

### Security Management
- **API key creation** and management
- **Usage statistics** and audit trails
- **Access control** and permission management
- **Security event logging**

### Quick Actions
- **Reconfigure services** via setup wizard
- **Test connections** and validate configurations
- **Create demo API keys** for testing
- **System health checks**

## Migration from Environment Variables

The setup wizard is fully backward compatible:

### Automatic Detection
- Checks for existing `STRIPE_API_KEY`, `XERO_CLIENT_ID`, etc.
- Uses environment variables if present
- Falls back to setup wizard if not configured

### Smooth Transition
1. **Keep existing setup**: Environment variables take precedence
2. **Migrate gradually**: Use setup wizard for new services
3. **Full migration**: Remove env vars to use encrypted storage
4. **Rollback option**: Environment variables always override

## 🧪 Development and Testing

### Test Configuration Manager
```bash
python setup_wizard.py
```

### Create Demo Configuration
```bash
# Run the setup wizard and use "Skip for Demo" options
# This creates a demo configuration for development
```

### API Testing
```bash
# Get health status
curl https://127.0.0.1:8000/health

# Test setup status
curl https://127.0.0.1:8000/api/setup/status

# Create demo API key (via web interface)
# Visit: https://127.0.0.1:8000/admin/create-demo-key
```

## Security Best Practices

### Credential Management
- **Never commit** the `secure_config/` directory to version control
- **Backup encryption key** securely (separate from config files)
- **Rotate credentials** regularly through the setup wizard
- **Monitor access** through the admin dashboard

### Production Deployment
- **Use HTTPS only** (setup wizard enforces SSL)
- **Secure file permissions** on config directory
- **Regular security audits** through admin dashboard
- **Environment isolation** between development and production

### Access Control
- **Generate unique API keys** for each client/application
- **Monitor API usage** through the dashboard
- **Revoke unused keys** regularly
- **Use role-based permissions** for API access

## Use Cases

### Financial Service Providers
- **Client onboarding**: Easy setup wizard for new integrations
- **Multi-tenant support**: Separate configurations per client
- **Compliance**: Encrypted credential storage and audit trails

### E-commerce Platforms
- **Payment processing**: Secure Stripe integration with testing
- **Accounting sync**: Automatic Xero integration for invoices
- **Demo environments**: Skip services for testing environments

### Development Teams
- **Rapid setup**: No manual environment configuration
- **Team collaboration**: Shared encrypted configurations
- **Testing workflows**: Demo mode for development

## Troubleshooting

### Setup Wizard Issues
- **Can't access setup wizard**: Check if `https://127.0.0.1:8000/setup` is accessible
- **API validation fails**: Verify credentials in your Stripe/Xero dashboards
- **Encryption errors**: Ensure `cryptography` package is installed correctly

### Configuration Problems
- **Credentials not loading**: Check `secure_config/` directory permissions
- **Services not available**: Verify configuration through `/health` endpoint  
- **Dashboard access**: Ensure security module is properly installed

### Common Solutions
```bash
# Reinstall crypto dependencies
pip install --force-reinstall cryptography

# Reset configuration (WARNING: Deletes all stored credentials)
rm -rf secure_config/

# Check health status
curl -k https://127.0.0.1:8000/health
```

## Support

### Getting Help
- **Health Check**: Visit `/health` for system status
- **Admin Dashboard**: Visit `/admin/dashboard` for detailed monitoring
- **Setup Wizard**: Visit `/setup` to reconfigure at any time

### Development
- **Test endpoints**: Use the `/health` endpoint to verify integration status
- **Debug mode**: Check console output for detailed error messages
- **API testing**: Use the admin dashboard to create test API keys

---

## Congratulations!

Your Financial Command Center now has a professional setup wizard that eliminates manual configuration and provides enterprise-grade security for credential management. The setup wizard makes onboarding new users effortless while maintaining the highest security standards.

**Next Steps:**
1. Configure your integrations through the setup wizard
2. Explore the enhanced admin dashboard  
3. Test API endpoints with automatically generated keys
4. Enjoy seamless financial operations!
