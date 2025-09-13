# enhanced_app.py - Building on your existing app.py with security
import os
import sys
from flask import Flask, session, redirect, url_for, jsonify, request, render_template_string
from datetime import datetime
import json

# Demo mode manager and mock data
from demo_mode import DemoModeManager, mock_stripe_payment
import xero_demo_data
import plaid_demo_data

# Xero imports (optional when in live mode)
try:
    from xero_oauth import init_oauth
    from xero_python.accounting import AccountingApi
    from xero_python.api_client import ApiClient, Configuration
    from xero_python.api_client.oauth2 import OAuth2Token
    from xero_python.exceptions import AccountingBadRequestException
    from xero_python.identity import IdentityApi
    from xero_python.api_client import serialize
    XERO_SDK_AVAILABLE = True
except Exception:
    XERO_SDK_AVAILABLE = False
from xero_client import save_token_and_tenant

# Import enhanced session configuration
from session_config import configure_flask_sessions

# Add our security layer
sys.path.append('.')
try:
    from auth.security import SecurityManager, require_api_key, log_transaction
    SECURITY_ENABLED = True
except ImportError:
    print("WARNING: Security module not found. Running without API key authentication.")
    print("   Create auth/security.py to enable security features.")
    SECURITY_ENABLED = False
    
    # Create dummy decorators if security not available
    def require_api_key(f):
        def wrapper(*args, **kwargs):
            # Add dummy client info for compatibility
            request.client_info = {'client_name': 'No Auth'}
            request.api_key = 'no-auth'
            return f(*args, **kwargs)
        return wrapper
    
    def log_transaction(operation, amount, currency, status):
        print(f"Transaction: {operation} - {amount} {currency} - {status}")

app = Flask(__name__)

# Initialize demo mode management (adds /api/mode and /admin/mode, and banner helpers)
demo = DemoModeManager(app)

# Enhanced session configuration will be set up after Xero client initialization
app.config['XERO_CLIENT_ID'] = os.getenv('XERO_CLIENT_ID', 'YOUR_CLIENT_ID')     
app.config['XERO_CLIENT_SECRET'] = os.getenv('XERO_CLIENT_SECRET', 'YOUR_CLIENT_SECRET')

# Initialize security manager if available
if SECURITY_ENABLED:
    security = SecurityManager()

# Xero setup (demo-safe)
api_client = None
oauth = None
xero = None
session_config = None  # Enhanced session configuration
REDIRECT_URI = "https://127.0.0.1:8000/callback"

if not demo.is_demo:
    cid = app.config['XERO_CLIENT_ID'] = os.getenv('XERO_CLIENT_ID', '')
    csec = app.config['XERO_CLIENT_SECRET'] = os.getenv('XERO_CLIENT_SECRET', '')

    if not cid or cid.startswith('YOUR_'):
        raise RuntimeError("XERO_CLIENT_ID not set. Export env var before running, or enable demo mode.")
    if not csec or csec.startswith('YOUR_'):
        raise RuntimeError("XERO_CLIENT_SECRET not set. Export env var before running, or enable demo mode.")

    if not XERO_SDK_AVAILABLE:
        raise RuntimeError("Xero SDK not available. Install dependencies or enable demo mode.")

    api_client = ApiClient(Configuration(
        oauth2_token=OAuth2Token(
            client_id=app.config['XERO_CLIENT_ID'],
            client_secret=app.config['XERO_CLIENT_SECRET'],
        )
    ))

    # Configure enhanced session management with OAuth token handlers
    session_config = configure_flask_sessions(app, api_client)
    oauth, xero = init_oauth(app)

# NEW: Health check endpoint (no auth required)
@app.route('/health', methods=['GET'])
def health_check():
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'mode': 'demo' if 'demo' in demo.get_mode() else 'live',
        'security': 'enabled' if SECURITY_ENABLED else 'disabled',
        'integrations': {
            'xero': 'configured',
            'stripe': 'available', 
            'plaid': 'available'
        }
    }
    
    # Add session health if available
    if session_config:
        health_data['session_config'] = session_config.health_check()
    
    return jsonify(health_data)

