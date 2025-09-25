"""
Enhanced Financial Command Center with Professional Setup Wizard
Replaces environment variable configuration with secure setup wizard
"""

import os
import sys

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

import os
import sys

# Add the local LLM adapter to the path before other imports
adapter_path = os.path.join(os.path.dirname(__file__), 'fcc-local-llm-adapter')
if os.path.exists(adapter_path) and adapter_path not in sys.path:
    sys.path.insert(0, adapter_path)

# Load environment variables from .env file FIRST
try:
    from dotenv import load_dotenv
    load_dotenv()
    print(f"Environment loaded - ASSISTANT_MODEL_TYPE: {os.getenv('ASSISTANT_MODEL_TYPE', 'not set')}")
    print(f"Environment loaded - USE_LLAMA32: {os.getenv('USE_LLAMA32', 'not set')}")
except ImportError:
    print("Warning: python-dotenv not installed, .env file will not be loaded")

from flask import Flask, session, redirect, url_for, jsonify, request, render_template
try:
    from flask_cors import CORS
except ImportError:
    CORS = None
from datetime import datetime
import json
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Demo mode manager and mock data
from demo_mode import DemoModeManager, mock_stripe_payment
import xero_demo_data
import plaid_demo_data

# Import setup wizard functionality
from setup_wizard import (
    SetupWizardAPI,
    ConfigurationManager,
    get_configured_credentials,
    is_setup_required,
    get_integration_status,
    sync_credentials_to_env,
)
from ui.helpers import build_nav, format_timestamp, summarize_details
from ui.dashboard import build_admin_dashboard_context
from ui.health import render_health_dashboard


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
from xero_client import save_token_and_tenant, has_stored_token, get_stored_token, clear_token_and_tenant, get_tenant_id
from setup_api_routes import create_setup_blueprint

# Add our security layer
sys.path.append('.')
try:
    from auth.security import SecurityManager, require_api_key, log_transaction
    SECURITY_ENABLED = True
except ImportError:
    print("WARNING: Security module not found. Running without API key authentication.")
    SECURITY_ENABLED = False
    
    # Create dummy decorators if security not available
    def require_api_key(f):
        def wrapper(*args, **kwargs):
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

# Enable debug mode for session debugging
app.config['DEBUG'] = True

# Global integration state placeholders
api_client = None
oauth = None
xero = None
session_config = None
XERO_AVAILABLE = False

def _build_xero_redirect_uri():
    """Compute the redirect URI used for Xero OAuth callbacks."""
    port = os.getenv('FCC_PORT') or os.getenv('PORT') or '8000'
    force_https = os.getenv('FORCE_HTTPS', 'true').lower() == 'true'
    allow_http = os.getenv('ALLOW_HTTP', 'false').lower() == 'true'
    scheme = 'https' if force_https or not allow_http else 'http'
    host = os.getenv('XERO_REDIRECT_HOST', 'localhost')
    return f"{scheme}://{host}:{port}/callback"

app.config['XERO_REDIRECT_URI'] = os.getenv('XERO_REDIRECT_URI', _build_xero_redirect_uri())

# Initialize enhanced session configuration
session_config = configure_flask_sessions(app)

# This will be properly configured after we set up the Xero client

# Initialize setup wizard API
setup_wizard_api = SetupWizardAPI()

# Enable CORS for setup API routes to support cross-origin wizard usage (e.g., file:// or different host)
if CORS is not None:
    # Allow any origin for the narrow setup API surface only
    CORS(app, resources={r"/api/setup/*": {"origins": "*"}}, supports_credentials=False)




def _apply_post_save_setup(result):
    """Update integration state after setup wizard finishes."""
    sync_credentials_to_env()
    global XERO_AVAILABLE, api_client, oauth, xero, session_config

    credentials = get_credentials_or_redirect()
    has_xero_credentials = bool(credentials.get('XERO_CLIENT_ID') and credentials.get('XERO_CLIENT_SECRET'))
    client = initialize_xero_client(credentials)

    if has_xero_credentials and client:
        result['xero_status'] = 'configured'
    elif has_xero_credentials:
        result['xero_status'] = 'saved_but_needs_restart'
        logger.warning('Xero configuration saved but client failed to initialize - restart may be required.')
    else:
        result['xero_status'] = 'skipped'

    has_stripe = bool(credentials.get('STRIPE_API_KEY'))
    demo_manager = globals().get('demo')
    if demo_manager and (has_xero_credentials or has_stripe):
        try:
            demo_manager.set_mode("live")
        except Exception as demo_error:  # pragma: no cover - logging only
            logger.debug(f'Demo mode update failed: {demo_error}')

    return result



def _xero_connection_payload():
    """Return persisted Xero connection status for the setup wizard UI."""
    tenant_id = get_tenant_id()
    has_token = has_stored_token()
    return {
        'connected': bool(has_token and tenant_id),
        'tenant_id': tenant_id or '',
        'has_token': bool(has_token),
    }


setup_api_bp = create_setup_blueprint(
    setup_wizard_api=setup_wizard_api,
    logger=logger,
    post_save_callback=_apply_post_save_setup,
    connection_status_provider=_xero_connection_payload,
)
app.register_blueprint(setup_api_bp, url_prefix='/api/setup')

# Initialize security manager if available
if SECURITY_ENABLED:
    security = SecurityManager()

# Import and setup Claude Desktop integration
try:
    from claude_integration import setup_claude_routes
    claude_setup_result = setup_claude_routes(app, logger)
    print("Claude Desktop integration loaded")
except ImportError as e:
    print(f"WARNING: Claude integration not available: {e}")
