"""
Enhanced Financial Command Center with Professional Setup Wizard
Replaces environment variable configuration with secure setup wizard
"""

import os
import sys
from flask import Flask, session, redirect, url_for, jsonify, request, render_template, send_from_directory
try:
    from flask_cors import CORS
except ImportError:
    CORS = None
from datetime import datetime
import json
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Import setup wizard functionality
from setup_wizard import SetupWizardAPI, get_configured_credentials, is_setup_required, get_integration_status

# Import enhanced session configuration
from session_config import configure_flask_sessions

# Your existing Xero imports
from xero_oauth import init_oauth
from xero_python.accounting import AccountingApi
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.exceptions import AccountingBadRequestException
from xero_python.identity import IdentityApi
from xero_python.api_client import serialize
from xero_client import save_token_and_tenant

# Add our security layer
sys.path.append('.')
try:
    from auth.security import SecurityManager, require_api_key, log_transaction
    SECURITY_ENABLED = True
except ImportError:
    print("⚠️  Security module not found. Running without API key authentication.")
    SECURITY_ENABLED = False
    
    # Create dummy decorators if security not available
    def require_api_key(f):
        def wrapper(*args, **kwargs):
            request.client_info = {'client_name': 'No Auth'}
            request.api_key = 'no-auth'
            return f(*args, **kwargs)
        return wrapper
    
    def log_transaction(operation, amount, currency, status):
        print(f"📊 Transaction: {operation} - {amount} {currency} - {status}")

app = Flask(__name__)

# Enable debug mode for session debugging
app.config['DEBUG'] = True

# Initialize enhanced session configuration
# This will be properly configured after we set up the Xero client

# Initialize setup wizard API
setup_wizard_api = SetupWizardAPI()

# Enable CORS for setup API routes to support cross-origin wizard usage (e.g., file:// or different host)
if CORS is not None:
    # Allow any origin for the narrow setup API surface only
    CORS(app, resources={r"/api/setup/*": {"origins": "*"}}, supports_credentials=False)

# Initialize security manager if available
if SECURITY_ENABLED:
    security = SecurityManager()

# Import and setup Claude Desktop integration
try:
    from claude_integration import setup_claude_routes
    claude_setup_result = setup_claude_routes(app, logger)
    print("✅ Claude Desktop integration loaded")
except ImportError as e:
    print(f"⚠️ Claude integration not available: {e}")
except Exception as e:
    print(f"⚠️ Claude integration setup failed: {e}")

def get_credentials_or_redirect():
    """Get credentials from setup wizard or redirect to setup if not configured"""
    credentials = get_configured_credentials()
    
    # Override with environment variables if they exist (for backward compatibility)
    env_stripe_key = os.getenv('STRIPE_API_KEY')
    env_xero_client_id = os.getenv('XERO_CLIENT_ID')
    env_xero_client_secret = os.getenv('XERO_CLIENT_SECRET')
    
    if env_stripe_key:
        credentials['STRIPE_API_KEY'] = env_stripe_key
    if env_xero_client_id:
        credentials['XERO_CLIENT_ID'] = env_xero_client_id
    if env_xero_client_secret:
        credentials['XERO_CLIENT_SECRET'] = env_xero_client_secret
    
    return credentials

def initialize_xero_client():
    """Initialize Xero API client with configured credentials"""
    credentials = get_credentials_or_redirect()
    
    xero_client_id = credentials.get('XERO_CLIENT_ID')
    xero_client_secret = credentials.get('XERO_CLIENT_SECRET')
    
    if not xero_client_id or not xero_client_secret:
        return None
        
    # Set app config for Xero
    app.config['XERO_CLIENT_ID'] = xero_client_id
    app.config['XERO_CLIENT_SECRET'] = xero_client_secret
    
    # Initialize API client
    api_client = ApiClient(Configuration(
        oauth2_token=OAuth2Token(
            client_id=xero_client_id,
            client_secret=xero_client_secret,
        )
    ))
    
    # Configure enhanced session management with OAuth token handlers
    session_config = configure_flask_sessions(app, api_client)
    
    return api_client

# Try to initialize Xero (will be None if not configured)
api_client = initialize_xero_client()
session_config = None  # Will be set if Xero is available

if api_client:
    try:
        oauth, xero = init_oauth(app)
        # Configure enhanced session management now that we have the API client
        session_config = configure_flask_sessions(app, api_client)
        XERO_AVAILABLE = True
        print("✅ Xero and enhanced session management initialized")
    except Exception as e:
        XERO_AVAILABLE = False
        print(f"⚠️ Xero initialization failed - configuration needed: {e}")
else:
    XERO_AVAILABLE = False
    # Still configure basic session management even without Xero
    session_config = configure_flask_sessions(app)
    print("⚠️ Xero not configured - setup wizard required")

# Routes

@app.route('/')
def index():
    """Enhanced home page that checks setup status"""
    if is_setup_required() and not (os.getenv('XERO_CLIENT_ID') and os.getenv('STRIPE_API_KEY')):
        return redirect(url_for('setup_wizard'))
    
    integration_status = get_integration_status()
    
    xero_buttons = ''
    if integration_status.get('xero', {}).get('configured'):
        xero_buttons = """
            <a href="/xero/contacts" class="btn">📋 View Contacts</a>
            <a href="/xero/invoices" class="btn">🧾 View Invoices</a>
        """
    else:
        xero_buttons = """
            <a href="/xero/contacts" class="btn">📋 View Contacts</a>
            <a href="/xero/invoices" class="btn">🧾 View Invoices</a>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Financial Command Center AI</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f5f7fa; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .header h1 {{ color: #333; margin-bottom: 10px; }}
            .setup-banner {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 30px; text-align: center; }}
            .features {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin: 30px 0; }}
            .feature {{ background: #f8f9ff; padding: 25px; border-radius: 8px; border-left: 4px solid #667eea; }}
            .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0; }}
            .status-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #ddd; }}
            .status-card.configured {{ border-left-color: #27ae60; background: #d4edda; }}
            .status-card.skipped {{ border-left-color: #f39c12; background: #fff3cd; }}
            .status-card.not-configured {{ border-left-color: #e74c3c; background: #f8d7da; }}
            .btn {{ background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }}
            .btn:hover {{ background: #5a6fd8; }}
            .btn-setup {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏦 Financial Command Center AI</h1>
                <p>Professional Financial Operations Platform</p>
            </div>
            
            <div class="setup-banner">
                <h3>🚀 Professional Setup Complete</h3>
                <p>Your Financial Command Center is configured and ready to use!</p>
                <a href="/setup" class="btn" style="background: rgba(255,255,255,0.2); border: 2px solid white;">⚙️ Reconfigure Settings</a>
            </div>
            
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.1);">
                <h3 style="margin: 0 0 15px 0; font-size: 1.5rem;">AI-Powered Financial Operations</h3>
                <p style="margin-bottom: 20px; opacity: 0.9;">Connect Claude Desktop to manage your finances with natural language commands</p>
                <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">
                    <a href="/claude/setup" class="btn" style="background: rgba(255,255,255,0.15); border: 2px solid rgba(255,255,255,0.3); backdrop-filter: blur(10px); font-weight: 600; padding: 12px 24px;">🛠️ Setup Claude Desktop</a>
                    <div style="background: rgba(255,255,255,0.1); padding: 8px 16px; border-radius: 20px; font-size: 0.9em; border: 1px solid rgba(255,255,255,0.2);">Try: "Show me our cash flow this month"</div>
                </div>
            </div>
            
            <h3>📊 Integration Status</h3>
            <div class="status-grid">
                <div class="status-card {'configured' if integration_status.get('stripe', {}).get('configured') else 'skipped' if integration_status.get('stripe', {}).get('skipped') else 'not-configured'}">
                    <h4>💳 Stripe Integration</h4>
                    <p>Status: {'✅ Configured' if integration_status.get('stripe', {}).get('configured') else '⏭️ Skipped (Demo)' if integration_status.get('stripe', {}).get('skipped') else '❌ Not Configured'}</p>
                </div>
                
                <div class="status-card {'configured' if integration_status.get('xero', {}).get('configured') else 'skipped' if integration_status.get('xero', {}).get('skipped') else 'not-configured'}">
                    <h4>📊 Xero Integration</h4>
                    <p>Status: {'✅ Configured' if integration_status.get('xero', {}).get('configured') else '⏭️ Skipped (Demo)' if integration_status.get('xero', {}).get('skipped') else '❌ Not Configured'}</p>
                </div>
            </div>
            
            <div class="features">
                <div class="feature">
                    <h3>🔐 Secure Configuration</h3>
                    <p>All credentials encrypted with AES-256 and stored locally</p>
                </div>
                <div class="feature">
                    <h3>💳 Payment Processing</h3>
                    <p>Stripe integration for secure payment handling and subscriptions</p>
                </div>
                <div class="feature">
                    <h3>📊 Accounting Sync</h3>
                    <p>Xero integration for invoices, contacts, and financial data</p>
                </div>
                <div class="feature">
                    <h3>🔄 Demo Mode</h3>
                    <p>Skip services for demo purposes - configure anytime later</p>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px;">
                <a href="/claude/setup" class="btn" style="background: #2563eb; font-size: 1.1em; padding: 16px 32px;">Connect to Claude Desktop</a><br><br>
                {xero_buttons}
                <a href="/admin/dashboard" class="btn">📊 Admin Dashboard</a>
                <a href="/health" class="btn">💓 Health Check</a>
                <a href="/setup" class="btn btn-setup">⚙️ Configuration</a>
            </div>
        </div>
    </body>
    </html>
    """

# Setup Wizard Routes

@app.route('/setup')
def setup_wizard():
    """Setup wizard main page"""
    return send_from_directory('templates', 'setup_wizard.html')

@app.route('/api/setup/test-stripe', methods=['POST'])
def test_stripe_api():
    """Test Stripe API connection"""
    data = request.get_json()
    result = setup_wizard_api.test_stripe_connection(data)
    return jsonify(result)

@app.route('/api/setup/test-xero', methods=['POST'])
def test_xero_api():
    """Test Xero OAuth configuration"""
    data = request.get_json()
    result = setup_wizard_api.test_xero_connection(data)
    return jsonify(result)