# NEW: API key management (if security enabled)
if SECURITY_ENABLED:
    @app.route('/api/create-key', methods=['POST'])
    def create_api_key():
        """Create a new API key for a client"""
        data = request.get_json() or {}
        
        client_name = data.get('client_name')
        if not client_name:
            return jsonify({'error': 'client_name required'}), 400
        
        permissions = data.get('permissions', ['read', 'write'])
        api_key = security.generate_api_key(client_name, permissions)
        
        return jsonify({
            'success': True,
            'api_key': api_key,
            'client_name': client_name,
            'permissions': permissions,
            'created_at': datetime.now().isoformat()
        })

    @app.route('/api/key-stats', methods=['GET'])
    @require_api_key
    def get_key_stats():
        """Get usage statistics for the current API key"""
        stats = security.get_client_stats(request.api_key)
        return jsonify(stats)

    @app.route('/api/ping', methods=['GET'])
    @require_api_key
    def secure_ping():
        """Test endpoint that requires authentication"""
        return jsonify({
            'message': 'pong',
            'client': request.client_info['client_name'],
            'timestamp': datetime.now().isoformat(),
            'permissions': request.client_info['permissions']
        })

# Your existing routes (preserved)
@app.route('/')
def index():
    banner = demo.banner_html()
    return banner + """
    <html>
    <head>
        <title>Financial Command Center AI</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f5f7fa; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 40px; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0; }
            .feature { background: #f8f9ff; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; }
            .btn { background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
            .btn:hover { background: #5a6fd8; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Financial Command Center AI</h1>
                <p>Unified Financial Operations Platform</p>
            </div>
            
            <div class="features">
                <div class="feature">
                    <h3>Secure API Access</h3>
                    <p>Enterprise-grade authentication and rate limiting</p>
                </div>
                <div class="feature">
                    <h3>Payment Processing</h3>
                    <p>Stripe integration for secure payment handling</p>
                </div>
                <div class="feature">
                    <h3>Banking Data</h3>
                    <p>Plaid integration for real-time account access</p>
                </div>
                <div class="feature">
                    <h3>Accounting</h3>
                    <p>Xero integration for invoices and contacts</p>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px;">
                <a href="/login" class="btn">Connect to Xero</a>
                <a href="/admin/dashboard" class="btn">Admin Dashboard</a>
                <a href="/health" class="btn">Health Check</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/login')
def login():
    """Xero login (disabled in demo mode)."""
    if 'demo' in demo.get_mode():
        banner = demo.banner_html()
        return f"""
        <html><body style='font-family:Segoe UI,Arial,sans-serif;'>
        {banner}
        <div style='max-width:720px;margin:40px auto;background:white;padding:30px;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,0.08)'>
            <h2>Xero Connection (Demo)</h2>
            <p>You are in demo mode. This experience uses sample Xero data for contacts and invoices.</p>
            <p>To connect your real Xero organisation, switch to <strong>Live</strong> mode.</p>
            <div style='margin-top:18px;'>
              <a href='/admin/mode' style='background:#667eea;color:white;padding:10px 14px;border-radius:6px;text-decoration:none;'>Upgrade to Real Data</a>
              <a href='/' style='margin-left:8px;'>Back</a>
            </div>
        </div>
        </body></html>
        """
    return xero.authorize_redirect(redirect_uri=REDIRECT_URI)

@app.route('/callback')
def callback():
    """Your existing Xero callback - enhanced with logging"""
    if demo.is_demo:
        return "Demo mode active. OAuth callback not applicable.", 400
    try:
        token = xero.authorize_access_token()
        allowed = {
            "access_token", "refresh_token", "token_type",
            "expires_in", "expires_at", "scope", "id_token"
        }
        token = {k: v for k, v in token.items() if k in allowed}
        session['token'] = token
        session.modified = True
        
        if not token:
            return "Authorization failed", 400

        # Your existing logic
        from xero_python.identity import IdentityApi
        identity = IdentityApi(api_client)
        conns = identity.get_connections()
        if not conns:
            return "No Xero organisations available for this user.", 400

        session['tenant_id'] = conns[0].tenant_id
        save_token_and_tenant(token, session['tenant_id'])
        
        # Enhanced: Log the successful connection
        if SECURITY_ENABLED:
            security.log_security_event("xero_oauth_success", "web_user", {
                "tenant_id": session['tenant_id'],
                "timestamp": datetime.now().isoformat()
            })
        
        return redirect(url_for('profile'))
    except Exception as e:
        return f"Authorization failed: {str(e)}", 400

@app.route('/profile')
def profile():
    """Your existing profile route - enhanced with better formatting"""
    if demo.is_demo:
        banner = demo.banner_html()
        return f"""
        <html>
        <head><title>Xero Profile (Demo)</title></head>
        <body style=\"font-family:Segoe UI,Arial,sans-serif;\">{banner}
        <div style=\"max-width: 800px; margin: 40px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.08);\">
          <h2>Xero (Demo)</h2>
          <p>This is a demo profile view. API endpoints return sample invoices and contacts.</p>
          <div style=\"margin-top:16px;\">
            <a href=\"/admin/mode\" style=\"background:#667eea;color:white;padding:10px 14px;border-radius:6px;text-decoration:none;\">Upgrade to Real Data</a>
            <a href=\"/\" style=\"margin-left:10px;\">Back</a>
          </div>
        </div>
        </body></html>
        """
    if 'token' not in session:
        return redirect(url_for('login'))
    if 'tenant_id' not in session:
        return "No tenant selected.", 400

    try:
        accounting = AccountingApi(api_client)
        accounts = accounting.get_accounts(session['tenant_id'])
        
        # Enhanced response with HTML
        return f"""
        <html>
        <head>
            <title>Xero Profile - Financial Command Center</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f5f7fa; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }}
                .account {{ background: #f8f9ff; padding: 15px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #667eea; }}
                .btn {{ background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; margin: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Connected to Xero!</h1>
                <p><strong>Tenant ID:</strong> {session['tenant_id']}</p>
                <p><strong>Total Accounts:</strong> {len(accounts.accounts)}</p>
                
                <h3>First 5 Accounts:</h3>
                {''.join([f'<div class="account">{account.name}</div>' for account in accounts.accounts[:5]])}
                
                <div style="margin-top: 30px;">
                    <a href="/api/xero/contacts" class="btn">View API Contacts</a>
                    <a href="/api/xero/invoices" class="btn">View API Invoices</a>
                    <a href="/admin/dashboard" class="btn">Admin Dashboard</a>
                    <a href="/logout" class="btn">Logout</a>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"Error fetching profile: {str(e)}", 500

@app.route('/logout')
def logout():
    """Your existing logout"""
    session.pop('token', None)
    session.pop('tenant_id', None)
    return redirect(url_for('index'))

# ENHANCED: Your Xero endpoints with API security
@app.route('/api/xero/contacts', methods=['GET'])
@require_api_key
def get_xero_contacts():
    """Get Xero contacts with security (demo-safe)."""
    if demo.is_demo:
        data = xero_demo_data.CONTACTS
        log_transaction('xero_contacts_access_demo', len(data), 'items', 'success')
        return jsonify({'success': True, 'mode': 'demo', 'contacts': data, 'count': len(data), 'client': request.client_info['client_name']})

    if not session.get("token"):
        return jsonify({'error': 'Xero not authenticated', 'auth_url': url_for('login', _external=True)}), 401

    try:
        accounting_api = AccountingApi(api_client)
        contacts = accounting_api.get_contacts(xero_tenant_id=session.get('tenant_id'))
        log_transaction('xero_contacts_access', len(contacts.contacts), 'items', 'success')
        contacts_data = []
        for contact in contacts.contacts:
            contacts_data.append({
                'contact_id': contact.contact_id,
                'name': contact.name,
                'email': contact.email_address,
                'status': contact.contact_status.value if contact.contact_status else None,
                'is_supplier': contact.is_supplier,
                'is_customer': contact.is_customer
            })
        return jsonify({'success': True, 'mode': 'live', 'contacts': contacts_data, 'count': len(contacts_data)})
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/xero/invoices', methods=['GET'])
@require_api_key
def get_xero_invoices():
    """Get Xero invoices with security (demo-safe)."""
    # Filters
    status_filter = request.args.get('status', 'DRAFT,SUBMITTED,AUTHORISED')
    limit = min(int(request.args.get('limit', 50)), 100)

    if demo.is_demo:
        all_inv = [inv for inv in xero_demo_data.INVOICES if inv.get('status') in status_filter.split(',')]
        invoices_data = all_inv[:limit]
        log_transaction('xero_invoices_access_demo', len(invoices_data), 'items', 'success')
        return jsonify({'success': True, 'mode': 'demo', 'invoices': invoices_data, 'count': len(invoices_data), 'total_available': len(all_inv), 'filters': {'status': status_filter, 'limit': limit}})

    if not session.get("token"):
        return jsonify({'error': 'Xero not authenticated', 'auth_url': url_for('login', _external=True)}), 401

    try:
        accounting_api = AccountingApi(api_client)
        invoices = accounting_api.get_invoices(xero_tenant_id=session.get('tenant_id'), statuses=status_filter.split(','))
        log_transaction('xero_invoices_access', len(invoices.invoices), 'items', 'success')
        invoices_data = []
        for i, invoice in enumerate(invoices.invoices):
            if i >= limit:
                break
            invoices_data.append({
                'invoice_id': invoice.invoice_id,
                'invoice_number': invoice.invoice_number,
                'type': invoice.type.value if invoice.type else None,
                'status': invoice.status.value if invoice.status else None,
                'total': float(invoice.total) if invoice.total else 0,
                'currency_code': invoice.currency_code.value if invoice.currency_code else 'USD',
                'date': invoice.date.isoformat() if invoice.date else None,
                'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
                'contact_name': invoice.contact.name if invoice.contact else None
            })
        return jsonify({'success': True, 'mode': 'live', 'invoices': invoices_data, 'count': len(invoices_data), 'total_available': len(invoices.invoices)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# NEW: Xero report (Profit & Loss)
@app.route('/api/xero/report/profit-and-loss', methods=['GET'])
@require_api_key
def xero_profit_and_loss():
    """Return a simple Profit & Loss report (demo-safe)."""
    try:
        if demo.is_demo:
            log_transaction('xero_report_pl_demo', 1, 'report', 'success')
            return jsonify({'success': True, 'mode': 'demo', 'report': xero_demo_data.PROFIT_AND_LOSS})
        return jsonify({'error': 'Report not implemented for live mode in this app'}), 501
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# NEW: Stripe integration endpoints
@app.route('/api/stripe/payment', methods=['POST'])
@require_api_key
def create_stripe_payment():
    """Create Stripe payment with security (demo-safe)."""
    try:
        data = request.get_json()
        if not data or 'amount' not in data:
            return jsonify({'error': 'amount required'}), 400
        
        amount_dollars = float(data['amount'])
        amount_cents = int(amount_dollars * 100)
        currency = data.get('currency', 'usd')
        description = data.get('description', f'Payment via {request.client_info["client_name"]}')
        
        # Log transaction attempt
        log_transaction('stripe_payment_create', amount_dollars, currency, 'initiated')

        if demo.is_demo:
            fake = mock_stripe_payment(amount_dollars, currency, description)
            log_transaction('stripe_payment_create_demo', amount_dollars, currency, 'succeeded')
            return jsonify(fake)

        # Live mode
        stripe_key = os.getenv('STRIPE_API_KEY')
        if not stripe_key:
            return jsonify({'error': 'Stripe not configured', 'message': 'Set STRIPE_API_KEY or enable demo mode'}), 500

        import stripe
        stripe.api_key = stripe_key

        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            description=description,
            automatic_payment_methods={'enabled': True}
        )

        log_transaction('stripe_payment_create', amount_dollars, currency, 'created')
        return jsonify({'success': True, 'payment_intent_id': payment_intent.id, 'client_secret': payment_intent.client_secret, 'amount': amount_dollars, 'currency': currency, 'status': payment_intent.status, 'client': request.client_info['client_name']})
        
    except Exception as e:
        log_transaction('stripe_payment_create', 
                       data.get('amount', 0) if 'data' in locals() else 0, 
                       data.get('currency', 'usd') if 'data' in locals() else 'usd', 
                       'failed')
        return jsonify({'error': str(e)}), 500

# NEW: Plaid integration (demo/live)
@app.route('/api/plaid/accounts', methods=['GET'])
@require_api_key
def get_plaid_accounts():
    """Get Plaid accounts (demo-safe)."""
    try:
        if demo.is_demo:
            accounts = plaid_demo_data.ACCOUNTS
            log_transaction('plaid_accounts_access_demo', len(accounts), 'accounts', 'success')
            return jsonify({'success': True, 'mode': 'demo', 'accounts': accounts, 'count': len(accounts), 'client': request.client_info['client_name']})
        return jsonify({'error': 'Plaid live mode not configured', 'message': 'Use demo mode or integrate plaid_mcp.py'}), 501
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plaid/transactions', methods=['GET'])
@require_api_key
def get_plaid_transactions():
    """Get Plaid transactions (demo-safe)."""
    try:
        if demo.is_demo:
            txns = plaid_demo_data.TRANSACTIONS
            log_transaction('plaid_transactions_access_demo', len(txns), 'transactions', 'success')
            return jsonify({'success': True, 'mode': 'demo', 'transactions': txns, 'count': len(txns), 'client': request.client_info['client_name']})
        return jsonify({'error': 'Plaid live mode not configured', 'message': 'Use demo mode or integrate plaid_mcp.py'}), 501
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# NEW: Admin dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard for managing API keys and monitoring"""
    
    if not SECURITY_ENABLED:
        return """
        <html>
        <body style="font-family: Arial; margin: 40px;">
            <h1>WARNING: Security Module Not Available</h1>
            <p>To enable the admin dashboard and API key management:</p>
            <ol>
                <li>Create the <code>auth/security.py</code> file</li>
                <li>Install: <code>pip install cryptography</code></li>
                <li>Restart the application</li>
            </ol>
            <p><a href="/">← Back to Home</a></p>
        </body>
        </html>
        """
    
    # Load current API keys and audit events
    api_keys = security._load_json(security.auth_file)
    audit_log = security._load_json(security.audit_file)
    recent_events = audit_log.get('events', [])[-10:]  # Last 10 events
    
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Financial Command Center - Admin Dashboard</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-box { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .stat-value { font-size: 2.5em; font-weight: bold; color: #667eea; }
            .stat-label { color: #666; margin-top: 10px; }
            .section { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .api-key { border-left: 4px solid #667eea; padding: 15px; margin: 10px 0; background: #f8f9ff; }
            .event { padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 5px; font-size: 0.9em; }
            .active { color: #27ae60; }
            .inactive { color: #e74c3c; }
            .btn { background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
            .btn:hover { background: #5a6fd8; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Financial Command Center AI</h1>
                <p>Admin Dashboard - API Key Management & Monitoring</p>
            </div>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{{ total_keys }}</div>
                    <div class="stat-label">Total API Keys</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value active">{{ active_keys }}</div>
                    <div class="stat-label">Active Keys</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{{ unique_clients }}</div>
                    <div class="stat-label">Unique Clients</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{{ recent_events|length }}</div>
                    <div class="stat-label">Recent Events</div>
                </div>
            </div>
            
            <div class="section">
                <h2>API Keys Management</h2>
                {% if api_keys %}
                    {% for key, info in api_keys.items() %}
                    <div class="api-key">
                        <h3>{{ info.client_name }}</h3>
                        <p><strong>API Key:</strong> <code>{{ key[:25] }}...</code></p>
                        <p><strong>Status:</strong> 
                            <span class="{{ 'active' if info.active else 'inactive' }}">
                                {{ 'Active' if info.active else 'Inactive' }}
                            </span>
                        </p>
                        <p><strong>Created:</strong> {{ info.created_at }}</p>
                        <p><strong>Last Used:</strong> {{ info.last_used or 'Never' }}</p>
                        <p><strong>Permissions:</strong> {{ ', '.join(info.permissions) }}</p>
                    </div>
                    {% endfor %}
                {% else %}
                    <p>No API keys created yet.</p>
                {% endif %}
                
                <div style="margin-top: 20px;">
                    <a href="/admin/create-demo-key" class="btn">Create Demo API Key</a>
                </div>
            </div>
            
            <div class="section">
                <h2>Recent Activity</h2>
                {% if recent_events %}
                    {% for event in recent_events %}
                    <div class="event">
                        <strong>{{ event.timestamp[:19] }}</strong> - 
                        {{ event.event_type }} by {{ event.client_name }}
                        {% if event.details %}
                        <br><small>{{ event.details }}</small>
                        {% endif %}
                    </div>
                    {% endfor %}
                {% else %}
                    <p>No recent activity.</p>
                {% endif %}
            </div>
            
            <div class="section">
                <h2>Quick Actions</h2>
                <a href="/health" class="btn">Health Check</a>
                <a href="/login" class="btn">Connect Xero</a>
                <a href="/admin/create-demo-key" class="btn">Create Demo Key</a>
                <a href="/" class="btn">Home</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Calculate stats
    total_keys = len(api_keys)
    active_keys = sum(1 for info in api_keys.values() if info.get('active', False))
    unique_clients = len(set(info['client_name'] for info in api_keys.values())) if api_keys else 0
    
    return demo.banner_html() + render_template_string(dashboard_html,
                                api_keys=api_keys,
                                total_keys=total_keys,
                                active_keys=active_keys,
                                unique_clients=unique_clients,
                                recent_events=recent_events)

@app.route('/admin/create-demo-key')
def create_demo_key():
    """Create demo API key via web interface"""
    if not SECURITY_ENABLED:
        return "Security module not available. Install cryptography and create auth/security.py", 500
    
    demo_key = security.generate_api_key("Web Demo Client", ["read", "write"])
    
    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f5f7fa; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }}
            .key-box {{ background: #e8f5e8; padding: 20px; border-radius: 8px; border: 1px solid #c3e6cb; margin: 20px 0; }}
            .code {{ background: #f8f9fa; padding: 15px; border-radius: 5px; font-family: 'Courier New', monospace; margin: 10px 0; overflow-x: auto; font-size: 14px; }}
            .btn {{ background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Demo API Key Created!</h1>
            
            <div class="key-box">
                <h3>Your New API Key:</h3>
                <div class="code">{demo_key}</div>
                <p><strong>Important:</strong> Save this key securely - it won't be shown again!</p>
            </div>
            
            <h3>Test Your API Key:</h3>
            
            <h4>1. Test Authentication:</h4>
            <div class="code">
curl -H "X-API-Key: {demo_key}" https://127.0.0.1:8000/api/ping
            </div>
            
            <h4>2. Get Xero Contacts (after connecting Xero):</h4>
            <div class="code">
curl -H "X-API-Key: {demo_key}" https://127.0.0.1:8000/api/xero/contacts
            </div>
            
            <h4>3. Create Stripe Payment:</h4>
            <div class="code">
curl -X POST -H "X-API-Key: {demo_key}" -H "Content-Type: application/json" \\
  -d '{{"amount": 25.50, "description": "Test payment"}}' \\
  https://127.0.0.1:8000/api/stripe/payment
            </div>
            
            <h4>4. Check Usage Stats:</h4>
            <div class="code">
curl -H "X-API-Key: {demo_key}" https://127.0.0.1:8000/api/key-stats
            </div>
            
            <div style="margin-top: 30px;">
                <a href="/admin/dashboard" class="btn">← Back to Dashboard</a>
                <a href="/login" class="btn">Connect Xero First</a>
            </div>
        </div>
    </body>
    </html>
    """

# Error handlers
@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'error': 'Unauthorized',
        'message': 'Valid API key required',
        'code': 'AUTH_REQUIRED'
    }), 401

@app.errorhandler(429)
def rate_limited(error):
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.',
        'code': 'RATE_LIMIT_EXCEEDED'
    }), 429

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred',
        'code': 'INTERNAL_ERROR'
    }), 500

if __name__ == '__main__':
    print("Starting Enhanced Financial Command Center...")
    print("=" * 60)
    print(f"Security: {'Enabled' if SECURITY_ENABLED else 'Disabled (install auth/security.py)'}")
    
    # Initialize SSL certificate management
    try:
        from cert_manager import CertificateManager
        from server_modes import configure_server_mode
        
        cert_manager = CertificateManager()
        ssl_context = None
        server_mode = "HTTPS"
        
        # Configure server mode management
        configure_server_mode(app)
        
        # Check SSL mode preference
        force_https = os.getenv('FORCE_HTTPS', 'true').lower() == 'true'
        allow_http = os.getenv('ALLOW_HTTP', 'false').lower() == 'true'
        
        if force_https or not allow_http:
            # HTTPS mode - generate certificates if needed
            print("HTTPS Mode - Ensuring SSL certificates...")
            cert_generated = cert_manager.ensure_certificates()
            ssl_context = cert_manager.get_ssl_context()
            
            if cert_generated:
                print("New SSL certificates generated!")
                print("To eliminate browser warnings, install the CA certificate:")
                print(f"   python cert_manager.py --bundle")
        else:
            # HTTP mode with warnings
            server_mode = "HTTP (with HTTPS upgrade prompts)"
            print("WARNING: HTTP Mode - Running without SSL encryption")
            print("   Set FORCE_HTTPS=true for production use")
    
    except ImportError as e:
        print("WARNING: SSL Certificate Manager not available - using Flask's adhoc SSL")
        print(f"   Install missing dependencies: {e}")
        ssl_context = 'adhoc'
    
    print("Available endpoints:")
    print("  GET  / - Enhanced home page")
    print("  GET  /health - System health check")
    print("  GET  /api/mode - Get current mode")
    print("  POST /api/mode - Set mode (demo|live)")
    print("  GET  /admin/mode - Mode toggle UI")
    print("  GET  /login - Xero OAuth login (your existing)")
    print("  GET  /callback - Xero OAuth callback (your existing)")
    print("  GET  /profile - Xero profile (your existing)")
    print("  GET  /logout - Xero logout (your existing)")
    
    if SECURITY_ENABLED:
        print("  Security Endpoints:")
        print("    POST /api/create-key - Create API key")
        print("    GET  /api/ping - Test authentication")
        print("    GET  /api/key-stats - Usage statistics")
    
    print("  Enhanced Xero API:")
    print("    GET  /api/xero/contacts - Get contacts (with auth)")
    print("    GET  /api/xero/invoices - Get invoices (with auth)")
    
    print("  Stripe Integration:")
    print("    POST /api/stripe/payment - Create payment")
    
    print("  Plaid Integration:")
    print("    GET  /api/plaid/accounts - Get accounts (demo)")
    
    print("  Admin Interface:")
    print("    GET  /admin/dashboard - Admin dashboard")
    print("    GET  /admin/create-demo-key - Create demo key")
    print("    GET  /admin/ssl-help - SSL setup guide")
    print("    GET  /admin/certificate-bundle - Download certificate bundle")
    
    print()
    protocol = "https" if ssl_context else "http"
    port = int(os.getenv('FCC_PORT') or os.getenv('PORT') or '8000')
    print("URLs:")
    print(f"  Home: {protocol}://127.0.0.1:{port}/")
    print(f"  Admin: {protocol}://127.0.0.1:{port}/admin/dashboard")
    print(f"  Health: {protocol}://127.0.0.1:{port}/health")
    print(f"  SSL Help: {protocol}://127.0.0.1:{port}/admin/ssl-help")
    print()
    
    if not SECURITY_ENABLED:
        print("WARNING: To enable security features:")
        print("   1. Create auth/security.py (copy from setup)")
        print("   2. pip install cryptography")
        print("   3. Restart application")
        print()
    
    print(f"Server Mode: {server_mode}")
    if ssl_context:
        print("SSL Certificate Status:")
        try:
            health = cert_manager.health_check()
            print(f"   Certificate Valid: {health['certificate_valid']}")
            print(f"   Expires: {health['expires']}")
            print(f"   Hostnames: {', '.join(health['hostnames'])}")
            if not health['certificate_valid']:
                print("   Certificates will be regenerated automatically")
        except Exception as e:
            print(f"   WARNING: Certificate check failed: {e}")
    
    print()
    print("Ready for client demonstrations!")
    
    # Start the Flask application
    if ssl_context:
        app.run(host='127.0.0.1', port=port, debug=True, ssl_context=ssl_context)
    else:
        # HTTP mode
        app.run(host='127.0.0.1', port=port, debug=True)
# Ensure stdout can print Unicode on Windows consoles
try:
    import io as _io
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    if getattr(sys.stdout, 'encoding', '').lower() != 'utf-8' and hasattr(sys.stdout, 'buffer'):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if getattr(sys.stderr, 'encoding', '').lower() != 'utf-8' and hasattr(sys.stderr, 'buffer'):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass
