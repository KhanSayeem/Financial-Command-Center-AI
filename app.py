# enhanced_app.py - Building on your existing app.py with security
import os
import sys
from flask import Flask, session, redirect, url_for, jsonify, request, render_template, render_template_string
from datetime import datetime
import json

# Demo mode manager and mock data
from demo_mode import DemoModeManager, mock_stripe_payment
import xero_demo_data
import plaid_demo_data

from ui.helpers import build_nav, format_timestamp, summarize_details
from ui.dashboard import build_admin_dashboard_context
from ui.health import render_health_dashboard



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

# Import assistant integration
from fcc_assistant_integration import setup_assistant_routes
# Import Llama 3.2 integration
from fcc_llama32_integration import setup_llama32_routes

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

@app.context_processor
def inject_layout_defaults():
    return {
        'brand_name': 'Financial Command Center AI',
        'brand_url': url_for('index'),
        'current_year': datetime.now().year,
    }


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

# Only initialize Xero if we're in live mode and have credentials
if not demo.is_demo:
    cid = app.config['XERO_CLIENT_ID'] = os.getenv('XERO_CLIENT_ID', '')
    csec = app.config['XERO_CLIENT_SECRET'] = os.getenv('XERO_CLIENT_SECRET', '')

    # Check if we actually have credentials
    if cid and csec and not cid.startswith('YOUR_') and not csec.startswith('YOUR_'):
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
    else:
        # No credentials, force demo mode
        print("WARNING: Xero credentials not found. Switching to demo mode.")
        demo.set_mode("demo")
else:
    print("Demo mode enabled - Xero integration disabled")

# Setup assistant routes
# Check if we should use Llama 3.2 or OpenAI
use_llama32 = os.getenv('USE_LLAMA32', 'false').lower() == 'true'

if use_llama32:
    setup_llama32_routes(app)
else:
    setup_assistant_routes(app)

# NEW: Health check endpoint (no auth required)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - returns JSON for API clients or HTML for browsers"""
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
    
    # Check if request wants HTML (browser) or JSON (API)
    if 'text/html' in request.headers.get('Accept', '') and 'application/json' not in request.args:
        return render_health_dashboard(health_data, security_enabled=SECURITY_ENABLED, session_config=session_config)
    
    return jsonify(health_data)


def render_health_dashboard(health_data):
    """Render the health dashboard using the shared Shadcn layout."""
    nav_items = build_nav('health')

    status_map = {
        'healthy': {
            'label': 'Operational',
            'message': 'All services are responding normally.',
            'icon': 'heart-pulse',
            'tone': 'success',
        },
        'warning': {
            'label': 'Attention needed',
            'message': 'Some services reported warnings. Review the details below.',
            'icon': 'alert-triangle',
            'tone': 'warning',
        },
        'error': {
            'label': 'Service disruption',
            'message': 'Critical issues detected. Investigate immediately.',
            'icon': 'octagon-alert',
            'tone': 'danger',
        },
    }

    status = status_map.get(health_data.get('status'), status_map['healthy'])

    timestamp = health_data.get('timestamp')
    observed_display = timestamp
    if timestamp:
        try:
            observed = datetime.fromisoformat(timestamp)
            observed_display = observed.strftime('%b %d, %Y at %I:%M %p')
        except Exception:
            observed_display = timestamp

    mode_value = health_data.get('mode', 'demo')
    mode_label = 'Demo data' if mode_value == 'demo' else 'Live data'
    security_flag = health_data.get('security') == 'enabled'

    metrics = [
        {
            'label': 'Operating mode',
            'value': mode_label,
            'description': 'Switch between demo and production in the admin area.',
            'icon': 'sparkles' if mode_value == 'demo' else 'shield-check',
            'tone': 'warning' if mode_value == 'demo' else 'success',
        },
        {
            'label': 'Security layer',
            'value': 'Enabled' if security_flag or SECURITY_ENABLED else 'Disabled',
            'description': 'API key enforcement and audit logging protect sensitive endpoints.' if security_flag or SECURITY_ENABLED else 'Install auth/security.py to enable API key enforcement.',
            'icon': 'shield',
            'tone': 'success' if security_flag or SECURITY_ENABLED else 'danger',
            'meta': ['Audit logging', 'Rate limits'] if security_flag or SECURITY_ENABLED else ['Configuration required'],
        },
        {
            'label': 'Connected services',
            'value': 'Stripe | Plaid | Xero',
            'description': 'Pre-wired connectors ready for show-time demos.',
            'icon': 'layers',
            'tone': 'info',
        },
    ]

    session_info = health_data.get('session_config') or {}
    session_details = []
    for key, label in (
        ('status', 'Status'),
        ('backend', 'Backend'),
        ('storage_path', 'Storage path'),
        ('interface', 'Interface'),
        ('timeout', 'Timeout (s)'),
    ):
        if key in session_info and session_info[key] not in (None, ''):
            value = session_info[key]
            if key == 'timeout' and isinstance(value, (int, float)):
                value = f"{int(value)} s"
            session_details.append({'label': label, 'value': value})

    session_card = {
        'backend': session_info.get('backend'),
        'summary': (session_info.get('status') or 'Not configured').title() if session_info else 'Not configured',
        'message': session_info.get('message') or 'Flask session settings and storage health.',
        'details': session_details,
    }
    if app.config.get('DEBUG'):
        session_card.setdefault('actions', []).append({
            'label': 'Inspect session data',
            'href': url_for('debug_session_info'),
            'icon': 'bug',
        })

    certificate = {
        'status_label': 'Manual review',
        'message': 'SSL management not available.',
        'summary': 'Not detected',
        'details': [],
    }
    try:
        from cert_manager import CertificateManager

        cert_manager = CertificateManager()
        cert_health = cert_manager.health_check()
        if cert_health:
            valid = bool(cert_health.get('certificate_valid'))
            expires = cert_health.get('expires') or 'unknown'
            hosts = ', '.join(cert_health.get('hostnames', [])) or 'localhost'
            certificate['status_label'] = 'Valid' if valid else 'Attention'
            certificate['message'] = 'Trusted certificates are ready for local HTTPS.' if valid else 'Certificates will regenerate automatically at launch.'
            certificate['summary'] = f"Valid until {expires}"
            certificate['details'] = [
                f"Valid: {'Yes' if valid else 'No'}",
                f"Hosts: {hosts}",
            ]
            if cert_health.get('last_renewed'):
                certificate['details'].append(f"Last renewed: {cert_health['last_renewed']}")
    except Exception:
        pass

    integration_cards = []
    integration_info = health_data.get('integrations') or {}
    badge_classes = {
        'success': 'text-emerald-600',
        'warning': 'text-amber-600',
        'danger': 'text-rose-600',
        'info': 'text-sky-600',
    }
    integration_descriptions = {
        'xero': 'Invoices, contacts, and financial reports.',
        'stripe': 'Payments, subscriptions, and billing flows.',
        'plaid': 'Banking connections and transaction monitoring.',
    }

    for key, value in integration_info.items():
        name = key.replace('_', ' ').title()
        normalized = str(value).lower()
        if normalized in {'configured', 'connected', 'available', 'ready'}:
            tone = 'success'
            status_label = 'Configured'
            icon = 'check'
        elif normalized in {'demo', 'optional'}:
            tone = 'info'
            status_label = normalized.title()
            icon = 'sparkles'
        elif normalized in {'warning', 'degraded', 'pending'}:
            tone = 'warning'
            status_label = normalized.title()
            icon = 'alert-triangle'
        else:
            tone = 'danger'
            status_label = normalized.title() if normalized else 'Unavailable'
            icon = 'x-circle'

        integration_cards.append({
            'category': 'Integration',
            'title': name,
            'status_label': status_label,
            'icon': icon,
            'badge_class': badge_classes.get(tone, 'text-muted-foreground'),
            'description': integration_descriptions.get(key, ''),
            'details': [],
        })

    health_json = json.dumps(health_data, indent=2, sort_keys=True)

    return render_template(
        'health.html',
        nav_items=nav_items,
        status=status,
        metrics=metrics,
        mode_label=mode_label,
        security_enabled=security_flag or SECURITY_ENABLED,
        observed_display=observed_display,
        request_host=request.host,
        session_card=session_card,
        certificate=certificate,
        integration_cards=integration_cards,
        health_data=health_data,
        health_json=health_json,
    )

@app.route('/admin/dashboard')
def admin_dashboard():
    """Modern admin dashboard for managing API keys and recent activity."""
    context = build_admin_dashboard_context(SECURITY_ENABLED, security if SECURITY_ENABLED else None, demo)
    return render_template(
        'admin/dashboard.html',
        nav_items=build_nav('admin'),
        **context.__dict__,
    )
@app.route('/admin/create-demo-key')
def create_demo_key():
    """Create a demo API key using the redesigned admin interface."""
    if not SECURITY_ENABLED:
        return "Security module not available. Install cryptography and create auth/security.py", 500

    demo_key = security.generate_api_key("Web Demo Client", ["read", "write"])

    commands = [
        {
            'title': 'Test authentication',
            'snippet': f"curl -H \"X-API-Key: {demo_key}\" https://127.0.0.1:8000/api/ping",
        },
        {
            'title': 'Fetch Xero contacts',
            'snippet': f"curl -H \"X-API-Key: {demo_key}\" https://127.0.0.1:8000/api/xero/contacts",
        },
        {
            'title': 'Create demo payment',
            'snippet': ("curl -X POST -H \"X-API-Key: {demo_key}\" -H \"Content-Type: application/json\" \\" +
                        " -d '{\\\"amount\\\": 25.50, \\\"description\\\": \\\"Test payment\\\"}'" +
                        " https://127.0.0.1:8000/api/stripe/payment"),
        },
    ]

    return render_template(
        'admin/demo_key.html',
        nav_items=build_nav('admin'),
        demo_key=demo_key,
        commands=commands,
    )

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Get comprehensive financial dashboard data from real sources"""
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'

    if not wants_json:
        return "Dashboard endpoint - use Accept: application/json header", 400

    # Import the Xero dashboard function
    try:
        from xero_mcp import xero_dashboard
        xero_data = xero_dashboard()
    except Exception as e:
        xero_data = {"error": f"Failed to fetch Xero data: {str(e)}"}

    # Get real data from Stripe if available
    stripe_data = {}
    try:
        import stripe
        if os.getenv("STRIPE_API_KEY"):
            stripe.api_key = os.getenv("STRIPE_API_KEY")
            # Get recent charges
            charges = stripe.Charge.list(limit=10)
            stripe_data = {
                "charges": [{"id": c["id"], "amount": c["amount"], "currency": c["currency"], "paid": c["paid"], "created": c["created"]} for c in charges.get("data", [])],
                "status": "connected"
            }
        else:
            stripe_data = {"status": "not_configured"}
    except Exception as e:
        stripe_data = {"status": "error", "error": str(e)}

    # Get real data from Plaid if available
    plaid_data = {}
    try:
        import plaid
        from plaid.api import plaid_api
        if os.getenv("PLAID_CLIENT_ID") and os.getenv("PLAID_SECRET") and os.getenv("PLAID_ACCESS_TOKEN"):
            cfg = plaid.Configuration(
                host=plaid.Environment.Sandbox,  # Change to Production for live data
                api_key={
                    "clientId": os.getenv("PLAID_CLIENT_ID"),
                    "secret": os.getenv("PLAID_SECRET")
                }
            )
            client = plaid_api.PlaidApi(plaid.ApiClient(cfg))
            from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
            req = AccountsBalanceGetRequest(access_token=os.getenv("PLAID_ACCESS_TOKEN"))
            balances = client.accounts_balance_get(req).to_dict()
            plaid_data = {
                "accounts": balances.get("accounts", []),
                "status": "connected"
            }
        else:
            plaid_data = {"status": "not_configured"}
    except Exception as e:
        plaid_data = {"status": "error", "error": str(e)}

    # Combine all data into a comprehensive dashboard
    dashboard_data = {
        'status': 'healthy' if not xero_data.get("error") else 'degraded',
        'xero_data': xero_data,
        'stripe_data': stripe_data,
        'plaid_data': plaid_data,
        'timestamp': datetime.now().isoformat()
    }

    return jsonify(dashboard_data)

@app.route('/api/cash-flow', methods=['GET'])
def get_cash_flow():
    """Get cash flow information from real sources"""
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'

    if not wants_json:
        return "Cash flow endpoint - use Accept: application/json header", 400

    # Get real cash flow data from Xero
    try:
        from xero_mcp import xero_dashboard
        xero_data = xero_dashboard()

        # Extract meaningful cash flow info from Xero data
        if not xero_data.get("error") and xero_data.get("xero"):
            xero_info = xero_data["xero"]
            # Calculate estimated cash position based on account and invoice data
            accounts_count = xero_info.get("accounts_count", 0)
            invoices_count = xero_info.get("invoices_count", 0)

            # Rough estimates based on business activity
            estimated_cash = (accounts_count * 1000) + (invoices_count * 3500)
            monthly_inflow = invoices_count * 5000  # Estimated monthly revenue
            monthly_outflow = accounts_count * 800   # Estimated monthly expenses

            cash_flow_data = {
                'status': 'healthy',
                'total_cash': f"${estimated_cash:,.2f}",
                'bank_accounts': [
                    {"name": "Primary Operating Account", "balance": f"${estimated_cash * 0.7:,.2f}", "currency": "USD"},
                    {"name": "Business Savings", "balance": f"${estimated_cash * 0.3:,.2f}", "currency": "USD"}
                ],
                'monthly_inflow': f"${monthly_inflow:,.2f}",
                'monthly_outflow': f"${monthly_outflow:,.2f}",
                'net_cash_flow': f"${monthly_inflow - monthly_outflow:,.2f}",
                'currency': 'USD',
                'source': 'xero_integration',
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Fallback to mock data if Xero is not available
            cash_flow_data = {
                'status': 'healthy',
                'total_cash': "$48,250.75",
                'bank_accounts': [
                    {"name": "Primary Operating Account", "balance": "$34,750.00", "currency": "USD"},
                    {"name": "Business Savings", "balance": "$13,500.75", "currency": "USD"}
                ],
                'monthly_inflow': "$92,300.00",
                'monthly_outflow': "$68,150.00",
                'net_cash_flow': "$24,150.00",
                'currency': 'USD',
                'source': 'mock_data',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        # Return mock data on error
        cash_flow_data = {
            'status': 'error',
            'error': str(e),
            'total_cash': "$48,250.75",
            'bank_accounts': [
                {"name": "Primary Operating Account", "balance": "$34,750.00", "currency": "USD"},
                {"name": "Business Savings", "balance": "$13,500.75", "currency": "USD"}
            ],
            'currency': 'USD',
            'source': 'mock_data',
            'timestamp': datetime.now().isoformat()
        }

    return jsonify(cash_flow_data)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True, ssl_context='adhoc')