@app.route('/api/setup/save-config', methods=['POST'])
def save_setup_config():
    """Save setup wizard configuration"""
    data = request.get_json()
    result = setup_wizard_api.save_configuration(data)
    
    if result['success']:
        # Reinitialize the application with new configuration
        global api_client, XERO_AVAILABLE, oauth, xero, session_config
        api_client = initialize_xero_client()
        if api_client:
            try:
                oauth, xero = init_oauth(app)
                # Reinitialize enhanced session management with new API client
                session_config = configure_flask_sessions(app, api_client)
                XERO_AVAILABLE = True
            except:
                XERO_AVAILABLE = False
    
    return jsonify(result)

@app.route('/api/setup/status', methods=['GET'])
def get_setup_status():
    """Get current setup status"""
    result = setup_wizard_api.get_configuration_status()
    return jsonify(result)

# Session Debugging Endpoints (for troubleshooting)

@app.route('/api/session/debug', methods=['GET'])
def debug_session_info():
    """Debug session information (development only)"""
    if not app.config.get('DEBUG', False):
        return jsonify({'error': 'Debug endpoints only available in development mode'}), 403
    
    from flask import session
    session_data = dict(session) if session else {}
    
    # Don't expose sensitive data
    safe_session = {}
    for k, v in session_data.items():
        if 'token' in k.lower() or 'secret' in k.lower():
            safe_session[k] = {'type': type(v).__name__, 'length': len(str(v)) if v else 0, 'present': bool(v)}
        else:
            safe_session[k] = v
    
    session_health = session_config.health_check() if session_config else {'status': 'not_configured'}
    
    return jsonify({
        'session_data': safe_session,
        'session_health': session_health,
        'session_permanent': session.permanent if session else False,
        'flask_config': {
            'SECRET_KEY_LENGTH': len(app.config.get('SECRET_KEY', '')),
            'SESSION_PERMANENT': app.config.get('SESSION_PERMANENT'),
            'SESSION_COOKIE_SECURE': app.config.get('SESSION_COOKIE_SECURE'),
            'SESSION_COOKIE_HTTPONLY': app.config.get('SESSION_COOKIE_HTTPONLY'),
            'PERMANENT_SESSION_LIFETIME': str(app.config.get('PERMANENT_SESSION_LIFETIME')),
        }
    })

@app.route('/api/session/test-persistence', methods=['POST'])
def test_session_persistence():
    """Test session persistence by storing and retrieving a test value"""
    if not app.config.get('DEBUG', False):
        return jsonify({'error': 'Debug endpoints only available in development mode'}), 403
    
    from flask import session
    import time
    
    # Store a test value with timestamp
    test_data = {
        'timestamp': time.time(),
        'test_value': f'session_test_{int(time.time())}'
    }
    
    session.permanent = True
    session['debug_test'] = test_data
    session.modified = True
    
    return jsonify({
        'success': True,
        'test_data_stored': test_data,
        'session_id': session.get('_id', 'no_id'),
        'instructions': 'Call GET /api/session/test-persistence to verify persistence'
    })

@app.route('/api/session/test-persistence', methods=['GET'])
def check_session_persistence():
    """Check if the test session data persisted"""
    if not app.config.get('DEBUG', False):
        return jsonify({'error': 'Debug endpoints only available in development mode'}), 403
    
    from flask import session
    import time
    
    test_data = session.get('debug_test')
    current_time = time.time()
    
    if test_data:
        age_seconds = current_time - test_data['timestamp']
        return jsonify({
            'persistence_test': 'PASSED',
            'test_data': test_data,
            'age_seconds': age_seconds,
            'session_healthy': True
        })
    else:
        return jsonify({
            'persistence_test': 'FAILED',
            'message': 'No test data found in session',
            'session_data_keys': list(session.keys()) if session else [],
            'session_healthy': False
        })

@app.route('/api/oauth/test-flow', methods=['GET'])
def test_oauth_flow():
    """Test OAuth flow and configuration (debug only)"""
    if not app.config.get('DEBUG', False):
        return jsonify({'error': 'Debug endpoints only available in development mode'}), 403
    
    from flask import session
    
    # Test OAuth configuration
    oauth_config = {
        'xero_available': XERO_AVAILABLE,
        'api_client_configured': api_client is not None,
        'oauth_configured': oauth is not None,
        'xero_configured': xero is not None,
        'session_config_available': session_config is not None,
    }
    
    # Test session token handling
    current_token = session.get('token')
    current_tenant = session.get('tenant_id')
    
    token_info = {
        'has_token': current_token is not None,
        'token_type': type(current_token).__name__ if current_token else None,
        'token_keys': list(current_token.keys()) if isinstance(current_token, dict) else [],
        'has_tenant_id': current_tenant is not None,
        'tenant_id': current_tenant
    }
    
    return jsonify({
        'oauth_config': oauth_config,
        'token_info': token_info,
        'flask_config': {
            'XERO_CLIENT_ID_SET': bool(app.config.get('XERO_CLIENT_ID')),
            'XERO_CLIENT_SECRET_SET': bool(app.config.get('XERO_CLIENT_SECRET')),
        },
        'instructions': 'Use /login to start OAuth flow, then check this endpoint again'
    })

# Health Check

@app.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check with integration status"""
    # Check if request wants JSON (API) or HTML (web UI)
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'
    
    credentials = get_credentials_or_redirect()
    integration_status = get_integration_status()
    
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '3.0.0',
        'security': 'enabled' if SECURITY_ENABLED else 'disabled',
        'setup_wizard': 'enabled',
        'integrations': {
            'stripe': {
                'available': bool(credentials.get('STRIPE_API_KEY')),
                'configured': integration_status.get('stripe', {}).get('configured', False),
                'skipped': integration_status.get('stripe', {}).get('skipped', False)
            },
            'xero': {
                'available': bool(credentials.get('XERO_CLIENT_ID')),
                'configured': integration_status.get('xero', {}).get('configured', False),
                'skipped': integration_status.get('xero', {}).get('skipped', False)
            }
        },
        'credentials_source': 'setup_wizard' if not os.getenv('STRIPE_API_KEY') else 'mixed'
    }
    
    # Add session configuration health if available
    if session_config:
        health_data['session_config'] = session_config.health_check()
    
    # Return JSON for API requests
    if wants_json:
        return jsonify(health_data)
    
    # Return beautiful web UI for browser requests
    return render_health_ui(health_data)

def render_health_ui(health_data):
    """Render beautiful web UI for health check"""
    # Calculate overall health score
    total_checks = 0
    passed_checks = 0
    
    # Check integrations
    for integration, data in health_data['integrations'].items():
        total_checks += 1
        if data['configured'] or data['skipped']:
            passed_checks += 1
    
    # Check session config
    if health_data.get('session_config'):
        session_checks = health_data['session_config']['checks']
        total_checks += len(session_checks)
        passed_checks += sum(session_checks.values())
    
    # Security check
    total_checks += 1
    if health_data['security'] == 'enabled':
        passed_checks += 1
    
    health_percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 100
    overall_status = 'excellent' if health_percentage >= 90 else 'good' if health_percentage >= 70 else 'warning'
    
    # Session info
    session_info = health_data.get('session_config', {})
    session_status = session_info.get('status', 'unknown')
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>System Health - Financial Command Center</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            :root {{
                --primary-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%);
                --success-gradient: linear-gradient(135deg, #10b981 0%, #059669 100%);
                --warning-gradient: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                --error-gradient: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                --glass-bg: rgba(255, 255, 255, 0.08);
                --glass-border: rgba(255, 255, 255, 0.2);
                --text-primary: #1f2937;
                --text-secondary: #6b7280;
                --shadow-light: rgba(0, 0, 0, 0.05);
                --shadow-medium: rgba(0, 0, 0, 0.1);
                --shadow-heavy: rgba(0, 0, 0, 0.25);
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{ 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                margin: 0; 
                padding: 0;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 25%, #334155 50%, #475569 75%, #64748b 100%);
                min-height: 100vh;
                color: var(--text-primary);
                overflow-x: hidden;
                position: relative;
            }}
            
            body::before {{
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: 
                    radial-gradient(circle at 25% 25%, rgba(99, 102, 241, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 75% 75%, rgba(139, 92, 246, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 50% 50%, rgba(217, 70, 239, 0.05) 0%, transparent 50%);
                pointer-events: none;
                z-index: 0;
            }}
            
            .container {{ 
                max-width: 1400px; 
                margin: 0 auto; 
                padding: 20px;
                position: relative;
                z-index: 1;
            }}
            
            .header-section {{
                background: var(--glass-bg);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid var(--glass-border);
                border-radius: 24px;
                padding: 40px;
                text-align: center;
                position: relative;
                margin-bottom: 32px;
                overflow: hidden;
            }}
            
            .header-section::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: var(--primary-gradient);
            }}
            
            .header-section.excellent {{
                border-color: rgba(16, 185, 129, 0.3);
            }}
            
            .header-section.excellent::before {{
                background: var(--success-gradient);
            }}
            
            .header-section.good {{
                border-color: rgba(245, 158, 11, 0.3);
            }}
            
            .header-section.good::before {{
                background: var(--warning-gradient);
            }}
            
            .header-section.warning {{
                border-color: rgba(239, 68, 68, 0.3);
            }}
            
            .header-section.warning::before {{
                background: var(--error-gradient);
            }}
            
            .status-indicator {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                padding: 12px 24px;
                border-radius: 50px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                margin-bottom: 24px;
                font-size: 0.9em;
                font-weight: 600;
                color: white;
            }}
            
            .header h1 {{ 
                font-size: clamp(2rem, 4vw, 3.5rem);
                font-weight: 700;
                background: var(--primary-gradient);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 16px;
                line-height: 1.2;
            }}
            
            .header p {{ 
                font-size: 1.1em;
                color: rgba(255, 255, 255, 0.8);
                margin-bottom: 8px;
                font-weight: 400;
            }}
            .health-score {{
                position: absolute;
                top: 24px;
                right: 24px;
                background: var(--glass-bg);
                backdrop-filter: blur(10px);
                border: 1px solid var(--glass-border);
                border-radius: 50px;
                padding: 12px 20px;
                font-size: 1.1em;
                font-weight: 600;
                color: white;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .content {{ 
                padding: 0;
            }}
            
            .status-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 24px;
                margin-bottom: 32px;
            }}
            
            .status-card {{
                background: var(--glass-bg);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid var(--glass-border);
                border-radius: 20px;
                padding: 32px;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }}
            
            .status-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: var(--glass-border);
                transition: all 0.3s ease;
            }}
            
            .status-card:hover {{
                transform: translateY(-8px) scale(1.02);
                border-color: rgba(255, 255, 255, 0.3);
                box-shadow: 
                    0 20px 40px rgba(0, 0, 0, 0.2),
                    0 0 80px rgba(99, 102, 241, 0.1);
            }}
            
            .status-card.healthy::before {{
                background: var(--success-gradient);
            }}
            
            .status-card.healthy:hover {{
                box-shadow: 
                    0 20px 40px rgba(0, 0, 0, 0.2),
                    0 0 80px rgba(16, 185, 129, 0.2);
            }}
            
            .status-card.warning::before {{
                background: var(--warning-gradient);
            }}
            
            .status-card.warning:hover {{
                box-shadow: 
                    0 20px 40px rgba(0, 0, 0, 0.2),
                    0 0 80px rgba(245, 158, 11, 0.2);
            }}
            
            .status-card.error::before {{
                background: var(--error-gradient);
            }}
            
            .status-card.error:hover {{
                box-shadow: 
                    0 20px 40px rgba(0, 0, 0, 0.2),
                    0 0 80px rgba(239, 68, 68, 0.2);
            }}
            .status-icon {{
                position: absolute;
                top: 24px;
                right: 24px;
                font-size: 2.5em;
                opacity: 0.6;
                filter: grayscale(1);
                transition: all 0.3s ease;
            }}
            
            .status-card:hover .status-icon {{
                opacity: 1;
                filter: grayscale(0);
                transform: scale(1.1) rotate(5deg);
            }}
            
            .card-title {{
                font-size: 1.4em;
                font-weight: 600;
                margin-bottom: 16px;
                color: white;
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            
            .card-content {{
                color: rgba(255, 255, 255, 0.8);
                line-height: 1.8;
                font-size: 0.95em;
            }}
            
            .status-badge {{
                display: inline-flex;
                align-items: center;
                padding: 6px 14px;
                border-radius: 50px;
                font-size: 0.8em;
                font-weight: 600;
                margin: 4px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: all 0.2s ease;
            }}
            
            .status-badge:hover {{
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            }}
            
            .badge-success {{ 
                background: rgba(16, 185, 129, 0.2); 
                color: #10b981; 
                border-color: rgba(16, 185, 129, 0.3);
            }}
            
            .badge-warning {{ 
                background: rgba(245, 158, 11, 0.2); 
                color: #f59e0b; 
                border-color: rgba(245, 158, 11, 0.3);
            }}
            
            .badge-danger {{ 
                background: rgba(239, 68, 68, 0.2); 
                color: #ef4444; 
                border-color: rgba(239, 68, 68, 0.3);
            }}
            
            .badge-info {{ 
                background: rgba(99, 102, 241, 0.2); 
                color: #6366f1; 
                border-color: rgba(99, 102, 241, 0.3);
            }}
            
            .metrics {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 24px;
                margin-top: 40px;
            }}
            
            .metric-card {{
                background: var(--glass-bg);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid var(--glass-border);
                border-radius: 20px;
                padding: 28px;
                text-align: center;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }}
            
            .metric-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: var(--primary-gradient);
                transform: translateX(-100%);
                transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            
            .metric-card:hover {{
                transform: translateY(-4px);
                border-color: rgba(255, 255, 255, 0.3);
                box-shadow: 
                    0 12px 24px rgba(0, 0, 0, 0.15),
                    0 0 40px rgba(99, 102, 241, 0.1);
            }}
            
            .metric-card:hover::before {{
                transform: translateX(0);
            }}
            
            .metric-number {{
                font-size: 2.2em;
                font-weight: 700;
                background: var(--primary-gradient);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 8px;
                line-height: 1;
            }}
            
            .metric-label {{
                color: rgba(255, 255, 255, 0.7);
                font-size: 0.85em;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 1.2px;
            }}
            .nav-buttons {{
                text-align: center;
                padding: 40px 0;
                margin-top: 40px;
            }}
            
            .btn {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 14px 28px;
                margin: 8px;
                background: var(--glass-bg);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid var(--glass-border);
                color: white;
                text-decoration: none;
                border-radius: 50px;
                font-weight: 500;
                font-size: 0.9em;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }}
            
            .btn::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: var(--primary-gradient);
                transition: left 0.5s ease;
                z-index: -1;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                border-color: rgba(255, 255, 255, 0.4);
                box-shadow: 
                    0 8px 25px rgba(0, 0, 0, 0.2),
                    0 0 40px rgba(99, 102, 241, 0.3);
            }}
            
            .btn:hover::before {{
                left: 0;
            }}
            
            .btn.secondary {{
                background: rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.1);
            }}
            
            .btn.secondary::before {{
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
            }}
            
            .btn.secondary:hover {{
                box-shadow: 
                    0 8px 25px rgba(0, 0, 0, 0.15),
                    0 0 30px rgba(255, 255, 255, 0.1);
            }}
            
            .auto-refresh {{
                position: fixed;
                top: 24px;
                right: 24px;
                background: var(--glass-bg);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid var(--glass-border);
                color: white;
                padding: 8px 14px;
                border-radius: 50px;
                font-size: 0.75em;
                font-weight: 500;
                z-index: 9999;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                cursor: pointer;
                user-select: none;
                display: flex;
                align-items: center;
                gap: 4px;
            }}
            
            .auto-refresh:hover {{
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
                box-shadow: 
                    0 8px 25px rgba(0, 0, 0, 0.3),
                    0 0 40px rgba(99, 102, 241, 0.2);
            }}
            
            @media (max-width: 1200px) {{
                .status-grid {{
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                }}
                .metrics {{
                    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                }}
            }}
            
            @media (max-width: 768px) {{
                .container {{
                    padding: 16px;
                }}
                
                .header-section {{
                    padding: 32px 24px;
                }}
                
                .status-grid {{ 
                    grid-template-columns: 1fr; 
                    gap: 20px;
                }}
                
                .status-card {{
                    padding: 24px;
                }}
                
                .metrics {{ 
                    grid-template-columns: repeat(2, 1fr);
                    gap: 16px;
                }}
                
                .metric-card {{
                    padding: 20px;
                }}
                
                .header h1 {{ 
                    font-size: clamp(1.8rem, 6vw, 2.5rem);
                }}
                
                .health-score {{ 
                    position: static; 
                    margin: 20px auto 0 auto;
                    display: inline-flex;
                }}
                
                .auto-refresh {{
                    top: 16px;
                    right: 16px;
                    padding: 6px 12px;
                    font-size: 0.7em;
                }}
                
                .btn {{
                    padding: 12px 20px;
                    font-size: 0.85em;
                    margin: 6px;
                }}
            }}
            
            @media (max-width: 480px) {{
                .header h1 {{
                    font-size: 1.8rem;
                }}
                
                .metrics {{
                    grid-template-columns: 1fr;
                }}
                
                .nav-buttons .btn {{
                    display: block;
                    margin: 8px auto;
                    max-width: 200px;
                }}
            }}
            
            @keyframes spin {{
                from {{ transform: rotate(0deg); }}
                to {{ transform: rotate(360deg); }}
            }}
            
            /* Improve text contrast and visibility */
            .card-title {{
                color: rgba(255, 255, 255, 0.95);
                font-weight: 600;
                font-size: 1.1em;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
            }}
            
            .description {{
                color: rgba(255, 255, 255, 0.8);
                font-weight: 400;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            }}
            
            .status-badge {{
                font-weight: 600;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
            }}
        </style>
    </head>
    <body>
        <div class="auto-refresh" id="autoRefresh" onclick="refreshPage()" title="Click to refresh now">
            <svg width="14" height="14" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
            </svg>
            <span>Auto-refresh: 30s</span>
        </div>
        
        <div class="container">
            <div class="header {overall_status}">
                <div class="health-score">{health_percentage:.0f}% Healthy</div>
                <h1>
                    <svg width="28" height="28" fill="currentColor" viewBox="0 0 20 20" style="vertical-align: middle; margin-right: 8px;">
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    System Health Dashboard
                </h1>
                <p>Financial Command Center AI - Version {health_data['version']}</p>
                <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="content">
                <div class="status-grid">
                    <!-- System Overview -->
                    <div class="status-card {'healthy' if overall_status == 'excellent' else 'warning' if overall_status == 'good' else 'error'}">
                        <div class="status-icon">
                            <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M3 5a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2h-2.22l.123.489.804.804A1 1 0 0113 18H7a1 1 0 01-.707-1.707l.804-.804L7.22 15H5a2 2 0 01-2-2V5zm5.771 7H5V5h10v7H8.771z" clip-rule="evenodd"/>
                            </svg>
                        </div>
                        <div class="card-title">System Overview</div>
                        <div class="card-content">
                            <span class="status-badge {'badge-success' if health_data['status'] == 'healthy' else 'badge-danger'}">Status: {health_data['status'].title()}</span><br>
                            <span class="status-badge badge-info">Security: {health_data['security'].title()}</span><br>
                            <span class="status-badge badge-info">Setup Wizard: {health_data['setup_wizard'].title()}</span>
                        </div>
                    </div>
                    
                    <!-- Stripe Integration -->
                    <div class="status-card {'healthy' if health_data['integrations']['stripe']['configured'] or health_data['integrations']['stripe']['skipped'] else 'warning'}">
                        <div class="status-icon">
                            <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4zm0 2h12v2H4V6zm0 4h12v4H4v-4z" clip-rule="evenodd"/>
                            </svg>
                        </div>
                        <div class="card-title">Stripe Integration</div>
                        <div class="card-content">
                            {'<span class="status-badge badge-success">Configured</span>' if health_data['integrations']['stripe']['configured'] else '<span class="status-badge badge-warning">Skipped (Demo)</span>' if health_data['integrations']['stripe']['skipped'] else '<span class="status-badge badge-danger">Not Configured</span>'}<br>
                            Available: {'Yes' if health_data['integrations']['stripe']['available'] else 'No'}
                        </div>
                    </div>
                    
                    <!-- Xero Integration -->
                    <div class="status-card {'healthy' if health_data['integrations']['xero']['configured'] or health_data['integrations']['xero']['skipped'] else 'warning'}">
                        <div class="status-icon">
                            <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
                            </svg>
                        </div>
                        <div class="card-title">Xero Integration</div>
                        <div class="card-content">
                            {'<span class="status-badge badge-success">Configured</span>' if health_data['integrations']['xero']['configured'] else '<span class="status-badge badge-warning">Skipped (Demo)</span>' if health_data['integrations']['xero']['skipped'] else '<span class="status-badge badge-danger">Not Configured</span>'}<br>
                            Available: {'Yes' if health_data['integrations']['xero']['available'] else 'No'}
                        </div>
                    </div>
                    
                    <!-- Session Management -->
                    <div class="status-card {'healthy' if session_status == 'healthy' else 'warning'}">
                        <div class="status-icon">
                            <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/>
                            </svg>
                        </div>
                        <div class="card-title">Session Management</div>
                        <div class="card-content">
                            <span class="status-badge {'badge-success' if session_status == 'healthy' else 'badge-warning'}">Status: {session_status.title()}</span><br>
                            {'Lifetime: ' + str(session_info.get('session_lifetime', 'N/A')) if session_info else 'Not configured'}<br>
                            {'Config: ' + str(session_info.get('config_directory', 'N/A')) if session_info else ''}
                        </div>
                    </div>
                </div>
                
                <div class="metrics">
                    <div class="metric-card">
                        <div class="metric-number">{health_percentage:.0f}%</div>
                        <div class="metric-label">Health Score</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-number">{passed_checks}/{total_checks}</div>
                        <div class="metric-label">Checks Passed</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-number">
                            <svg width="32" height="32" fill="{'#10b981' if health_data['security'] == 'enabled' else '#f59e0b'}" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                            </svg>
                        </div>
                        <div class="metric-label">Security</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-number">v{health_data['version']}</div>
                        <div class="metric-label">Version</div>
                    </div>
                </div>
            </div>
            
            <div class="nav-buttons">
                <a href="/claude/setup" class="btn btn-primary">
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
                    </svg>
                    Connect to Claude Desktop
                </a>
                <a href="/" class="btn">
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"/>
                    </svg>
                    Home
                </a>
                <a href="/admin/dashboard" class="btn">
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z"/><path d="M12 2.252A8.014 8.014 0 0117.748 8H12V2.252z"/>
                    </svg>
                    Admin Dashboard
                </a>
                <a href="/setup" class="btn secondary">
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd"/>
                    </svg>
                    Setup
                </a>
                <a href="/health?format=json" class="btn secondary">
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h4a1 1 0 010 2H6.414l2.293 2.293a1 1 0 01-1.414 1.414L5 6.414V8a1 1 0 01-2 0V4zm9 1a1 1 0 010-2h4a1 1 0 011 1v4a1 1 0 01-2 0V6.414l-2.293 2.293a1 1 0 11-1.414-1.414L13.586 5H12zm-9 7a1 1 0 012 0v1.586l2.293-2.293a1 1 0 111.414 1.414L6.414 15H8a1 1 0 010 2H4a1 1 0 01-1-1v-4zm13-1a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 010-2h1.586l-2.293-2.293a1 1 0 111.414-1.414L15 13.586V12a1 1 0 011-1z" clip-rule="evenodd"/>
                    </svg>
                    JSON API
                </a>
            </div>
        </div>
        
        <script>
            let refreshCountdown = 30;
            let countdownInterval;
            
            function updateCountdown() {{
                const refreshElement = document.getElementById('autoRefresh');
                if (refreshElement) {{
                    refreshElement.innerHTML = `
                        <svg width="14" height="14" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
                        </svg>
                        <span>Auto-refresh: ${{refreshCountdown}}s</span>
                    `;
                    if (refreshCountdown <= 0) {{
                        refreshPage();
                    }} else {{
                        refreshCountdown--;
                    }}
                }}
            }}
            
            function refreshPage() {{
                const refreshElement = document.getElementById('autoRefresh');
                if (refreshElement) {{
                    refreshElement.innerHTML = `
                        <svg width="14" height="14" fill="currentColor" viewBox="0 0 20 20" style="animation: spin 1s linear infinite;">
                            <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
                        </svg>
                        <span>Refreshing...</span>
                    `;
                    refreshElement.style.background = 'rgba(40, 167, 69, 0.9)'; // Green background
                }}
                setTimeout(() => {{
                    window.location.reload();
                }}, 500);
            }}
            
            function startCountdown() {{
                refreshCountdown = 30;
                countdownInterval = setInterval(updateCountdown, 1000);
            }}
            
            // Start the countdown when page loads
            document.addEventListener('DOMContentLoaded', function() {{
                startCountdown();
            }});
            
            // Add keyboard shortcut (Ctrl+R or F5 equivalent)
            document.addEventListener('keydown', function(e) {{
                if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {{
                    e.preventDefault();
                    refreshPage();
                }}
            }});
        </script>
    </body>
    </html>
    """

