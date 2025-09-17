
import json
import os
from pathlib import Path
from typing import Dict, Tuple

from flask import jsonify, render_template

from ui.helpers import build_nav

def setup_warp_routes(app, logger=None):
    """Setup Warp AI Terminal integration routes on the Flask app."""

    @app.route('/warp/setup')
    def warp_setup_page():
        port = app.config.get('PORT', int(os.getenv('FCC_PORT', '8000')))
        server_url = f"https://localhost:{port}"
        nav_items = build_nav('setup')

        return render_template(
            'integrations/warp_setup.html',
            server_url=server_url,
            nav_items=nav_items,
        )

    @app.route('/api/warp/generate-config', methods=['GET'])
    def generate_warp_config():
        try:
            config_json, summary, server_url = _build_warp_config(app)
            return jsonify({
                'success': True,
                'config': config_json,
                'summary': summary,
                'server_url': server_url,
                'message': f"Configuration generated with {summary['total_servers']} MCP servers",
            })
        except Exception as exc:
            if logger:
                logger.error(f"Warp config generation error: {exc}")
            return jsonify({
                'success': False,
                'message': f"Configuration generation error: {exc}",
            }), 500

    return True

def _build_warp_config(app) -> Tuple[str, Dict[str, object], str]:
    """Generate the Warp MCP configuration payload."""
    from setup_wizard import ConfigurationManager

    config_manager = ConfigurationManager()
    stored_config = config_manager.load_config() or {}

    port = app.config.get('PORT', int(os.getenv('FCC_PORT', '8000')))
    server_url = f"https://localhost:{port}"

    base_dir = Path(__file__).resolve().parent
    python_exe = _detect_python_executable(base_dir)

    mcp_servers: Dict[str, Dict[str, object]] = {}

    def _add_server(key: str, script_name: str, env: Dict[str, object]):
        script_path = base_dir / script_name
        if script_path.exists():
            mcp_servers[key] = {
                'command': python_exe,
                'args': [str(script_path)],
                'env': {k: v for k, v in env.items() if v not in (None, '')},
                'working_directory': None,
            }

    _add_server(
        'financial-command-center-warp',
        'mcp_server_warp.py',
        {
            'FCC_SERVER_URL': server_url,
            'FCC_API_KEY': 'claude-desktop-integration',
        },
    )

    stripe_config = stored_config.get('stripe', {})
    if stripe_config and not stripe_config.get('skipped'):
        _add_server(
            'stripe-integration-warp',
            'stripe_mcp_warp.py',
            {
                'STRIPE_API_KEY': stripe_config.get('api_key'),
                'STRIPE_API_VERSION': stripe_config.get('api_version', '2024-06-20'),
                'STRIPE_DEFAULT_CURRENCY': stripe_config.get('default_currency', 'usd'),
                'MCP_STRIPE_PROD': 'true' if stripe_config.get('mode') == 'live' else 'false',
            },
        )

    plaid_config = stored_config.get('plaid', {})
    if plaid_config and not plaid_config.get('skipped'):
        _add_server(
            'plaid-integration-warp',
            'plaid_mcp_warp.py',
            {
                'PLAID_CLIENT_ID': plaid_config.get('client_id'),
                'PLAID_SECRET': plaid_config.get('secret'),
                'PLAID_ENV': plaid_config.get('environment', 'sandbox'),
            },
        )

    xero_config = stored_config.get('xero', {})
    if xero_config and not xero_config.get('skipped'):
        _add_server(
            'xero-integration-warp',
            'xero_mcp_warp.py',
            {
                'XERO_CLIENT_ID': xero_config.get('client_id'),
                'XERO_CLIENT_SECRET': xero_config.get('client_secret'),
            },
        )

    compliance_env: Dict[str, object] = {}
    if plaid_config and not plaid_config.get('skipped'):
        compliance_env.update({
            'PLAID_CLIENT_ID': plaid_config.get('client_id'),
            'PLAID_SECRET': plaid_config.get('secret'),
            'PLAID_ENV': plaid_config.get('environment', 'sandbox'),
        })
    if stripe_config and not stripe_config.get('skipped'):
        compliance_env['STRIPE_API_KEY'] = stripe_config.get('api_key')

    _add_server(
        'compliance-suite-warp',
        'compliance_mcp_warp.py',
        compliance_env,
    )

    config_json = json.dumps({'mcpServers': mcp_servers}, indent=2)

    included_servers = list(mcp_servers.keys())
    setup_type = 'virtual_environment' if 'venv' in python_exe else 'system_python'

    summary = {
        'total_servers': len(included_servers),
        'servers': included_servers,
        'credentials_used': {
            'stripe': bool(stripe_config and not stripe_config.get('skipped')),
            'xero': bool(xero_config and not xero_config.get('skipped')),
            'plaid': bool(plaid_config and not plaid_config.get('skipped')),
        },
        'python_executable': python_exe,
        'project_directory': str(base_dir),
        'setup_type': setup_type,
        'portable_instructions': {
            'note': 'This configuration is customized for your specific setup',
            'python_location': 'Virtual environment detected' if 'venv' in python_exe else 'System Python detected',
            'paths_are_absolute': 'Paths are specific to your project directory',
            'sharing_note': 'Other users should generate their own config from their setup',
        },
    }

    return config_json, summary, server_url

def _detect_python_executable(base_dir: Path) -> str:
    """Return the best python executable path for the current environment."""
    import shutil

    candidates = [
        base_dir / '.venv' / 'Scripts' / 'python.exe',
        base_dir / '.venv' / 'bin' / 'python',
        base_dir / 'venv' / 'Scripts' / 'python.exe',
        base_dir / 'venv' / 'bin' / 'python',
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    for executable in ('python', 'python3'):
        resolved_path = shutil.which(executable)
        if resolved_path:
            return resolved_path

    return 'python'