except Exception as e:
    print(f"WARNING: Claude integration setup failed: {e}")

# Import and setup Warp AI Terminal integration
try:
    from warp_integration import setup_warp_routes
    warp_setup_result = setup_warp_routes(app, logger)
    print("Warp AI Terminal integration loaded")
except ImportError as e:
    print(f"WARNING: Warp integration not available: {e}")
except Exception as e:
    print(f"WARNING: Warp integration setup failed: {e}")

# Import and setup ChatGPT integration
try:
    from chatgpt_integration import setup_chatgpt_routes
    chatgpt_setup_result = setup_chatgpt_routes(app, logger)
    print("ChatGPT integration loaded")
except ImportError as e:
    print(f"WARNING: ChatGPT integration not available: {e}")
except Exception as e:
    print(f"WARNING: ChatGPT integration setup failed: {e}")

# Import and setup Financial Command Center Assistant integration
try:
    from fcc_assistant_integration import setup_assistant_routes
    assistant_setup_result = setup_assistant_routes(app)
    print("Financial Command Center Assistant integration loaded")
except ImportError as e:
    print(f"WARNING: Financial Command Center Assistant integration not available: {e}")
except Exception as e:
    print(f"WARNING: Financial Command Center Assistant integration setup failed: {e}")

def get_credentials_or_redirect():
    """Get credentials from setup wizard or redirect to setup if not configured"""
    credentials = get_configured_credentials()
    
    # Override with environment variables if they exist (for backward compatibility)
    env_stripe_key = os.getenv('STRIPE_API_KEY')
    env_xero_client_id = os.getenv('XERO_CLIENT_ID')
    env_xero_client_secret = os.getenv('XERO_CLIENT_SECRET')
    env_plaid_client_id = os.getenv('PLAID_CLIENT_ID')
    env_plaid_secret = os.getenv('PLAID_SECRET')
    
    if env_stripe_key:
        credentials['STRIPE_API_KEY'] = env_stripe_key
    if env_xero_client_id:
        credentials['XERO_CLIENT_ID'] = env_xero_client_id
    if env_xero_client_secret:
        credentials['XERO_CLIENT_SECRET'] = env_xero_client_secret
    if env_plaid_client_id:
        credentials['PLAID_CLIENT_ID'] = env_plaid_client_id
    if env_plaid_secret:
        credentials['PLAID_SECRET'] = env_plaid_secret

    return credentials

def update_api_client_token(api_client, token):
    """Update API client with OAuth token"""
    if not api_client or not token:
        return api_client

    try:
        # Create a completely new API client with the token
        from xero_python.api_client import ApiClient, Configuration
        from xero_python.api_client.oauth2 import OAuth2Token

        # Create new OAuth2Token with client credentials
        oauth2_token = OAuth2Token(
            client_id=app.config['XERO_CLIENT_ID'],
            client_secret=app.config['XERO_CLIENT_SECRET']
        )

        # Set the token data directly on the token object
        oauth2_token.token = token

        # Create new API client with this token
        new_api_client = ApiClient(Configuration(oauth2_token=oauth2_token))

        # Set up token getter and saver functions
        @new_api_client.oauth2_token_getter
        def get_token():
            return token

        @new_api_client.oauth2_token_saver
        def save_token(new_token):
            if new_token:
                from xero_client import store_token
                store_token(new_token)

        logger.info("Successfully created new API client with token and handlers")
        return new_api_client

    except Exception as e:
        logger.error(f"Failed to create API client with token: {e}")
        return api_client


def has_active_xero_token():
    """Check whether a Xero OAuth token is available via session metadata or persistent storage."""
    try:
        if session.get('token_meta'):
            return True
    except RuntimeError:
        pass  # Outside request context
    try:
        return has_stored_token()
    except Exception as token_error:
        logger.debug(f"Token availability check failed: {token_error}")
        return False



def build_xero_setup_url(*, external: bool = False) -> str:
    """Return the setup wizard URL anchored to the Xero step."""
    base = url_for('setup_wizard', _external=external)
    return f"{base}#step3"


def redirect_to_xero_setup():
    """Redirect users to the Xero connection section of the wizard."""
    return redirect(build_xero_setup_url())


def initialize_xero_client(credentials=None):
    """Initialize Xero API client and attach OAuth session handlers."""
    global api_client, oauth, xero, session_config, XERO_AVAILABLE

    credentials = credentials or get_credentials_or_redirect()

    xero_client_id = credentials.get('XERO_CLIENT_ID')
    xero_client_secret = credentials.get('XERO_CLIENT_SECRET')

    if not xero_client_id or not xero_client_secret:
        XERO_AVAILABLE = False
        oauth = None
        xero = None
        return None

    try:
        app.config['XERO_CLIENT_ID'] = xero_client_id
        app.config['XERO_CLIENT_SECRET'] = xero_client_secret
        app.config['XERO_REDIRECT_URI'] = os.getenv('XERO_REDIRECT_URI', _build_xero_redirect_uri())

        oauth2_token = OAuth2Token(
            client_id=xero_client_id,
            client_secret=xero_client_secret,
        )

        api_client = ApiClient(Configuration(oauth2_token=oauth2_token))
        if session_config:
            session_config.configure_oauth_session_handlers(api_client)
        else:
            session_config = configure_flask_sessions(app, api_client)

        oauth, xero = init_oauth(app)
        XERO_AVAILABLE = True
        logger.info("Xero OAuth client initialized without restart requirement")
        return api_client
    except Exception as exc:
        logger.warning(f"Failed to initialize Xero client: {exc}")
        api_client = None
        oauth = None
        xero = None
        XERO_AVAILABLE = False
        return None