# Xero Routes (only if configured)

@app.route('/login')
def login():
    """Xero OAuth login - only if configured"""
    if not XERO_AVAILABLE:
        return jsonify({
            'error': 'Xero not configured',
            'message': 'Complete setup wizard first',
            'setup_url': url_for('setup_wizard', _external=True)
        }), 400
    return xero.authorize_redirect(redirect_uri="https://localhost:8000/callback")

@app.route('/callback')
def callback():
    """Xero OAuth callback with enhanced error handling"""
    if not XERO_AVAILABLE:
        return "Xero not configured. Complete setup wizard first.", 400
        
    try:
        # Get the authorization token
        token = xero.authorize_access_token()
        
        # Enhanced validation and logging
        if not token:
            logger.error("OAuth authorization returned None token")
            return "Authorization failed: No token received", 400
        
        if not isinstance(token, dict):
            logger.error(f"OAuth token is not a dict: {type(token)}")
            return "Authorization failed: Invalid token format", 400
        
        # Validate required token fields
        required_fields = ['access_token', 'token_type']
        missing_fields = [field for field in required_fields if field not in token]
        if missing_fields:
            logger.error(f"OAuth token missing required fields: {missing_fields}")
            return f"Authorization failed: Missing token fields: {', '.join(missing_fields)}", 400
        
        logger.info(f"Received OAuth token with fields: {list(token.keys())}")
        
        # The enhanced session configuration handles token storage automatically via the API client's token saver
        # But we need to ensure the token is properly stored by triggering the saver manually if needed
        try:
            # Filter and store the token manually to ensure it's saved
            allowed_fields = {
                "access_token", "refresh_token", "token_type",
                "expires_in", "expires_at", "scope", "id_token"
            }
            filtered_token = {k: v for k, v in token.items() if k in allowed_fields}
            
            from flask import session
            session.permanent = True
            session['token'] = filtered_token
            session.modified = True
            logger.info("OAuth token stored in session successfully")
        except Exception as token_error:
            logger.error(f"Failed to store token in session: {token_error}")
            return f"Authorization failed: Token storage error: {str(token_error)}", 400
        
        # Get tenant information
        from xero_python.identity import IdentityApi
        try:
            identity = IdentityApi(api_client)
            conns = identity.get_connections()
            if not conns:
                return "No Xero organisations available for this user.", 400
            
            tenant_id = conns[0].tenant_id
            session['tenant_id'] = tenant_id
            logger.info(f"Connected to Xero tenant: {tenant_id}")
            
            # Save token and tenant using existing function
            save_token_and_tenant(filtered_token, tenant_id)
            
        except Exception as identity_error:
            logger.error(f"Failed to get Xero identity: {identity_error}")
            return f"Authorization failed: Identity error: {str(identity_error)}", 400
        
        # Log security event
        if SECURITY_ENABLED:
            security.log_security_event("xero_oauth_success", "web_user", {
                "tenant_id": session['tenant_id'],
                "timestamp": datetime.now().isoformat()
            })
        
        return redirect(url_for('profile'))
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return f"Authorization failed: {str(e)}", 400

@app.route('/profile')
def profile():
    """Xero profile page"""
    if not XERO_AVAILABLE:
        return redirect(url_for('setup_wizard'))
        
    if 'token' not in session:
        return redirect(url_for('login'))
    if 'tenant_id' not in session:
        return "No tenant selected.", 400

    try:
        accounting = AccountingApi(api_client)
        accounts = accounting.get_accounts(session['tenant_id'])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Xero Profile - Financial Command Center</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f5f7fa; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }}
                .account {{ background: #f8f9ff; padding: 15px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #667eea; }}
                .btn {{ background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; margin: 5px; }}
                .success-banner {{ background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); padding: 20px; border-radius: 8px; margin-bottom: 30px; color: #155724; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-banner">
                    <h2>✅ Successfully Connected to Xero!</h2>
                    <p>Your accounting integration is now active and ready to use.</p>
                </div>
                
                <h1>Xero Integration Status</h1>
                <p><strong>Tenant ID:</strong> {session['tenant_id']}</p>
                <p><strong>Total Accounts:</strong> {len(accounts.accounts)}</p>
                <p><strong>Connection Status:</strong> <span style="color: #27ae60;">✅ Active</span></p>
                
                <h3>Sample Accounts (First 5):</h3>
                {''.join([f'<div class="account"><strong>{account.name}</strong><br><small>Code: {account.code}</small></div>' for account in accounts.accounts[:5]])}
                
                <div style="margin-top: 30px;">
                    <a href="/xero/contacts" class="btn">📋 View Contacts</a>
                    <a href="/xero/invoices" class="btn">🧾 View Invoices</a>
                    <a href="/admin/dashboard" class="btn">📊 Admin Dashboard</a>
                    <a href="/" class="btn">🏠 Home</a>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"Error fetching profile: {str(e)}", 500

@app.route('/logout')
def logout():
    """Logout from Xero"""
    session.pop('token', None)
    session.pop('tenant_id', None)
    return redirect(url_for('index'))

# Web UI Endpoints for Xero Data

@app.route('/xero/contacts')
def view_xero_contacts():
    """Web UI for viewing Xero contacts"""
    if not XERO_AVAILABLE:
        return redirect(url_for('setup_wizard'))
        
    if 'token' not in session:
        return redirect(url_for('login'))
    if 'tenant_id' not in session:
        return "No tenant selected. Please <a href='/login'>login again</a>.", 400

    try:
        from xero_python.accounting import AccountingApi
        accounting_api = AccountingApi(api_client)
        logger.info(f"Fetching contacts for tenant: {session['tenant_id']}")
        contacts = accounting_api.get_contacts(xero_tenant_id=session['tenant_id'])
        logger.info(f"Retrieved {len(contacts.contacts if contacts.contacts else [])} contacts")
        
        # Prepare contacts data
        contacts_data = []
        for i, contact in enumerate(contacts.contacts[:50]):  # Limit to first 50 for performance
            try:
                # Safely get contact status
                status = 'N/A'
                if hasattr(contact, 'contact_status') and contact.contact_status:
                    if hasattr(contact.contact_status, 'value'):
                        status = contact.contact_status.value
                    else:
                        status = str(contact.contact_status)
                
                contacts_data.append({
                    'contact_id': getattr(contact, 'contact_id', f'unknown_{i}'),
                    'name': getattr(contact, 'name', 'N/A') or 'N/A',
                    'email': getattr(contact, 'email_address', 'N/A') or 'N/A',
                    'phone': getattr(contact, 'phone_number', 'N/A') or 'N/A',
                    'status': status,
                    'is_supplier': bool(getattr(contact, 'is_supplier', False)),
                    'is_customer': bool(getattr(contact, 'is_customer', False)),
                    'first_name': getattr(contact, 'first_name', '') or '',
                    'last_name': getattr(contact, 'last_name', '') or ''
                })
            except Exception as contact_error:
                logger.warning(f"Error processing contact {i}: {contact_error}")
                # Add a placeholder contact so the UI doesn't break
                contacts_data.append({
                    'contact_id': f'error_{i}',
                    'name': f'Contact {i} (Error)',
                    'email': 'N/A',
                    'phone': 'N/A',
                    'status': 'Error',
                    'is_supplier': False,
                    'is_customer': False,
                    'first_name': '',
                    'last_name': ''
                })
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Xero Contacts - Financial Command Center</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    min-height: 100vh;
                }}
                .container {{ 
                    max-width: 1200px; 
                    margin: 0 auto; 
                    background: white; 
                    border-radius: 15px; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1); 
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{ margin: 0; font-size: 2.5em; font-weight: 300; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                .content {{ padding: 30px; }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .stat-card {{
                    background: #f8f9ff;
                    padding: 20px;
                    border-radius: 10px;
                    border-left: 4px solid #667eea;
                    text-align: center;
                }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #667eea; margin-bottom: 5px; }}
                .stat-label {{ color: #666; font-size: 0.9em; }}
                .contacts-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                    gap: 20px;
                    margin-top: 20px;
                }}
                .contact-card {{
                    background: white;
                    border: 1px solid #e1e5e9;
                    border-radius: 10px;
                    padding: 20px;
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                }}
                .contact-card:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                    border-color: #667eea;
                }}
                .contact-name {{ font-size: 1.2em; font-weight: 600; color: #333; margin-bottom: 8px; }}
                .contact-email {{ color: #667eea; font-size: 0.9em; margin-bottom: 5px; }}
                .contact-phone {{ color: #666; font-size: 0.9em; margin-bottom: 10px; }}
                .contact-tags {{ margin-top: 10px; }}
                .tag {{
                    display: inline-block;
                    padding: 3px 8px;
                    background: #e8f2ff;
                    color: #0066cc;
                    border-radius: 12px;
                    font-size: 0.8em;
                    margin-right: 5px;
                    margin-bottom: 5px;
                }}
                .tag.supplier {{ background: #fff3cd; color: #856404; }}
                .tag.customer {{ background: #d4edda; color: #155724; }}
                .nav-buttons {{
                    text-align: center;
                    padding: 20px;
                    border-top: 1px solid #e1e5e9;
                    background: #f8f9fa;
                }}
                .btn {{
                    display: inline-block;
                    padding: 12px 24px;
                    margin: 0 10px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 500;
                    transition: all 0.3s ease;
                }}
                .btn:hover {{ background: #5a6fd8; transform: translateY(-1px); }}
                .btn.secondary {{ background: #6c757d; }}
                .btn.secondary:hover {{ background: #5a6268; }}
                .search-box {{
                    width: 100%;
                    max-width: 300px;
                    padding: 10px 15px;
                    border: 1px solid #ddd;
                    border-radius: 25px;
                    font-size: 14px;
                    margin-bottom: 20px;
                }}
                .search-box:focus {{
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
                }}
                @media (max-width: 768px) {{
                    .contacts-grid {{ grid-template-columns: 1fr; }}
                    .stats {{ grid-template-columns: repeat(2, 1fr); }}
                    .header h1 {{ font-size: 2em; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Xero Contacts</h1>
                    <p>Connected to tenant: {session['tenant_id']}</p>
                </div>
                
                <div class="content">
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-number">{len(contacts_data)}</div>
                            <div class="stat-label">Total Contacts</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{len([c for c in contacts_data if c['is_customer']])}</div>
                            <div class="stat-label">Customers</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{len([c for c in contacts_data if c['is_supplier']])}</div>
                            <div class="stat-label">Suppliers</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{len([c for c in contacts_data if c['email'] != 'N/A'])}</div>
                            <div class="stat-label">With Email</div>
                        </div>
                    </div>
                    
                    <input type="text" id="searchBox" class="search-box" placeholder="🔍 Search contacts..." onkeyup="filterContacts()">
                    
                    <div class="contacts-grid" id="contactsGrid">
                        {''.join([
                            f'''<div class="contact-card" data-name="{contact['name'].lower()}" data-email="{contact['email'].lower()}">
                                <div class="contact-name">{contact['name']}</div>
                                <div class="contact-email">📧 {contact['email']}</div>
                                <div class="contact-phone">📞 {contact['phone']}</div>
                                <div class="contact-tags">
                                    <span class="tag">Status: {contact['status']}</span>
                                    {('<span class="tag customer">Customer</span>' if contact['is_customer'] else '')}
                                    {('<span class="tag supplier">Supplier</span>' if contact['is_supplier'] else '')}
                                </div>
                            </div>''' 
                            for contact in contacts_data
                        ])}
                    </div>
                </div>
                
                <div class="nav-buttons">
                    <a href="/xero/invoices" class="btn">🧾 View Invoices</a>
                    <a href="/profile" class="btn secondary">👤 Back to Profile</a>
                    <a href="/" class="btn secondary">🏠 Home</a>
                </div>
            </div>
            
            <script>
                function filterContacts() {{
                    const searchTerm = document.getElementById('searchBox').value.toLowerCase();
                    const contacts = document.querySelectorAll('.contact-card');
                    
                    contacts.forEach(contact => {{
                        const name = contact.getAttribute('data-name');
                        const email = contact.getAttribute('data-email');
                        
                        if (name.includes(searchTerm) || email.includes(searchTerm)) {{
                            contact.style.display = 'block';
                        }} else {{
                            contact.style.display = 'none';
                        }}
                    }});
                }}
            </script>
        </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"Error fetching contacts: {e}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error - Xero Contacts</title></head>
        <body style="font-family: Arial, sans-serif; padding: 40px; text-align: center;">
            <h1 style="color: #e74c3c;">❌ Error Loading Contacts</h1>
            <p>There was an error loading your Xero contacts:</p>
            <p style="color: #666; font-style: italic;">{str(e)}</p>
            <p><a href="/login" style="color: #667eea;">Try logging in again</a> or <a href="/profile" style="color: #667eea;">return to profile</a></p>
        </body>
        </html>
        """, 500

@app.route('/xero/invoices')
def view_xero_invoices():
    """Web UI for viewing Xero invoices"""
    if not XERO_AVAILABLE:
        return redirect(url_for('setup_wizard'))
        
    if 'token' not in session:
        return redirect(url_for('login'))
    if 'tenant_id' not in session:
        return "No tenant selected. Please <a href='/login'>login again</a>.", 400

    try:
        from xero_python.accounting import AccountingApi
        accounting_api = AccountingApi(api_client)
        
        # Get invoices with status filter
        status_filter = request.args.get('status', 'DRAFT,SUBMITTED,AUTHORISED')
        invoices = accounting_api.get_invoices(
            xero_tenant_id=session['tenant_id'],
            statuses=status_filter.split(',')
        )
        
        # Prepare invoices data
        invoices_data = []
        for invoice in (invoices.invoices or [])[:50]:  # Limit to first 50
            # Safely get invoice type
            invoice_type = 'N/A'
            if hasattr(invoice, 'type') and invoice.type:
                if hasattr(invoice.type, 'value'):
                    invoice_type = invoice.type.value
                else:
                    invoice_type = str(invoice.type)
            
            # Safely get invoice status
            invoice_status = 'N/A'
            if hasattr(invoice, 'status') and invoice.status:
                if hasattr(invoice.status, 'value'):
                    invoice_status = invoice.status.value
                else:
                    invoice_status = str(invoice.status)
            
            # Safely get currency code
            currency = 'USD'
            if hasattr(invoice, 'currency_code') and invoice.currency_code:
                if hasattr(invoice.currency_code, 'value'):
                    currency = invoice.currency_code.value
                else:
                    currency = str(invoice.currency_code)
            
            # Safely get contact name
            contact_name = 'N/A'
            if hasattr(invoice, 'contact') and invoice.contact:
                contact_name = getattr(invoice.contact, 'name', 'N/A') or 'N/A'
            
            invoices_data.append({
                'invoice_id': getattr(invoice, 'invoice_id', 'N/A'),
                'invoice_number': getattr(invoice, 'invoice_number', 'N/A'),
                'type': invoice_type,
                'status': invoice_status,
                'total': float(getattr(invoice, 'total', 0) or 0),
                'currency_code': currency,
                'date': getattr(invoice, 'date', None),
                'due_date': getattr(invoice, 'due_date', None),
                'contact_name': contact_name,
                'amount_due': float(getattr(invoice, 'amount_due', 0) or 0),
                'amount_paid': float(getattr(invoice, 'amount_paid', 0) or 0)
            })
        
        # Calculate statistics
        total_amount = sum(inv['total'] for inv in invoices_data)
        total_due = sum(inv['amount_due'] for inv in invoices_data)
        total_paid = sum(inv['amount_paid'] for inv in invoices_data)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Xero Invoices - Financial Command Center</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    min-height: 100vh;
                }}
                .container {{ 
                    max-width: 1400px; 
                    margin: 0 auto; 
                    background: white; 
                    border-radius: 15px; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1); 
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{ margin: 0; font-size: 2.5em; font-weight: 300; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                .content {{ padding: 30px; }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .stat-card {{
                    background: #f8f9ff;
                    padding: 20px;
                    border-radius: 10px;
                    border-left: 4px solid #764ba2;
                    text-align: center;
                }}
                .stat-number {{ font-size: 1.8em; font-weight: bold; color: #764ba2; margin-bottom: 5px; }}
                .stat-label {{ color: #666; font-size: 0.9em; }}
                .invoice-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    background: white;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .invoice-table th {{
                    background: #f8f9fa;
                    padding: 15px 12px;
                    text-align: left;
                    font-weight: 600;
                    color: #495057;
                    border-bottom: 2px solid #dee2e6;
                }}
                .invoice-table td {{
                    padding: 12px;
                    border-bottom: 1px solid #dee2e6;
                }}
                .invoice-table tr:hover {{
                    background-color: #f8f9ff;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 0.85em;
                    font-weight: 500;
                    text-transform: uppercase;
                }}
                .status-draft {{ background: #fff3cd; color: #856404; }}
                .status-submitted {{ background: #cce5ff; color: #004085; }}
                .status-authorised {{ background: #d4edda; color: #155724; }}
                .status-paid {{ background: #d1ecf1; color: #0c5460; }}
                .type-badge {{
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 0.8em;
                    font-weight: 500;
                }}
                .type-accrec {{ background: #e8f5e8; color: #2e7d32; }}
                .type-accpay {{ background: #fff3e0; color: #f57c00; }}
                .amount {{ font-weight: 600; }}
                .amount.positive {{ color: #27ae60; }}
                .amount.negative {{ color: #e74c3c; }}
                .nav-buttons {{
                    text-align: center;
                    padding: 20px;
                    border-top: 1px solid #e1e5e9;
                    background: #f8f9fa;
                }}
                .btn {{
                    display: inline-block;
                    padding: 12px 24px;
                    margin: 0 10px;
                    background: #764ba2;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 500;
                    transition: all 0.3s ease;
                }}
                .btn:hover {{ background: #6a4c93; transform: translateY(-1px); }}
                .btn.secondary {{ background: #6c757d; }}
                .btn.secondary:hover {{ background: #5a6268; }}
                .search-filter {{
                    display: flex;
                    gap: 15px;
                    margin-bottom: 20px;
                    flex-wrap: wrap;
                    align-items: center;
                }}
                .search-box, .filter-select {{
                    padding: 10px 15px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 14px;
                }}
                .search-box {{ flex: 1; min-width: 200px; }}
                .filter-select {{ min-width: 150px; }}
                @media (max-width: 768px) {{
                    .stats {{ grid-template-columns: repeat(2, 1fr); }}
                    .header h1 {{ font-size: 2em; }}
                    .invoice-table {{ font-size: 0.9em; }}
                    .search-filter {{ flex-direction: column; }}
                    .search-box, .filter-select {{ width: 100%; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧾 Xero Invoices</h1>
                    <p>Connected to tenant: {session['tenant_id']}</p>
                </div>
                
                <div class="content">
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-number">{len(invoices_data)}</div>
                            <div class="stat-label">Total Invoices</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${total_amount:,.2f}</div>
                            <div class="stat-label">Total Amount</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${total_due:,.2f}</div>
                            <div class="stat-label">Amount Due</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${total_paid:,.2f}</div>
                            <div class="stat-label">Amount Paid</div>
                        </div>
                    </div>
                    
                    <div class="search-filter">
                        <input type="text" id="searchBox" class="search-box" placeholder="🔍 Search invoices..." onkeyup="filterInvoices()">
                        <select id="statusFilter" class="filter-select" onchange="filterInvoices()">
                            <option value="">All Statuses</option>
                            <option value="DRAFT">Draft</option>
                            <option value="SUBMITTED">Submitted</option>
                            <option value="AUTHORISED">Authorised</option>
                            <option value="PAID">Paid</option>
                        </select>
                    </div>
                    
                    <table class="invoice-table">
                        <thead>
                            <tr>
                                <th>Invoice #</th>
                                <th>Contact</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Date</th>
                                <th>Due Date</th>
                                <th>Total</th>
                                <th>Amount Due</th>
                            </tr>
                        </thead>
                        <tbody id="invoiceTableBody">
                            {''.join([
                                f'''<tr class="invoice-row" data-contact="{invoice['contact_name'].lower()}" data-number="{invoice['invoice_number'].lower()}" data-status="{invoice['status'].lower()}">
                                    <td><strong>{invoice['invoice_number']}</strong></td>
                                    <td>{invoice['contact_name']}</td>
                                    <td><span class="type-badge type-{invoice['type'].lower()}">{invoice['type']}</span></td>
                                    <td><span class="status-badge status-{invoice['status'].lower()}">{invoice['status']}</span></td>
                                    <td>{invoice['date'].strftime('%Y-%m-%d') if invoice['date'] else 'N/A'}</td>
                                    <td>{invoice['due_date'].strftime('%Y-%m-%d') if invoice['due_date'] else 'N/A'}</td>
                                    <td class="amount positive">{invoice['currency_code']} ${invoice['total']:,.2f}</td>
                                    <td class="amount {'positive' if invoice['amount_due'] > 0 else 'negative' if invoice['amount_due'] < 0 else ''}">${invoice['amount_due']:,.2f}</td>
                                </tr>'''
                                for invoice in invoices_data
                            ])}
                        </tbody>
                    </table>
                </div>
                
                <div class="nav-buttons">
                    <a href="/xero/contacts" class="btn">📋 View Contacts</a>
                    <a href="/profile" class="btn secondary">👤 Back to Profile</a>
                    <a href="/" class="btn secondary">🏠 Home</a>
                </div>
            </div>
            
            <script>
                function filterInvoices() {{
                    const searchTerm = document.getElementById('searchBox').value.toLowerCase();
                    const statusFilter = document.getElementById('statusFilter').value.toLowerCase();
                    const rows = document.querySelectorAll('.invoice-row');
                    
                    rows.forEach(row => {{
                        const contact = row.getAttribute('data-contact');
                        const number = row.getAttribute('data-number');
                        const status = row.getAttribute('data-status');
                        
                        const matchesSearch = contact.includes(searchTerm) || number.includes(searchTerm);
                        const matchesStatus = statusFilter === '' || status === statusFilter;
                        
                        if (matchesSearch && matchesStatus) {{
                            row.style.display = 'table-row';
                        }} else {{
                            row.style.display = 'none';
                        }}
                    }});
                }}
            </script>
        </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error - Xero Invoices</title></head>
        <body style="font-family: Arial, sans-serif; padding: 40px; text-align: center;">
            <h1 style="color: #e74c3c;">❌ Error Loading Invoices</h1>
            <p>There was an error loading your Xero invoices:</p>
            <p style="color: #666; font-style: italic;">{str(e)}</p>
            <p><a href="/login" style="color: #667eea;">Try logging in again</a> or <a href="/profile" style="color: #667eea;">return to profile</a></p>
        </body>
        </html>
        """, 500

# Enhanced API Endpoints

@app.route('/api/xero/contacts', methods=['GET'])
@require_api_key
def get_xero_contacts():
    """Get Xero contacts - enhanced with setup wizard integration"""
    if not XERO_AVAILABLE:
        return jsonify({
            'error': 'Xero not configured',
            'message': 'Complete setup wizard first',
            'setup_url': url_for('setup_wizard', _external=True)
        }), 400
        
    if not session.get("token"):
        return redirect(url_for('login'))
    
    try:
        accounting_api = AccountingApi(api_client)
        contacts = accounting_api.get_contacts(
            xero_tenant_id=session.get('tenant_id')
        )
        
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
        
        return jsonify({
            'success': True,
            'contacts': contacts_data,
            'count': len(contacts_data),
            'client': request.client_info['client_name'],
            'tenant_id': session.get('tenant_id')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/xero/invoices', methods=['GET'])
@require_api_key
def get_xero_invoices():
    """Get Xero invoices - available once Xero is configured and authed.
    Adds sensible defaults and clear errors when not ready."""
    if not XERO_AVAILABLE:
        return jsonify({
            'error': 'Xero not configured',
            'message': 'Complete setup wizard first',
            'setup_url': url_for('setup_wizard', _external=True)
        }), 400

    if not session.get("token"):
        return redirect(url_for('login'))

    # Filters
    status_filter = request.args.get('status', 'DRAFT,SUBMITTED,AUTHORISED')
    limit = min(int(request.args.get('limit', 50)), 100)

    try:
        accounting_api = AccountingApi(api_client)
        invoices = accounting_api.get_invoices(
            xero_tenant_id=session.get('tenant_id'),
            statuses=status_filter.split(',')
        )

        log_transaction('xero_invoices_access', len(invoices.invoices), 'items', 'success')

        invoices_data = []
        for i, invoice in enumerate(invoices.invoices or []):
            if i >= limit:
                break
            invoices_data.append({
                'invoice_id': getattr(invoice, 'invoice_id', None),
                'invoice_number': getattr(invoice, 'invoice_number', None),
                'type': getattr(getattr(invoice, 'type', None), 'value', None),
                'status': getattr(getattr(invoice, 'status', None), 'value', None),
                'total': float(getattr(invoice, 'total', 0) or 0),
                'currency_code': getattr(getattr(invoice, 'currency_code', None), 'value', 'USD'),
                'date': getattr(getattr(invoice, 'date', None), 'isoformat', lambda: None)(),
                'due_date': getattr(getattr(invoice, 'due_date', None), 'isoformat', lambda: None)(),
                'contact_name': getattr(getattr(invoice, 'contact', None), 'name', None),
            })

        return jsonify({
            'success': True,
            'invoices': invoices_data,
            'count': len(invoices_data),
            'total_available': len(getattr(invoices, 'invoices', []) or []),
            'filters': {'status': status_filter, 'limit': limit}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stripe/payment', methods=['POST'])
@require_api_key
def create_stripe_payment():
    """Create Stripe payment - enhanced with setup wizard integration"""
    credentials = get_credentials_or_redirect()
    stripe_key = credentials.get('STRIPE_API_KEY')
    
    if not stripe_key:
        integration_status = get_integration_status()
        if integration_status.get('stripe', {}).get('skipped'):
            return jsonify({
                'error': 'Stripe in demo mode',
                'message': 'Stripe was skipped during setup - configure it to process real payments',
                'setup_url': url_for('setup_wizard', _external=True),
                'demo': True
            }), 400
        else:
            return jsonify({
                'error': 'Stripe not configured',
                'message': 'Complete setup wizard first',
                'setup_url': url_for('setup_wizard', _external=True)
            }), 400
    
    try:
        import stripe
        stripe.api_key = stripe_key
        
        data = request.get_json()
        if not data or 'amount' not in data:
            return jsonify({'error': 'amount required'}), 400
        
        amount_dollars = float(data['amount'])
        amount_cents = int(amount_dollars * 100)
        currency = data.get('currency', 'usd')
        description = data.get('description', f'Payment via {request.client_info["client_name"]}')
        
        log_transaction('stripe_payment_create', amount_dollars, currency, 'initiated')
        
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            description=description,
            automatic_payment_methods={'enabled': True}
        )
        
        log_transaction('stripe_payment_create', amount_dollars, currency, 'created')
        
        return jsonify({
            'success': True,
            'payment_intent_id': payment_intent.id,
            'client_secret': payment_intent.client_secret,
            'amount': amount_dollars,
            'currency': currency,
            'status': payment_intent.status,
            'client': request.client_info['client_name']
        })
        
    except Exception as e:
        log_transaction('stripe_payment_create', 
                       data.get('amount', 0) if 'data' in locals() else 0, 
                       data.get('currency', 'usd') if 'data' in locals() else 'usd', 
                       'failed')
        return jsonify({'error': str(e)}), 500

# Enhanced Admin Dashboard

@app.route('/admin/dashboard')
def admin_dashboard():
    """Enhanced admin dashboard with setup wizard integration"""
    if not SECURITY_ENABLED:
        return """
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial; margin: 40px;">
            <h1>⚠️ Security Module Not Available</h1>
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
    
    # Load security data and integration status
    api_keys = security._load_json(security.auth_file)
    audit_log = security._load_json(security.audit_file)
    recent_events = audit_log.get('events', [])[-10:]
    integration_status = get_integration_status()
    
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Financial Command Center - Admin Dashboard</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f7fa; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-box { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
            .stat-value { font-size: 2.5em; font-weight: bold; color: #667eea; margin-bottom: 10px; }
            .stat-label { color: #666; }
            .section { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .integration-status { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .integration-card { padding: 20px; border-radius: 8px; border-left: 4px solid #ddd; }
            .integration-card.configured { border-left-color: #27ae60; background: #d4edda; }
            .integration-card.skipped { border-left-color: #f39c12; background: #fff3cd; }
            .integration-card.not-configured { border-left-color: #e74c3c; background: #f8d7da; }
            .btn { background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
            .btn:hover { background: #5a6fd8; }
            .api-key { border-left: 4px solid #667eea; padding: 15px; margin: 10px 0; background: #f8f9ff; }
            .event { padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 5px; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏦 Financial Command Center AI</h1>
                <p>Admin Dashboard - System Management & Monitoring</p>
            </div>
            
            {% if not api_keys %}
            <div class="section" style="border-left:4px solid #f39c12; background:#fff3cd;">
                <h3 style="margin-top:0;">First‑Run Tip: Create a Demo API Key</h3>
                <p>To call APIs from your browser or curl, create a demo key and include it in the <code>X-API-Key</code> header.</p>
                <div class="api-key" style="background:#fff;">
                    <div><a class="btn" href="/admin/create-demo-key">Create Demo Key</a></div>
                    <div style="margin-top:10px; font-family:monospace; font-size:14px;">curl -k -H "X-API-Key: YOUR_KEY" https://localhost:8000/health</div>
                </div>
            </div>
            {% endif %}

            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{{ total_keys }}</div>
                    <div class="stat-label">Total API Keys</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" style="color: #27ae60;">{{ active_keys }}</div>
                    <div class="stat-label">Active Keys</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{{ configured_services }}</div>
                    <div class="stat-label">Configured Services</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{{ recent_events|length }}</div>
                    <div class="stat-label">Recent Events</div>
                </div>
            </div>
            
            <div class="section">
                <h2>🔌 Integration Status</h2>
                <div class="integration-status">
                    <div class="integration-card {{ 'configured' if stripe_configured else 'skipped' if stripe_skipped else 'not-configured' }}">
                        <h3>💳 Stripe Integration</h3>
                        <p><strong>Status:</strong> {{ '✅ Configured & Active' if stripe_configured else '⏭️ Skipped (Demo Mode)' if stripe_skipped else '❌ Not Configured' }}</p>
                        <p><strong>Payment Processing:</strong> {{ 'Enabled' if stripe_configured else 'Demo Mode' if stripe_skipped else 'Disabled' }}</p>
                    </div>
                    
                    <div class="integration-card {{ 'configured' if xero_configured else 'skipped' if xero_skipped else 'not-configured' }}">
                        <h3>📊 Xero Integration</h3>
                        <p><strong>Status:</strong> {{ '✅ Configured & Active' if xero_configured else '⏭️ Skipped (Demo Mode)' if xero_skipped else '❌ Not Configured' }}</p>
                        <p><strong>Accounting Sync:</strong> {{ 'Enabled' if xero_configured else 'Demo Mode' if xero_skipped else 'Disabled' }}</p>
                    </div>
                    
                    <div class="integration-card" style="border-left-color: #2563eb; background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(99, 102, 241, 0.1) 100%);">
                        <h3>Claude Desktop AI</h3>
                        <p><strong>Status:</strong> Ready for Setup</p>
                        <p><strong>AI Operations:</strong> Natural Language Commands</p>
                        <p><strong>Commands:</strong> "Show cash flow", "List unpaid invoices", "Find contacts"</p>
                        <div style="margin-top: 15px;">
                            <a href="/claude/setup" class="btn" style="background: #2563eb; font-size: 0.9em; padding: 8px 16px;">🛠️ Configure Now</a>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>🔑 API Keys Management</h2>
                {% if api_keys %}
                    {% for key, info in api_keys.items() %}
                    <div class="api-key">
                        <h3>{{ info.client_name }}</h3>
                        <p><strong>API Key:</strong> <code>{{ key[:25] }}...</code></p>
                        <p><strong>Status:</strong> 
                            <span style="color: {{ '#27ae60' if info.active else '#e74c3c' }};">
                                {{ 'Active' if info.active else 'Inactive' }}
                            </span>
                        </p>
                        <p><strong>Created:</strong> {{ info.created_at }}</p>
                        <p><strong>Last Used:</strong> {{ info.last_used or 'Never' }}</p>
                        <p><strong>Permissions:</strong> {{ ', '.join(info.permissions) }}</p>
                    </div>
                    {% endfor %}
                {% else %}
                    <p>No API keys created yet. Use <a href="/admin/create-demo-key">Create Demo Key</a> to generate one instantly.</p>
                {% endif %}
            </div>
            
            <div class="section">
                <h2>📊 Recent Activity</h2>
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
                <h2>🚀 Quick Actions</h2>
                <a href="/claude/setup" class="btn" style="background: #2563eb;">Connect to Claude Desktop</a>
                <a href="/setup" class="btn">⚙️ Configuration Wizard</a>
                <a href="/health" class="btn">💓 Health Check</a>
                {% if xero_configured %}
                <a href="/login" class="btn">🔗 Connect Xero</a>
                {% endif %}
                <a href="/admin/create-demo-key" class="btn">🔑 Create Demo Key</a>
                <a href="/" class="btn">🏠 Home</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Calculate stats
    total_keys = len(api_keys)
    active_keys = sum(1 for info in api_keys.values() if info.get('active', False))
    configured_services = sum([
        integration_status.get('stripe', {}).get('configured', False),
        integration_status.get('xero', {}).get('configured', False)
    ])
    
    from jinja2 import Template
    template = Template(dashboard_html)
    
    return template.render(
        api_keys=api_keys,
        total_keys=total_keys,
        active_keys=active_keys,
        configured_services=configured_services,
        recent_events=recent_events,
        stripe_configured=integration_status.get('stripe', {}).get('configured', False),
        stripe_skipped=integration_status.get('stripe', {}).get('skipped', False),
        xero_configured=integration_status.get('xero', {}).get('configured', False),
        xero_skipped=integration_status.get('xero', {}).get('skipped', False)
    )

@app.route('/admin/create-demo-key')
def create_demo_key():
    """Create demo API key via web interface"""
    if not SECURITY_ENABLED:
        return "Security module not available. Install cryptography and create auth/security.py", 500
    
    demo_key = security.generate_api_key("Web Demo Client", ["read", "write"])
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Demo API Key Created</title>
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
            <h1>🔑 Demo API Key Created!</h1>
            
            <div class="key-box">
                <h3>Your New API Key:</h3>
                <div class="code">{demo_key}</div>
                <p><strong>⚠️ Important:</strong> Save this key securely - it won't be shown again!</p>
            </div>
            
            <h3>🧪 Test Your API Key:</h3>
            
            <h4>1. Test Authentication:</h4>
            <div class="code">
curl -H "X-API-Key: {demo_key}" https://localhost:8000/api/ping
            </div>
            
            <h4>2. Get Health Status:</h4>
            <div class="code">
curl -H "X-API-Key: {demo_key}" https://localhost:8000/health
            </div>
            
            <div style="margin-top: 30px;">
                <a href="/admin/dashboard" class="btn">← Back to Dashboard</a>
                <a href="/setup" class="btn">⚙️ Configuration Wizard</a>
            </div>
        </div>
    </body>
    </html>
    """

# Claude Desktop Integration Routes - Now handled by claude_integration.py module
# (Routes removed to prevent duplication)

# Duplicate Claude routes removed - now handled by claude_integration.py

# =============================================================================
# MCP Integration API Endpoints  
# =============================================================================

@app.route('/api/cash-flow', methods=['GET'])
def get_cash_flow():
    """Get cash flow information"""
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'
    
    if not wants_json:
        return "Cash flow endpoint - use Accept: application/json header", 400
    
    # Mock cash flow data
    cash_flow_data = {
        'status': 'healthy',
        'cash_flow': {
            'current_balance': 45750.32,
            'currency': 'USD',
            'monthly_inflow': 89500.00,
            'monthly_outflow': 67200.00,
            'net_monthly': 22300.00,
            'trend': 'positive',
            'accounts': [
                {'name': 'Main Operating', 'balance': 35750.32, 'type': 'checking'},
                {'name': 'Reserve Fund', 'balance': 10000.00, 'type': 'savings'}
            ],
            'recent_transactions': [
                {'date': '2025-09-13', 'description': 'Client Payment', 'amount': 5500.00, 'type': 'inflow'},
                {'date': '2025-09-12', 'description': 'Office Rent', 'amount': -2800.00, 'type': 'outflow'},
                {'date': '2025-09-11', 'description': 'Software License', 'amount': -299.00, 'type': 'outflow'},
            ]
        },
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify(cash_flow_data)

@app.route('/api/invoices', methods=['GET'])
def get_invoices():
    """Get invoices with optional filtering"""
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'
    
    if not wants_json:
        return "Invoices endpoint - use Accept: application/json header", 400
    
    # Get filter parameters
    status = request.args.get('status', 'all').lower()
    amount_min = request.args.get('amount_min', type=float)
    customer = request.args.get('customer', '').lower()
    
    # Mock invoice data with realistic business data
    all_invoices = [
        {'invoice_id': 'INV-2025-001', 'customer': 'Acme Corporation', 'amount': 8750.00, 'status': 'paid'},
        {'invoice_id': 'INV-2025-002', 'customer': 'TechStart Inc', 'amount': 2450.00, 'status': 'pending'},
        {'invoice_id': 'INV-2025-003', 'customer': 'Global Systems Ltd', 'amount': 15750.00, 'status': 'overdue'},
        {'invoice_id': 'INV-2025-004', 'customer': 'StartupXYZ', 'amount': 650.00, 'status': 'draft'}
    ]
    
    # Apply filters
    filtered_invoices = all_invoices
    if status != 'all':
        filtered_invoices = [inv for inv in filtered_invoices if inv['status'] == status]
    if amount_min:
        filtered_invoices = [inv for inv in filtered_invoices if inv['amount'] >= amount_min]
    if customer:
        filtered_invoices = [inv for inv in filtered_invoices if customer in inv['customer'].lower()]
    
    return jsonify({'status': 'success', 'invoices': filtered_invoices, 'total_count': len(filtered_invoices)})

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """Get customer/supplier contacts"""
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'
    
    if not wants_json:
        return "Contacts endpoint - use Accept: application/json header", 400
    
    search_term = request.args.get('search', '').lower()
    
    all_contacts = [
        {'contact_id': 'CNT-001', 'name': 'Acme Corporation', 'email': 'billing@acme-corp.com', 'type': 'customer'},
        {'contact_id': 'CNT-002', 'name': 'TechStart Inc', 'email': 'accounts@techstart.io', 'type': 'customer'},
        {'contact_id': 'CNT-003', 'name': 'Global Systems Ltd', 'email': 'finance@globalsys.com', 'type': 'customer'},
        {'contact_id': 'CNT-004', 'name': 'StartupXYZ', 'email': 'hello@startupxyz.com', 'type': 'customer'}
    ]
    
    if search_term:
        filtered_contacts = [c for c in all_contacts if search_term in c['name'].lower() or search_term in c['email'].lower()]
    else:
        filtered_contacts = all_contacts
    
    return jsonify({'status': 'success', 'contacts': filtered_contacts, 'total_count': len(filtered_contacts)})

@app.route('/api/dashboard', methods=['GET']) 
def get_dashboard():
    """Get comprehensive financial dashboard data"""
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'
    
    if not wants_json:
        return "Dashboard endpoint - use Accept: application/json header", 400
    
    dashboard_data = {
        'status': 'healthy',
        'overview': {'total_revenue_ytd': 245780.50, 'net_profit_ytd': 56360.20, 'profit_margin': 22.9},
        'cash_flow': {'current_balance': 45750.32, 'monthly_burn_rate': 67200.00},
        'invoices': {'total_outstanding': 18850.00, 'overdue_amount': 15750.00, 'pending_count': 3},
        'integrations': {
            'stripe': {'status': 'connected'}, 
            'xero': {'status': 'connected'}, 
            'plaid': {'status': 'connected'}
        },
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify(dashboard_data)
if __name__ == '__main__':
    print("🚀 Starting Financial Command Center with Setup Wizard...")
    print("=" * 60)
    print(f"🔐 Security: {'Enabled' if SECURITY_ENABLED else 'Disabled'}")
    print(f"⚙️ Setup Wizard: Enabled")
    print(f"📊 Xero: {'Available' if XERO_AVAILABLE else 'Needs Configuration'}")
    
    credentials = get_credentials_or_redirect()
    print(f"💳 Stripe: {'Configured' if credentials.get('STRIPE_API_KEY') else 'Needs Setup'}")
    
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
            print("🔐 HTTPS Mode - Ensuring SSL certificates...")
            cert_generated = cert_manager.ensure_certificates()
            ssl_context = cert_manager.get_ssl_context()
            
            if cert_generated:
                print("✨ New SSL certificates generated!")
                print("📦 To eliminate browser warnings, install the CA certificate:")
                print(f"   python cert_manager.py --bundle")
        else:
            # HTTP mode with warnings
            server_mode = "HTTP (with HTTPS upgrade prompts)"
            print("⚠️  HTTP Mode - Running without SSL encryption")
            print("   Set FORCE_HTTPS=true for production use")
    
    except ImportError as e:
        print("⚠️  SSL Certificate Manager not available - using Flask's adhoc SSL")
        print(f"   Install missing dependencies: {e}")
        ssl_context = 'adhoc'
    
    print()
    print("📋 Available endpoints:")
    print("  GET  / - Smart home page (redirects to setup if needed)")
    print("  GET  /setup - Professional setup wizard")
    print("  GET  /health - Enhanced health check")
    
    if SECURITY_ENABLED:
        print("  🔑 Security Endpoints: /api/ping, /api/create-key, /api/key-stats")
    
    print("  📊 Admin: /admin/dashboard")
    print("  💳 Stripe: /api/stripe/payment")
    print("  🔧 SSL Help: /admin/ssl-help")
    print("  📦 Certificate Bundle: /admin/certificate-bundle")
    print("Claude Desktop: /claude/setup, /api/claude/*, /api/mcp")
    
    if XERO_AVAILABLE:
        print("  🔗 Xero: /login, /callback, /profile, /api/xero/contacts, /api/xero/invoices")
    else:
        print("  🔗 Xero: Configure via setup wizard")
    
    print()
    protocol = "https" if ssl_context else "http"
    # Allow launcher to select/override port
    import os as _os
    port = int(_os.getenv('FCC_PORT') or _os.getenv('PORT') or '8000')
    print("🌐 URLs:")
    print(f"  🏠 Home: {protocol}://localhost:{port}/")
    print(f"  ⚙️ Setup: {protocol}://localhost:{port}/setup")
    print(f"  🎛️  Admin: {protocol}://localhost:{port}/admin/dashboard")
    print(f"  🔧 SSL Help: {protocol}://localhost:{port}/admin/ssl-help")
    print()
    
    if is_setup_required() and not os.getenv('STRIPE_API_KEY'):
        print("🎯 FIRST TIME SETUP:")
        print(f"   Visit {protocol}://localhost:{port}/setup to configure your integrations")
        print(f"   Or {protocol}://localhost:{port}/ to start the guided setup")
        print()
    
    print(f"🔒 Server Mode: {server_mode}")
    if ssl_context and ssl_context != 'adhoc':
        print("📜 SSL Certificate Status:")
        try:
            health = cert_manager.health_check()
            print(f"   ✅ Certificate Valid: {health['certificate_valid']}")
            print(f"   📅 Expires: {health['expires']}")
            print(f"   🏷️  Hostnames: {', '.join(health['hostnames'])}")
            if not health['certificate_valid']:
                print("   🔄 Certificates will be regenerated automatically")
        except Exception as e:
            print(f"   ⚠️  Certificate check failed: {e}")
    
    print()
    print("🔥 Professional Financial Command Center ready!")
    
    # Start the Flask application
    if ssl_context:
        app.run(host='localhost', port=port, debug=True, ssl_context=ssl_context)
    else:
        # HTTP mode
        app.run(host='localhost', port=port, debug=True)
# Ensure stdout can print Unicode on Windows consoles
try:
    import io as _io
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    # Fallback hard wrap
    if getattr(sys.stdout, 'encoding', '').lower() != 'utf-8' and hasattr(sys.stdout, 'buffer'):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if getattr(sys.stderr, 'encoding', '').lower() != 'utf-8' and hasattr(sys.stderr, 'buffer'):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass
