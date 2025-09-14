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
        return render_health_dashboard(health_data)
    
    return jsonify(health_data)


def render_health_dashboard(health_data):
    """Render HTML health dashboard with clean styling"""
    banner = demo.banner_html()
    
    # Determine status colors and icons
    status_info = {
        'healthy': {'color': 'var(--success-color)', 'icon': 'fas fa-check-circle', 'text': 'System Healthy'},
        'warning': {'color': 'var(--warning-color)', 'icon': 'fas fa-exclamation-triangle', 'text': 'Minor Issues'},
        'error': {'color': 'var(--danger-color)', 'icon': 'fas fa-times-circle', 'text': 'System Error'}
    }
    
    current_status = status_info.get(health_data['status'], status_info['healthy'])
    
    # SSL Certificate status
    ssl_status = 'unknown'
    ssl_info = ''
    try:
        from cert_manager import CertificateManager
        cert_manager = CertificateManager()
        cert_health = cert_manager.health_check()
        ssl_status = 'healthy' if cert_health['certificate_valid'] else 'warning'
        ssl_info = f"Expires: {cert_health['expires']}, Valid: {'Yes' if cert_health['certificate_valid'] else 'No'}"
    except Exception:
        ssl_status = 'warning'
        ssl_info = 'SSL management not available'
    
    template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>System Health - Financial Command Center AI</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        
        <style>
            /* Root variables for consistent color scheme */
            :root {{
                --primary-color: #2563eb;
                --primary-hover: #1d4ed8;
                --secondary-color: #64748b;
                --success-color: #059669;
                --warning-color: #d97706;
                --danger-color: #dc2626;
                --text-primary: #1e293b;
                --text-secondary: #64748b;
                --bg-primary: #ffffff;
                --bg-secondary: #f8fafc;
                --border-color: #e2e8f0;
                --border-radius: 8px;
                --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            }}
            
            * {{
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: var(--bg-secondary);
                color: var(--text-primary);
                line-height: 1.6;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            .header {{
                background: {current_status['color']};
                color: white;
                padding: 2rem;
                border-radius: var(--border-radius);
                margin-bottom: 2rem;
                text-align: center;
            }}
            
            .header h1 {{
                font-size: 2rem;
                font-weight: 600;
                margin: 0 0 0.5rem 0;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.75rem;
            }}
            
            .header p {{
                margin: 0;
                opacity: 0.9;
                font-size: 1.1rem;
            }}
            
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}
            
            .stat-card {{
                background: var(--bg-primary);
                padding: 1.5rem;
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                border: 1px solid var(--border-color);
                border-left: 4px solid var(--primary-color);
            }}
            
            .stat-card.success {{
                border-left-color: var(--success-color);
            }}
            
            .stat-card.warning {{
                border-left-color: var(--warning-color);
            }}
            
            .stat-card.danger {{
                border-left-color: var(--danger-color);
            }}
            
            .stat-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 1rem;
            }}
            
            .stat-title {{
                font-size: 1.125rem;
                font-weight: 600;
                color: var(--text-primary);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            
            .stat-icon {{
                color: var(--primary-color);
                font-size: 1.25rem;
            }}
            
            .stat-status {{
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .status-healthy {{
                background: #d1fae5;
                color: #065f46;
            }}
            
            .status-warning {{
                background: #fef3c7;
                color: #92400e;
            }}
            
            .status-error {{
                background: #fee2e2;
                color: #991b1b;
            }}
            
            .stat-value {{
                font-size: 1.5rem;
                font-weight: 700;
                color: var(--text-primary);
                margin-bottom: 0.5rem;
            }}
            
            .stat-description {{
                color: var(--text-secondary);
                font-size: 0.875rem;
            }}
            
            .section {{
                background: var(--bg-primary);
                padding: 1.5rem;
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                margin-bottom: 1.5rem;
                border: 1px solid var(--border-color);
            }}
            
            .section h2 {{
                font-size: 1.25rem;
                font-weight: 600;
                margin-bottom: 1rem;
                color: var(--text-primary);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            
            .detail-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem 0;
                border-bottom: 1px solid var(--border-color);
            }}
            
            .detail-item:last-child {{
                border-bottom: none;
            }}
            
            .detail-label {{
                font-weight: 500;
                color: var(--text-primary);
            }}
            
            .detail-value {{
                color: var(--text-secondary);
                font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
                font-size: 0.875rem;
            }}
            
            .btn {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.75rem 1.5rem;
                background: var(--primary-color);
                color: white;
                text-decoration: none;
                border-radius: var(--border-radius);
                font-weight: 500;
                transition: all 0.2s ease;
                cursor: pointer;
                border: none;
                margin: 0.25rem;
                font-size: 0.875rem;
            }}
            
            .btn:hover {{
                background: var(--primary-hover);
                transform: translateY(-1px);
            }}
            
            .actions {{
                text-align: center;
                margin-top: 2rem;
                padding: 1.5rem;
                background: var(--bg-primary);
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                border: 1px solid var(--border-color);
            }}
            
            .refresh-info {{
                margin-top: 1rem;
                padding: 1rem;
                background: var(--bg-secondary);
                border-radius: var(--border-radius);
                color: var(--text-secondary);
                font-size: 0.875rem;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
            }}
        </style>
        
        <script>
            // Auto-refresh every 30 seconds
            setTimeout(() => {{
                if (document.visibilityState === 'visible') {{
                    window.location.reload();
                }}
            }}, 30000);
            
            function refreshHealth() {{
                window.location.reload();
            }}
        </script>
    </head>
    <body>
        {banner}
        <div class="container">
            <div class="header">
                <h1><i class="{current_status['icon']}"></i>{current_status['text']}</h1>
                <p>System status as of {health_data['timestamp'][:19].replace('T', ' ')}</p>
            </div>
            
            <div class="stats">
                <div class="stat-card success">
                    <div class="stat-header">
                        <div class="stat-title">
                            <i class="fas fa-server stat-icon"></i>
                            Application
                        </div>
                        <span class="stat-status status-healthy">Running</span>
                    </div>
                    <div class="stat-value">v{health_data['version']}</div>
                    <div class="stat-description">Core application is operational</div>
                </div>
                
                <div class="stat-card {'success' if health_data['security'] == 'enabled' else 'warning'}">
                    <div class="stat-header">
                        <div class="stat-title">
                            <i class="fas fa-shield-alt stat-icon"></i>
                            Security
                        </div>
                        <span class="stat-status status-{'healthy' if health_data['security'] == 'enabled' else 'warning'}">
                            {health_data['security'].title()}
                        </span>
                    </div>
                    <div class="stat-value">{health_data['security'].title()}</div>
                    <div class="stat-description">API key authentication & rate limiting</div>
                </div>
                
                <div class="stat-card {'success' if ssl_status == 'healthy' else 'warning'}">
                    <div class="stat-header">
                        <div class="stat-title">
                            <i class="fas fa-lock stat-icon"></i>
                            SSL/TLS
                        </div>
                        <span class="stat-status status-{ssl_status}">{'Secured' if ssl_status == 'healthy' else 'Check Required'}</span>
                    </div>
                    <div class="stat-value">{'HTTPS' if ssl_status == 'healthy' else 'Mixed'}</div>
                    <div class="stat-description">{ssl_info}</div>
                </div>
                
                <div class="stat-card success">
                    <div class="stat-header">
                        <div class="stat-title">
                            <i class="fas fa-database stat-icon"></i>
                            Mode
                        </div>
                        <span class="stat-status status-healthy">{health_data['mode'].title()}</span>
                    </div>
                    <div class="stat-value">{health_data['mode'].title()} Mode</div>
                    <div class="stat-description">{'Using sample data for testing' if health_data['mode'] == 'demo' else 'Connected to live services'}</div>
                </div>
            </div>
            
            <div class="section">
                <h2><i class="fas fa-puzzle-piece"></i>Integration Status</h2>
                {chr(10).join([f'<div class="detail-item"><span class="detail-label">{integration.title()}</span><span class="detail-value">{status.title()}</span></div>' for integration, status in health_data['integrations'].items()])}
            </div>
            
            <div class="section">
                <h2><i class="fas fa-info-circle"></i>System Information</h2>
                <div class="detail-item">
                    <span class="detail-label">Version</span>
                    <span class="detail-value">{health_data['version']}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Mode</span>
                    <span class="detail-value">{health_data['mode']}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Security</span>
                    <span class="detail-value">{health_data['security']}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Last Check</span>
                    <span class="detail-value">{health_data['timestamp'][:19].replace('T', ' ')}</span>
                </div>
            </div>
            
            <div class="actions">
                <h3 style="margin: 0 0 1rem 0; color: var(--text-primary);">Quick Actions</h3>
                <button onclick="refreshHealth()" class="btn"><i class="fas fa-sync-alt"></i>Refresh Status</button>
                <a href="/admin/dashboard" class="btn"><i class="fas fa-tachometer-alt"></i>Admin Dashboard</a>
                <a href="/admin/ssl-help" class="btn"><i class="fas fa-certificate"></i>SSL Setup</a>
                <a href="/" class="btn"><i class="fas fa-home"></i>Home</a>
            </div>
            
            <div class="refresh-info">
                <i class="fas fa-clock"></i>
                This page auto-refreshes every 30 seconds
            </div>
        </div>
    </body>
    </html>
    """
    
    return template

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
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Financial Command Center AI</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        
        <style>
            /* Root variables for consistent color scheme */
            :root {
                --primary-color: #2563eb;
                --primary-hover: #1d4ed8;
                --secondary-color: #64748b;
                --success-color: #059669;
                --warning-color: #d97706;
                --danger-color: #dc2626;
                --text-primary: #1e293b;
                --text-secondary: #64748b;
                --bg-primary: #ffffff;
                --bg-secondary: #f8fafc;
                --border-color: #e2e8f0;
                --border-radius: 8px;
                --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            }
            
            * {
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: var(--bg-secondary);
                color: var(--text-primary);
                line-height: 1.6;
            }
            
            .container {
                max-width: 900px;
                margin: 0 auto;
            }
            
            .header {
                background: var(--primary-color);
                color: white;
                padding: 2rem;
                border-radius: var(--border-radius);
                margin-bottom: 2rem;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2rem;
                font-weight: 600;
                margin: 0 0 0.5rem 0;
            }
            
            .header p {
                margin: 0;
                opacity: 0.9;
                font-size: 1.1rem;
            }
            
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 1.5rem;
                margin: 2rem 0;
            }
            
            .feature {
                background: var(--bg-primary);
                padding: 1.5rem;
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                border: 1px solid var(--border-color);
                border-left: 4px solid var(--primary-color);
                transition: all 0.2s ease;
            }
            
            .feature:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.15);
            }
            
            .feature h3 {
                margin: 0 0 0.75rem 0;
                font-size: 1.125rem;
                font-weight: 600;
                color: var(--text-primary);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .feature p {
                margin: 0;
                color: var(--text-secondary);
                line-height: 1.5;
            }
            
            .feature i {
                color: var(--primary-color);
                font-size: 1.25rem;
            }
            
            .actions {
                text-align: center;
                margin-top: 2rem;
                padding: 1.5rem;
                background: var(--bg-primary);
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                border: 1px solid var(--border-color);
            }
            
            .btn {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.75rem 1.5rem;
                background: var(--primary-color);
                color: white;
                text-decoration: none;
                border-radius: var(--border-radius);
                font-weight: 500;
                transition: all 0.2s ease;
                cursor: pointer;
                border: none;
                margin: 0.25rem;
                font-size: 0.875rem;
            }
            
            .btn:hover {
                background: var(--primary-hover);
                transform: translateY(-1px);
            }
            
            .btn i {
                font-size: 0.875rem;
            }
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
                    <h3><i class="fas fa-shield-alt"></i>Secure API Access</h3>
                    <p>Enterprise-grade authentication and rate limiting with comprehensive audit logging</p>
                </div>
                <div class="feature">
                    <h3><i class="fas fa-credit-card"></i>Payment Processing</h3>
                    <p>Stripe integration for secure payment handling and subscription management</p>
                </div>
                <div class="feature">
                    <h3><i class="fas fa-university"></i>Banking Data</h3>
                    <p>Plaid integration for real-time account access and transaction monitoring</p>
                </div>
                <div class="feature">
                    <h3><i class="fas fa-calculator"></i>Accounting</h3>
                    <p>Xero integration for invoices, contacts, and comprehensive financial reporting</p>
                </div>
            </div>
            
            <div class="actions">
                <h3 style="margin: 0 0 1rem 0; color: var(--text-primary);">Get Started</h3>
                <a href="/login" class="btn"><i class="fas fa-plug"></i>Connect to Xero</a>
                <a href="/admin/dashboard" class="btn"><i class="fas fa-tachometer-alt"></i>Admin Dashboard</a>
                <a href="/health" class="btn"><i class="fas fa-heartbeat"></i>Health Check</a>
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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Financial Command Center - Admin Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        
        <style>
            /* Root variables for consistent color scheme */
            :root {
                --primary-color: #2563eb;
                --primary-hover: #1d4ed8;
                --secondary-color: #64748b;
                --success-color: #059669;
                --warning-color: #d97706;
                --danger-color: #dc2626;
                --text-primary: #1e293b;
                --text-secondary: #64748b;
                --bg-primary: #ffffff;
                --bg-secondary: #f8fafc;
                --border-color: #e2e8f0;
                --border-radius: 8px;
                --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            }
            
            * {
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: var(--bg-secondary);
                color: var(--text-primary);
                line-height: 1.6;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .header {
                background: var(--primary-color);
                color: white;
                padding: 2rem;
                border-radius: var(--border-radius);
                margin-bottom: 2rem;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2rem;
                font-weight: 600;
                margin: 0 0 0.5rem 0;
            }
            
            .header p {
                margin: 0;
                opacity: 0.9;
                font-size: 1.1rem;
            }
            
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }
            
            .stat-box {
                background: var(--bg-primary);
                padding: 1.5rem;
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                border: 1px solid var(--border-color);
            }
            
            .stat-value {
                font-size: 2.5rem;
                font-weight: 700;
                color: var(--primary-color);
                margin-bottom: 0.5rem;
            }
            
            .stat-label {
                color: var(--text-secondary);
                font-weight: 500;
                font-size: 0.875rem;
            }
            
            .section {
                background: var(--bg-primary);
                padding: 1.5rem;
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                margin-bottom: 1.5rem;
                border: 1px solid var(--border-color);
            }
            
            .section h2 {
                font-size: 1.25rem;
                font-weight: 600;
                margin-bottom: 1rem;
                color: var(--text-primary);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .api-key {
                border-left: 4px solid var(--primary-color);
                padding: 1rem;
                margin: 1rem 0;
                background: var(--bg-secondary);
                border-radius: 0 var(--border-radius) var(--border-radius) 0;
            }
            
            .api-key h3 {
                margin: 0 0 0.5rem 0;
                font-size: 1rem;
                font-weight: 600;
                color: var(--text-primary);
            }
            
            .api-key p {
                margin: 0.25rem 0;
                font-size: 0.875rem;
                color: var(--text-secondary);
            }
            
            .api-key code {
                background: var(--bg-primary);
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
                font-size: 0.75rem;
                border: 1px solid var(--border-color);
            }
            
            .event {
                padding: 0.75rem;
                margin: 0.5rem 0;
                background: var(--bg-secondary);
                border-radius: var(--border-radius);
                font-size: 0.875rem;
                border: 1px solid var(--border-color);
            }
            
            .active {
                color: var(--success-color);
                font-weight: 600;
            }
            
            .inactive {
                color: var(--danger-color);
                font-weight: 600;
            }
            
            .btn {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.75rem 1.5rem;
                background: var(--primary-color);
                color: white;
                text-decoration: none;
                border-radius: var(--border-radius);
                font-weight: 500;
                transition: all 0.2s ease;
                cursor: pointer;
                border: none;
                margin: 0.25rem;
                font-size: 0.875rem;
            }
            
            .btn:hover {
                background: var(--primary-hover);
                transform: translateY(-1px);
            }
            
            .btn i {
                font-size: 0.875rem;
            }
            
            .no-data {
                text-align: center;
                padding: 2rem;
                color: var(--text-secondary);
            }
            
            .no-data i {
                font-size: 3rem;
                margin-bottom: 1rem;
                opacity: 0.5;
            }
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
                <h2><i class="fas fa-key"></i>API Keys Management</h2>
                {% if api_keys %}
                    {% for key, info in api_keys.items() %}
                    <div class="api-key">
                        <h3><i class="fas fa-user"></i>{{ info.client_name }}</h3>
                        <p><strong>API Key:</strong> <code>{{ key[:25] }}...</code></p>
                        <p><strong>Status:</strong> 
                            <span class="{{ 'active' if info.active else 'inactive' }}">
                                <i class="fas {{ 'fa-check-circle' if info.active else 'fa-times-circle' }}"></i>
                                {{ 'Active' if info.active else 'Inactive' }}
                            </span>
                        </p>
                        <p><strong>Created:</strong> <i class="fas fa-calendar"></i> {{ info.created_at }}</p>
                        <p><strong>Last Used:</strong> <i class="fas fa-clock"></i> {{ info.last_used or 'Never' }}</p>
                        <p><strong>Permissions:</strong> <i class="fas fa-shield-alt"></i> {{ ', '.join(info.permissions) }}</p>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="no-data">
                        <i class="fas fa-key"></i>
                        <p>No API keys created yet.</p>
                        <p>Create your first API key to start using the system.</p>
                    </div>
                {% endif %}
                
                <div style="margin-top: 20px;">
                    <a href="/admin/create-demo-key" class="btn"><i class="fas fa-plus"></i>Create Demo API Key</a>
                </div>
            </div>
            
            <div class="section">
                <h2><i class="fas fa-history"></i>Recent Activity</h2>
                {% if recent_events %}
                    {% for event in recent_events %}
                    <div class="event">
                        <i class="fas fa-info-circle" style="color: var(--primary-color); margin-right: 0.5rem;"></i>
                        <strong>{{ event.timestamp[:19] }}</strong> - 
                        {{ event.event_type }} by {{ event.client_name }}
                        {% if event.details %}
                        <br><small style="margin-left: 1.25rem;">{{ event.details }}</small>
                        {% endif %}
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="no-data">
                        <i class="fas fa-history"></i>
                        <p>No recent activity.</p>
                        <p>API usage and events will appear here once you start using the system.</p>
                    </div>
                {% endif %}
            </div>
            
            <div class="section">
                <h2><i class="fas fa-tools"></i>Quick Actions</h2>
                <a href="/health" class="btn"><i class="fas fa-heartbeat"></i>Health Check</a>
                <a href="/login" class="btn"><i class="fas fa-plug"></i>Connect Xero</a>
                <a href="/admin/create-demo-key" class="btn"><i class="fas fa-key"></i>Create Demo Key</a>
                <a href="/" class="btn"><i class="fas fa-home"></i>Home</a>
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
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Demo API Key Created - Financial Command Center</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        
        <style>
            /* Root variables for consistent color scheme */
            :root {{
                --primary-color: #2563eb;
                --primary-hover: #1d4ed8;
                --secondary-color: #64748b;
                --success-color: #059669;
                --warning-color: #d97706;
                --danger-color: #dc2626;
                --text-primary: #1e293b;
                --text-secondary: #64748b;
                --bg-primary: #ffffff;
                --bg-secondary: #f8fafc;
                --border-color: #e2e8f0;
                --border-radius: 8px;
                --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            }}
            
            * {{
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: var(--bg-secondary);
                color: var(--text-primary);
                line-height: 1.6;
            }}
            
            .container {{
                max-width: 900px;
                margin: 0 auto;
            }}
            
            .header {{
                background: var(--success-color);
                color: white;
                padding: 2rem;
                border-radius: var(--border-radius);
                margin-bottom: 2rem;
                text-align: center;
            }}
            
            .header h1 {{
                font-size: 2rem;
                font-weight: 600;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.75rem;
            }}
            
            .key-box {{
                background: #f0fdf4;
                padding: 1.5rem;
                border-radius: var(--border-radius);
                border: 1px solid #bbf7d0;
                margin: 1.5rem 0;
            }}
            
            .key-box h3 {{
                margin: 0 0 1rem 0;
                color: #166534;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            
            .code {{
                background: var(--bg-primary);
                padding: 1rem;
                border-radius: var(--border-radius);
                font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
                margin: 0.75rem 0;
                overflow-x: auto;
                font-size: 0.875rem;
                border: 1px solid var(--border-color);
                color: var(--text-primary);
            }}
            
            .section {{
                background: var(--bg-primary);
                padding: 1.5rem;
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                margin-bottom: 1.5rem;
                border: 1px solid var(--border-color);
            }}
            
            .section h3 {{
                margin: 0 0 1rem 0;
                color: var(--text-primary);
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            
            .section h4 {{
                margin: 1.5rem 0 0.5rem 0;
                color: var(--text-primary);
                font-weight: 600;
                font-size: 1rem;
            }}
            
            .btn {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.75rem 1.5rem;
                background: var(--primary-color);
                color: white;
                text-decoration: none;
                border-radius: var(--border-radius);
                font-weight: 500;
                transition: all 0.2s ease;
                cursor: pointer;
                border: none;
                margin: 0.25rem;
                font-size: 0.875rem;
            }}
            
            .btn:hover {{
                background: var(--primary-hover);
                transform: translateY(-1px);
            }}
            
            .alert {{
                padding: 1rem;
                border-radius: var(--border-radius);
                margin: 1rem 0;
                border: 1px solid var(--warning-color);
                background: #fffbeb;
                color: #92400e;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1><i class="fas fa-check-circle"></i>Demo API Key Created!</h1>
            </div>
            
            <div class="key-box">
                <h3><i class="fas fa-key"></i>Your New API Key:</h3>
                <div class="code">{demo_key}</div>
                <div class="alert">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>Important:</strong> Save this key securely - it won't be shown again!
                </div>
            </div>
            
            <div class="section">
                <h3><i class="fas fa-flask"></i>Test Your API Key</h3>
                
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
            </div>
            
            <div style="text-align: center; margin-top: 2rem;">
                <a href="/admin/dashboard" class="btn"><i class="fas fa-arrow-left"></i>Back to Dashboard</a>
                <a href="/login" class="btn"><i class="fas fa-plug"></i>Connect Xero First</a>
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