api_client = initialize_xero_client()
if XERO_AVAILABLE:
    print("Xero and enhanced session management initialized")
else:
    print("WARNING: Xero not configured - setup wizard required")

# Routes

@app.route('/')
def index():
    """Enhanced home page that checks setup status"""
    if is_setup_required() and not (os.getenv('XERO_CLIENT_ID') and os.getenv('STRIPE_API_KEY')):
        return redirect(url_for('setup_wizard'))

    integration_status = get_integration_status()

    nav_items = build_nav('overview')

    configured_integrations = sum(1 for data in integration_status.values() if data.get('configured'))
    total_integrations = len(integration_status)

    setup_pending = configured_integrations < total_integrations
    hero = {
        'title': 'Launch-ready financial operations cockpit',
        'description': 'Connect ledgers, payments, and AI copilots with a guided wizard built for enterprise demos.',
        'pill': {
            'label': 'Setup required' if setup_pending else 'Setup complete',
            'icon': 'clipboard-check' if setup_pending else 'sparkles',
        },
        'actions': [
            {
                'label': 'Launch setup wizard' if setup_pending else 'Review configuration',
                'href': url_for('setup_wizard'),
                'icon': 'sliders-horizontal',
                'variant': 'primary',
            },
            {
                'label': 'Open health view',
                'href': url_for('health_check'),
                'icon': 'activity',
                'variant': 'secondary',
            },
            {
                'label': 'Visit admin center',
                'href': url_for('admin_dashboard'),
                'icon': 'shield',
                'variant': 'ghost',
            },
        ],
        'points': [
            {
                'title': 'Guided connector onboarding',
                'description': 'Stripe, Xero, and Plaid credentials flow through a single wizard.',
                'icon': 'settings-2',
            },
            {
                'title': 'AI copilots on tap',
                'description': 'Wire Claude Desktop or Warp Terminal to orchestrate natural-language workflows.',
                'icon': 'bot',
            },
        ],
    }

    def integration_card(name: str, label: str, info: dict, description: str, actions: list) -> dict:
        status_label = 'Not configured'
        status_icon = 'circle'
        status_tone = 'info'
        if info.get('configured'):
            status_label = 'Configured'
            status_icon = 'check'
            status_tone = 'success'
        elif info.get('available'):
            status_label = 'Credentials saved'
            status_icon = 'sparkles'
            status_tone = 'info'
        elif info.get('skipped'):
            status_label = 'Demo mode'
            status_icon = 'clock'
            status_tone = 'warning'
        return {
            'category': 'Integration',
            'title': label,
            'status_label': status_label,
            'status_icon': status_icon,
            'status_tone': status_tone,
            'description': description,
            'actions': actions,
        }

    integration_cards = [
        integration_card(
            'stripe',
            'Stripe payments',
            integration_status.get('stripe', {}),
            'Process demo payments and subscriptions with instant test data.',
            [{'label': 'Configure Stripe', 'href': url_for('setup_wizard'), 'icon': 'credit-card'}],
        ),
        integration_card(
            'plaid',
            'Plaid banking',
            integration_status.get('plaid', {}),
            'Connect bank feeds and monitor transactions in real time.',
            [{'label': 'Configure Plaid', 'href': url_for('setup_wizard'), 'icon': 'banknote'}],
        ),
        integration_card(
            'xero',
            'Xero accounting',
            integration_status.get('xero', {}),
            'Sync contacts, invoices, and profit & loss reporting.',
            [{'label': 'Connect Xero', 'href': url_for('login'), 'icon': 'link'}],
        ),
    ]

    integration_cards.extend(
        [
            {
                'category': 'AI',
                'title': 'Claude Desktop',
                'status_label': 'Available',
                'status_icon': 'bot',
                'status_tone': 'info',
                'description': 'Pair Claude Desktop with the Command Center for natural-language workflows.',
                'actions': [{'label': 'Setup Claude', 'href': '/claude/setup', 'icon': 'bot'}],
            },
            {
                'category': 'AI',
                'title': 'Warp Terminal',
                'status_label': 'Available',
                'status_icon': 'terminal',
                'status_tone': 'info',
                'description': 'Connect Warp to trigger compliance MCP commands hands-free.',
                'actions': [{'label': 'Setup Warp', 'href': '/warp/setup', 'icon': 'terminal'}],
            },
            {
                'category': 'AI',
                'title': 'ChatGPT',
                'status_label': 'Available',
                'status_icon': 'message-circle',
                'status_tone': 'success',
                'description': 'Enable natural language financial commands through ChatGPT Desktop.',
                'actions': [{'label': 'Connect ChatGPT', 'href': '/chatgpt/setup', 'icon': 'message-circle'}],
            },
        ]
    )

    stats = [
        {
            'label': 'Configured connectors',
            'value': f"{configured_integrations}/{total_integrations}",
            'description': 'Stripe, Plaid, and Xero ready for show-time demos.',
            'icon': 'plug',
        },
        {
            'label': 'AI copilots standing by',
            'value': '3',
            'description': 'Claude Desktop, Warp Terminal, and ChatGPT integrations ship with guides.',
            'icon': 'bot',
            'tone': 'info',
        },
        {
            'label': 'Environment',
            'value': 'Demo mode' if demo.is_demo else 'Live mode',
            'description': 'Switch any time from the admin area to showcase real data.',
            'icon': 'sparkles' if demo.is_demo else 'shield-check',
            'tone': 'warning' if demo.is_demo else 'success',
        },
    ]

    support_cards = [
        {
            'badge': 'Setup',
            'title': 'Launch checklist',
            'description': 'Track onboarding progress across every connector.',
            'icon': 'sliders-horizontal',
            'checklist_items': [
                {'label': 'Stripe', 'value': 'Configured' if integration_status.get('stripe', {}).get('configured') else 'Pending'},
                {'label': 'Xero', 'value': 'Connected' if integration_status.get('xero', {}).get('configured') else 'Authenticate'},
            ],
            'actions': [{'label': 'Open setup wizard', 'href': url_for('setup_wizard'), 'icon': 'sliders'}],
        },
    ]

    ai_callout = {
        'badge': 'AI copilots',
        'title': 'Bring Claude, Warp, and ChatGPT into your financial workflow',
        'description': 'Preview natural-language commands for compliance, reporting, and client updates backed by your live connectors.',
        'actions': [
            {'label': 'Setup Claude Desktop', 'href': '/claude/setup', 'icon': 'bot'},
            {'label': 'Setup Warp Terminal', 'href': '/warp/setup', 'icon': 'terminal'},
            {'label': 'Connect to ChatGPT', 'href': '/chatgpt/setup', 'icon': 'message-circle'},
        ],
        'tips': [
            '"Summarize today\'s Stripe payments"',
            '"Show overdue invoices for ACME"',
        ],
    }

    feature_highlights = [
        {
            'title': 'Guided credential management',
            'description': 'The setup wizard encrypts keys at rest and validates connections before launch.',
            'icon': 'key-round',
        },
        {
            'title': 'Financial data explorers',
            'description': 'Responsive views for contacts and invoices with instant filtering and status badges.',
            'icon': 'table',
        },
        {
            'title': 'SSL everywhere',
            'description': 'Local CA packages keep stakeholder demos trusted in modern browsers.',
            'icon': 'shield',
        },
    ]

    quick_links = [
        {
            'label': 'View Xero contacts',
            'description': 'Explore enriched contact cards with live search.',
            'href': url_for('view_xero_contacts'),
            'icon': 'users',
        },
        {
            'label': 'Review invoices',
            'description': 'Sort and filter invoices with payment status indicators.',
            'href': url_for('view_xero_invoices'),
            'icon': 'file-text',
        },
        {
            'label': 'SSL help center',
            'description': 'Share quick instructions to trust local certificates.',
            'href': '/admin/ssl-help',
            'icon': 'shield',
        },
    ]

    return render_template(
        'home.html',
        nav_items=nav_items,
        hero=hero,
        support_cards=support_cards,
        stats=stats,
        integration_cards=integration_cards,
        ai_callout=ai_callout,
        feature_highlights=feature_highlights,
        quick_links=quick_links,
    )
@app.route('/setup')
def setup_wizard():
    """Setup wizard main page"""
    nav_items = build_nav('setup')
    return render_template('setup_wizard.html', nav_items=nav_items)

@app.route('/api/xero/debug', methods=['GET'])
def debug_xero_status():
    """Debug Xero configuration status"""
    credentials = get_credentials_or_redirect()
    
    debug_info = {
        'XERO_AVAILABLE': XERO_AVAILABLE,
        'has_client_id': bool(credentials.get('XERO_CLIENT_ID')),
        'has_client_secret': bool(credentials.get('XERO_CLIENT_SECRET')),
        'flask_config_client_id': bool(app.config.get('XERO_CLIENT_ID')),
        'flask_config_client_secret': bool(app.config.get('XERO_CLIENT_SECRET')),
        'api_client_exists': api_client is not None,
        'oauth_exists': oauth is not None,
        'xero_exists': xero is not None,
        'setup_status': get_integration_status()
    }
    
    return jsonify(debug_info)

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

    token_meta = session.get('token_meta')

    current_tenant = session.get('tenant_id')

    store_error = None

    stored_token = {}

    try:

        from xero_client import get_stored_token

        stored_token = get_stored_token()

    except Exception as err:

        store_error = str(err)



    token_info = {

        'session_has_metadata': token_meta is not None,

        'stored_token_keys': list(stored_token.keys()) if isinstance(stored_token, dict) else [],

        'has_stored_token': bool(stored_token.get('access_token')) if isinstance(stored_token, dict) else False,

        'has_tenant_id': current_tenant is not None,

        'tenant_id': current_tenant,

        'store_error': store_error

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
    
    # Get demo mode status
    from demo_mode import DemoModeManager
    demo_manager = DemoModeManager()
    current_mode = demo_manager.get_mode()
    
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '3.0.0',
        'security': 'enabled' if SECURITY_ENABLED else 'disabled',
        'setup_wizard': 'enabled',
        'mode': current_mode,  # Add mode to health data
        'integrations': {
            'stripe': {
                'available': bool(credentials.get('STRIPE_API_KEY')),
                'configured': integration_status.get('stripe', {}).get('configured', False),
                'skipped': integration_status.get('stripe', {}).get('skipped', False)
            },
            'plaid': {
                'available': bool(credentials.get('PLAID_CLIENT_ID') and credentials.get('PLAID_SECRET')),
                'configured': integration_status.get('plaid', {}).get('configured', False),
                'skipped': integration_status.get('plaid', {}).get('skipped', False)
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
    
    if wants_json:
        return jsonify(health_data)

    simplified_integrations = {}
    for name, info in health_data['integrations'].items():
        if isinstance(info, dict):
            if info.get('configured'):
                simplified_integrations[name] = 'configured'
            elif info.get('available'):
                simplified_integrations[name] = 'available'
            elif info.get('skipped'):
                simplified_integrations[name] = 'demo'
            else:
                simplified_integrations[name] = 'missing'
        else:
            simplified_integrations[name] = str(info)

    health_for_ui = dict(health_data)
    health_for_ui['integrations'] = simplified_integrations

    return render_health_dashboard(
        health_for_ui,
        security_enabled=SECURITY_ENABLED,
        session_config=session_config,
    )


@app.route('/login')
def login():
    """Xero OAuth login - only if configured"""
    logger.info(f"Login attempt - XERO_AVAILABLE: {XERO_AVAILABLE}")
    
    if not XERO_AVAILABLE:
        # Check if credentials exist but weren't loaded
        credentials = get_credentials_or_redirect()
        if credentials.get('XERO_CLIENT_ID') and credentials.get('XERO_CLIENT_SECRET'):
            logger.warning("Xero credentials exist but XERO_AVAILABLE is False - try restarting the app")
            return jsonify({
                'error': 'Xero configured but not loaded',
                'message': 'Please restart the application to load Xero configuration',
                'setup_url': url_for('setup_wizard', _external=True)
            }), 400
        
        return jsonify({
            'error': 'Xero not configured',
            'message': 'Complete setup wizard first',
            'setup_url': build_xero_setup_url(external=True)
        }), 400
    
    try:
        logger.info("Initiating Xero OAuth redirect")
        redirect_uri = app.config.get('XERO_REDIRECT_URI', _build_xero_redirect_uri())
        logger.info(f"Using redirect URI: {redirect_uri}")
        return xero.authorize_redirect(redirect_uri=redirect_uri)
    except Exception as e:
        logger.error(f"Error during Xero OAuth redirect: {e}")
        return jsonify({
            'error': 'OAuth initialization failed',
            'message': str(e),
            'details': 'Check your Xero app configuration and redirect URI'
        }), 500

@app.route('/callback')
def callback():
    """Xero OAuth callback with enhanced error handling"""
    if not XERO_AVAILABLE:
        return "Xero not configured. Complete setup wizard first.", 400
        
    try:
        from flask import request as flask_request
        logger.info(f"OAuth callback received with args: {dict(flask_request.args)}")
        
        # For development, we can bypass state validation if needed
        # The state mismatch often happens due to Flask restarts during development
        try:
            token = xero.authorize_access_token()
        except Exception as auth_error:
            if "mismatching_state" in str(auth_error) or "CSRF Warning" in str(auth_error):
                logger.warning(f"State mismatch detected, attempting without state validation: {auth_error}")
                # Try to get token manually without state check
                from authlib.integrations.flask_client.apps import FlaskOAuth2App
                from authlib.oauth2.rfc6749 import OAuth2Error
                
                # Get authorization code from request
                code = flask_request.args.get('code')
                if not code:
                    raise OAuth2Error('Missing authorization code')
                
                # Exchange code for token manually
                token_endpoint = 'https://identity.xero.com/connect/token'
                token_data = {
                    'grant_type': 'authorization_code',
                    'client_id': app.config['XERO_CLIENT_ID'],
                    'client_secret': app.config['XERO_CLIENT_SECRET'],
                    'code': code,
                    'redirect_uri': app.config.get('XERO_REDIRECT_URI', _build_xero_redirect_uri())
                }
                
                import requests
                import base64
                
                # Create basic auth header
                auth_string = f"{app.config['XERO_CLIENT_ID']}:{app.config['XERO_CLIENT_SECRET']}"
                auth_bytes = base64.b64encode(auth_string.encode('ascii'))
                auth_header = f"Basic {auth_bytes.decode('ascii')}"
                
                headers = {
                    'Authorization': auth_header,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                logger.info(f"Making token exchange request to {token_endpoint}")
                logger.info(f"Token data: {dict(token_data)}")

                response = requests.post(token_endpoint, data=token_data, headers=headers)
                logger.info(f"Token exchange response status: {response.status_code}")
                logger.info(f"Token exchange response: {response.text}")

                if response.status_code != 200:
                    logger.error(f'Token exchange failed with status {response.status_code}: {response.text}')
                    return "Authorization failed: Token exchange failed. Please check your Xero app configuration.", 400

                try:
                    token = response.json()
                    logger.info(f"Successfully parsed token with keys: {list(token.keys())}")
                except Exception as json_error:
                    logger.error(f"Failed to parse token response as JSON: {json_error}")
                    return "Authorization failed: Invalid token response format", 400
            else:
                raise auth_error
        
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
        
        # The enhanced session configuration handles token storage automatically via the API client token saver

        # Ensure the filtered token payload is available for downstream persistence

        allowed_fields = {

            "access_token", "refresh_token", "token_type",

            "expires_in", "expires_at", "scope", "id_token"

        }

        filtered_token = {k: v for k, v in token.items() if k in allowed_fields}

        try:

            session.permanent = True

            session.pop('token', None)

            session['token_meta'] = {

                'has_refresh_token': bool(filtered_token.get('refresh_token')),

                'stored_at': datetime.now().isoformat()

            }

            session.modified = True

            logger.info("OAuth token metadata stored for session")

        except Exception as token_error:

            logger.error(f"Failed to store token metadata: {token_error}")

            return f"Authorization failed: Token storage error: {str(token_error)}", 400



        # Get tenant information
        from xero_python.identity import IdentityApi
        try:
            # Validate filtered_token before using it
            if not filtered_token or not filtered_token.get('access_token'):
                logger.error(f"Invalid filtered_token: {filtered_token}")
                return "Authorization failed: Invalid access token received", 400

            logger.info(f"Updating API client with token containing: {list(filtered_token.keys())}")

            # Update the API client with the new token before using it
            global api_client
            api_client = update_api_client_token(api_client, filtered_token)
            
            identity = IdentityApi(api_client)
            conns = identity.get_connections()
            if not conns:
                return "No Xero organisations available for this user.", 400
            
            tenant_id = conns[0].tenant_id
            session['tenant_id'] = tenant_id
            logger.info(f"Connected to Xero tenant: {tenant_id}")
            
            # Save token and tenant using existing function
            save_token_and_tenant(filtered_token, tenant_id, app.config['XERO_CLIENT_ID'], app.config['XERO_CLIENT_SECRET'])
            
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
        # Return a simple error message to avoid validation issues
        return "Authorization failed: Please check the application logs for details", 400

@app.route('/profile')
def profile():
    """Xero profile page"""
    if not XERO_AVAILABLE:
        return redirect_to_xero_setup()

    if not has_active_xero_token():
        return redirect_to_xero_setup()
    if 'tenant_id' not in session:
        return "No tenant selected.", 400

    try:
        accounting = AccountingApi(api_client)
        accounts = accounting.get_accounts(session['tenant_id'])
        
        contacts = accounting.get_contacts(xero_tenant_id=session['tenant_id'])
        contacts_data = []
        for contact in (contacts.contacts or [])[:50]:
            contacts_data.append({
                'contact_id': getattr(contact, 'contact_id', 'N/A'),
                'name': getattr(contact, 'name', 'N/A') or 'N/A',
                'email': getattr(contact, 'email_address', 'N/A') or 'N/A',
                'phone': getattr(contact, 'phone_number', 'N/A') or 'N/A',
                'status': str(getattr(contact, 'contact_status', 'N/A')) if hasattr(contact, 'contact_status') else 'N/A',
                'is_supplier': bool(getattr(contact, 'is_supplier', False)),
                'is_customer': bool(getattr(contact, 'is_customer', False)),
            })
        
        stats = {
            'total': len(contacts_data),
            'customers': sum(1 for c in contacts_data if c['is_customer']),
            'suppliers': sum(1 for c in contacts_data if c['is_supplier']),
            'with_email': sum(1 for c in contacts_data if c['email'] and c['email'] != 'N/A'),
        }

        nav_items = build_nav('contacts')

        return render_template(
            'xero/contacts.html',
            nav_items=nav_items,
            contacts=contacts_data,
            stats=stats,
            tenant=session.get('tenant_id'),
        )
    except Exception as e:
        return f"Error fetching profile: {str(e)}", 500

@app.route('/logout')
def logout():
    """Logout from Xero"""
    session.pop('token', None)
    session.pop('token_meta', None)
    clear_token_and_tenant()
    session.pop('tenant_id', None)
    return redirect(url_for('index'))

# Web UI Endpoints for Xero Data

@app.route('/xero/contacts')
def view_xero_contacts():
    """Web UI for viewing Xero contacts"""
    if not XERO_AVAILABLE:
        return redirect_to_xero_setup()

    if not has_active_xero_token():
        return redirect_to_xero_setup()
    if 'tenant_id' not in session:
        return "No tenant selected. Please <a href='/login'>login again</a>.", 400

    try:
        from xero_python.accounting import AccountingApi
        accounting_api = AccountingApi(api_client)
        logger.info(f"Fetching contacts for tenant: {session['tenant_id']}")
        contacts = accounting_api.get_contacts(xero_tenant_id=session['tenant_id'])
        logger.info(f"Retrieved {len(contacts.contacts if contacts.contacts else [])} contacts")

        contacts_data = []
        for contact in (contacts.contacts or [])[:50]:
            contacts_data.append({
                'contact_id': getattr(contact, 'contact_id', 'N/A'),
                'name': getattr(contact, 'name', 'N/A') or 'N/A',
                'email': getattr(contact, 'email_address', 'N/A') or 'N/A',
                'phone': getattr(contact, 'phone_number', 'N/A') or 'N/A',
                'status': str(getattr(contact, 'contact_status', 'N/A')) if hasattr(contact, 'contact_status') else 'N/A',
                'is_supplier': bool(getattr(contact, 'is_supplier', False)),
                'is_customer': bool(getattr(contact, 'is_customer', False)),
            })

        stats = {
            'total': len(contacts_data),
            'customers': sum(1 for c in contacts_data if c['is_customer']),
            'suppliers': sum(1 for c in contacts_data if c['is_supplier']),
            'with_email': sum(1 for c in contacts_data if c['email'] and c['email'] != 'N/A'),
        }

        nav_items = build_nav('contacts')

        return render_template(
            'xero/contacts.html',
            nav_items=nav_items,
            contacts=contacts_data,
            stats=stats,
            tenant=session.get('tenant_id'),
        )

    except Exception as error:
        logger.error(f"Error fetching contacts: {error}")
        return f"Error fetching contacts: {error}", 500

@app.route('/xero/invoices')
def view_xero_invoices():
    """Web UI for viewing Xero invoices"""
    if not XERO_AVAILABLE:
        return redirect_to_xero_setup()

    if not has_active_xero_token():
        return redirect_to_xero_setup()
    if 'tenant_id' not in session:
        return "No tenant selected. Please <a href='/login'>login again</a>.", 400

    try:
        from xero_python.accounting import AccountingApi
        accounting_api = AccountingApi(api_client)
        status_filter = request.args.get('status', 'DRAFT,SUBMITTED,AUTHORISED')
        invoices = accounting_api.get_invoices(
            xero_tenant_id=session['tenant_id'],
            statuses=status_filter.split(','),
        )

        def _format_date(value):
            if not value:
                return None
            try:
                return value.strftime('%Y-%m-%d')
            except AttributeError:
                return str(value)

        invoices_data = []
        for invoice in (invoices.invoices or [])[:50]:
            invoice_type = str(getattr(invoice, 'type', 'N/A'))
            invoice_status = str(getattr(invoice, 'status', 'N/A'))
            currency = str(getattr(invoice, 'currency_code', 'USD'))
            contact_name = getattr(getattr(invoice, 'contact', None), 'name', 'N/A') or 'N/A'

            invoices_data.append({
                'invoice_id': getattr(invoice, 'invoice_id', 'N/A'),
                'invoice_number': getattr(invoice, 'invoice_number', 'N/A'),
                'type': invoice_type,
                'status': invoice_status,
                'total': float(getattr(invoice, 'total', 0) or 0),
                'currency_code': currency,
                'issued_date': _format_date(getattr(invoice, 'date', None)),
                'due_date': _format_date(getattr(invoice, 'due_date', None)),
                'contact_name': contact_name,
                'amount_due': float(getattr(invoice, 'amount_due', 0) or 0),
                'amount_paid': float(getattr(invoice, 'amount_paid', 0) or 0),
            })

        stats = {
            'count': len(invoices_data),
            'total_amount': sum(inv['total'] for inv in invoices_data),
            'total_due': sum(inv['amount_due'] for inv in invoices_data),
            'total_paid': sum(inv['amount_paid'] for inv in invoices_data),
        }

        nav_items = build_nav('invoices')

        return render_template(
            'xero/invoices.html',
            nav_items=nav_items,
            invoices=invoices_data,
            stats=stats,
            status_filter=status_filter,
        )

    except Exception as error:
        logger.error(f"Error fetching invoices: {error}")
        return f"Error fetching invoices: {error}", 500

@app.route('/api/xero/contacts', methods=['GET'])
@require_api_key
def get_xero_contacts():
    """Get Xero contacts - enhanced with setup wizard integration"""
    if not XERO_AVAILABLE:
        return jsonify({
            'error': 'Xero not configured',
            'message': 'Complete setup wizard first',
            'setup_url': build_xero_setup_url(external=True)
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
    """Admin dashboard using the shared Shadcn templates."""
    context = build_admin_dashboard_context(SECURITY_ENABLED, security if SECURITY_ENABLED else None, demo)
    nav_items = build_nav('admin')
    return render_template(
        'admin/dashboard.html',
        nav_items=nav_items,
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
            'snippet': f'curl -H "X-API-Key: {demo_key}" https://127.0.0.1:8000/api/ping',
        },
        {
            'title': 'Fetch Xero contacts',
            'snippet': f'curl -H "X-API-Key: {demo_key}" https://127.0.0.1:8000/api/xero/contacts',
        },
        {
            'title': 'Create demo payment',
            'snippet': (
                f"curl -X POST -H \"X-API-Key: {demo_key}\" -H \"Content-Type: application/json\" "
                f"-d '{{\"amount\": 25.50, \"description\": \"Test payment\"}}' "
                f"https://127.0.0.1:8000/api/stripe/payment"
            ),
        },
    ]

    nav_items = build_nav('admin')

    return render_template(
        'admin/demo_key.html',
        nav_items=nav_items,
        demo_key=demo_key,
        commands=commands,
    )


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
    """Get comprehensive financial dashboard data from real sources"""
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'
    
    if not wants_json:
        return "Dashboard endpoint - use Accept: application/json header", 400
    
    # Import the Xero dashboard function
    xero_data = {}
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
            # Determine environment based on PLAID_ENV or default to Sandbox
            plaid_env = os.getenv("PLAID_ENV", "Sandbox")
            env_map = {
                "Sandbox": plaid.Environment.Sandbox,
                "Development": plaid.Environment.Development,
                "Production": plaid.Environment.Production
            }
            host = env_map.get(plaid_env, plaid.Environment.Sandbox)
            
            cfg = plaid.Configuration(
                host=host,
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

@app.route('/api/export/excel', methods=['GET'])
def export_financial_data_excel():
    """Export financial data to Excel format"""
    try:
        from flask import send_file
        from financial_export import create_financial_excel_export

        # Create Excel file
        excel_data = create_financial_excel_export()

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'financial_export_{timestamp}.xlsx'

        return send_file(
            excel_data,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate Excel export',
            'message': str(e)
        }), 500

@app.route('/api/dashboard/charts', methods=['GET'])
def get_dashboard_chart_data():
    """Get real Xero data formatted for dashboard charts"""
    try:
        from financial_export import fetch_xero_financial_data

        # Fetch real Xero data
        xero_data = fetch_xero_financial_data()

        if "error" in xero_data:
            return jsonify({
                'error': xero_data["error"],
                'chart_data': None
            }), 400

        # Process data for charts
        chart_data = {}

        # Revenue by Customer Chart Data
        if xero_data.get('invoices'):
            revenue_by_customer = {}
            for invoice in xero_data['invoices']:
                customer = invoice.get('Contact_Name', 'Unknown')
                total = invoice.get('Total', 0)
                if customer in revenue_by_customer:
                    revenue_by_customer[customer] += total
                else:
                    revenue_by_customer[customer] = total

            # Sort by revenue and take top 10
            sorted_revenue = sorted(revenue_by_customer.items(), key=lambda x: x[1], reverse=True)[:10]
            chart_data['revenue_by_customer'] = [
                {'name': customer, 'value': revenue} for customer, revenue in sorted_revenue
            ]

        # Invoice Status Distribution
        if xero_data.get('invoices'):
            status_counts = {}
            for invoice in xero_data['invoices']:
                status = invoice.get('Status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1

            chart_data['invoice_status'] = [
                {'name': status, 'value': count} for status, count in status_counts.items()
            ]

        # Monthly Revenue Trend (based on invoice dates)
        if xero_data.get('invoices'):
            monthly_revenue = {}
            for invoice in xero_data['invoices']:
                date_str = invoice.get('Date', '')
                total = invoice.get('Total', 0)
                if date_str:
                    try:
                        invoice_date = datetime.strptime(date_str, '%Y-%m-%d')
                        month_key = invoice_date.strftime('%Y-%m')
                        monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + total
                    except ValueError:
                        continue

            # Sort by month and prepare for chart
            sorted_months = sorted(monthly_revenue.items())
            chart_data['monthly_revenue'] = [
                {'month': month, 'revenue': revenue} for month, revenue in sorted_months
            ]

        # Outstanding vs Paid Amounts
        if xero_data.get('invoices'):
            total_outstanding = sum(inv.get('Amount_Due', 0) for inv in xero_data['invoices'])
            total_paid = sum(inv.get('Total', 0) - inv.get('Amount_Due', 0) for inv in xero_data['invoices'])

            chart_data['payment_status'] = [
                {'name': 'Outstanding', 'value': total_outstanding},
                {'name': 'Paid', 'value': total_paid}
            ]

        # Account Types Distribution
        if xero_data.get('accounts'):
            account_types = {}
            for account in xero_data['accounts']:
                acc_type = account.get('Type', 'Unknown')
                account_types[acc_type] = account_types.get(acc_type, 0) + 1

            chart_data['account_types'] = [
                {'name': acc_type, 'value': count} for acc_type, count in account_types.items()
            ]

        # Customer vs Supplier Breakdown
        if xero_data.get('contacts'):
            customer_count = sum(1 for contact in xero_data['contacts'] if contact.get('Is_Customer'))
            supplier_count = sum(1 for contact in xero_data['contacts'] if contact.get('Is_Supplier'))

            chart_data['contact_types'] = [
                {'name': 'Customers', 'value': customer_count},
                {'name': 'Suppliers', 'value': supplier_count}
            ]

        return jsonify({
            'success': True,
            'chart_data': chart_data,
            'data_timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': 'Failed to generate chart data',
            'message': str(e)
        }), 500

@app.route('/dashboard/charts')
def financial_charts_dashboard():
    """Render the financial charts dashboard page"""
    nav_items = build_nav('dashboard')

    # Check if user is connected to Xero
    try:
        from xero_client import has_stored_token, get_tenant_id

        xero_connected = has_stored_token() and get_tenant_id()

        return render_template('dashboard/financial_charts.html',
                             nav_items=nav_items,
                             xero_connected=xero_connected)
    except Exception as e:
        # If there's any error checking Xero status, assume not connected
        return render_template('dashboard/financial_charts.html',
                             nav_items=nav_items,
                             xero_connected=False)

if __name__ == '__main__':
    print("Starting Financial Command Center with Setup Wizard...")
    print("=" * 60)
    print(f"Security: {'Enabled' if SECURITY_ENABLED else 'Disabled'}")
    print(f"Setup Wizard: Enabled")
    print(f"Xero: {'Available' if XERO_AVAILABLE else 'Needs Configuration'}")
    
    credentials = get_credentials_or_redirect()
    print(f"Stripe: {'Configured' if credentials.get('STRIPE_API_KEY') else 'Needs Setup'}")
    
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
    
    print()
    print("Available endpoints:")
    print("  GET  / - Smart home page (redirects to setup if needed)")
    print("  GET  /setup - Professional setup wizard")
    print("  GET  /health - Enhanced health check")
    
    if SECURITY_ENABLED:
        print("  Security Endpoints: /api/ping, /api/create-key, /api/key-stats")
    
    print("  Admin: /admin/dashboard")
    print("  Stripe: /api/stripe/payment")
    print("  SSL Help: /admin/ssl-help")
    print("  Certificate Bundle: /admin/certificate-bundle")
    print("Claude Desktop: /claude/setup, /api/claude/*, /api/mcp")
    print("Financial Command Center Assistant: /assistant/*")
    
    if XERO_AVAILABLE:
        print("  Xero: /login, /callback, /profile, /api/xero/contacts, /api/xero/invoices")
    else:
        print("  Xero: Configure via setup wizard")
    
    print()
    protocol = "https" if ssl_context else "http"
    # Allow launcher to select/override port
    import os as _os
    port = int(_os.getenv('FCC_PORT') or _os.getenv('PORT') or '8000')
    print("URLs:")
    print(f"  Home: {protocol}://127.0.0.1:{port}/")
    print(f"  Setup: {protocol}://127.0.0.1:{port}/setup")
    print(f"  Admin: {protocol}://127.0.0.1:{port}/admin/dashboard")
    print(f"  SSL Help: {protocol}://127.0.0.1:{port}/admin/ssl-help")
    print()
    
    if is_setup_required() and not os.getenv('STRIPE_API_KEY'):
        print("FIRST TIME SETUP:")
        print(f"   Visit {protocol}://127.0.0.1:{port}/setup to configure your integrations")
        print(f"   Or {protocol}://127.0.0.1:{port}/ to start the guided setup")
        print()
    
    print(f"Server Mode: {server_mode}")
    if ssl_context and ssl_context != 'adhoc':
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
    print("Professional Financial Command Center ready!")
    
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
    # Fallback hard wrap
    if getattr(sys.stdout, 'encoding', '').lower() != 'utf-8' and hasattr(sys.stdout, 'buffer'):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if getattr(sys.stderr, 'encoding', '').lower() != 'utf-8' and hasattr(sys.stderr, 'buffer'):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass









