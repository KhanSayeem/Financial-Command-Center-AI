"""
ChatGPT Integration Module for Financial Command Center AI
Enables natural language financial commands through ChatGPT Desktop
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional, Any
import requests

from flask import jsonify, render_template, request
from ui.helpers import build_nav

# Add fcc-openai-adapter to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fcc-openai-adapter'))

def setup_chatgpt_routes(app, logger=None):
    """Setup ChatGPT integration routes on the Flask app."""
    
    @app.route('/chatgpt/setup')
    def chatgpt_setup_page():
        port = app.config.get('PORT', int(os.getenv('FCC_PORT', '8000')))
        server_url = f"https://localhost:{port}"
        nav_items = build_nav('setup')

        return render_template(
            'integrations/chatgpt_setup.html',
            server_url=server_url,
            nav_items=nav_items,
        )

    @app.route('/api/chatgpt/config', methods=['GET'])
    def get_chatgpt_config():
        """Get current ChatGPT configuration status."""
        try:
            # Check if we have a stored API key
            config_path = Path(__file__).parent / 'secure_config' / 'chatgpt_config.json'
            configured = config_path.exists()
            
            return jsonify({
                'success': True,
                'configured': configured,
                'message': 'ChatGPT configuration status retrieved'
            })
        except Exception as exc:
            if logger:
                logger.error(f"ChatGPT config status error: {exc}")
            return jsonify({
                'success': False,
                'message': f"Configuration status error: {exc}",
            }), 500

    @app.route('/api/chatgpt/connect', methods=['POST'])
    def connect_chatgpt():
        """Connect ChatGPT with the provided API key."""
        try:
            data = request.get_json()
            api_key = data.get('openai_api_key')
            
            if not api_key:
                return jsonify({
                    'success': False,
                    'message': 'OpenAI API key is required'
                }), 400
            
            # Validate API key by making a simple request to OpenAI
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Test the API key with a simple models request
            response = requests.get(
                'https://api.openai.com/v1/models/gpt-4o',
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                return jsonify({
                    'success': False,
                    'message': 'Invalid OpenAI API key or insufficient permissions'
                }), 400
            
            # Store the API key securely
            config_path = Path(__file__).parent / 'secure_config'
            config_path.mkdir(exist_ok=True)
            
            config_file = config_path / 'chatgpt_config.json'
            config_data = {
                'openai_api_key': api_key,
                'created_at': __import__('datetime').datetime.now().isoformat()
            }
            
            config_file.write_text(json.dumps(config_data, indent=2))
            
            # Build configuration summary
            config_json, summary, server_url = _build_chatgpt_config(app)
            
            return jsonify({
                'success': True,
                'config': config_json,
                'summary': summary,
                'server_url': server_url,
                'message': f"ChatGPT connected successfully with {summary['total_servers']} MCP servers",
            })
        except Exception as exc:
            if logger:
                logger.error(f"ChatGPT connection error: {exc}")
            return jsonify({
                'success': False,
                'message': f"Connection error: {exc}",
            }), 500

    @app.route('/api/chatgpt/test', methods=['POST'])
    def test_chatgpt_connection():
        """Test the ChatGPT connection."""
        try:
            # Load the stored API key
            config_path = Path(__file__).parent / 'secure_config' / 'chatgpt_config.json'
            if not config_path.exists():
                return jsonify({
                    'success': False,
                    'message': 'ChatGPT not configured. Please connect first.'
                }), 400
            
            config_data = json.loads(config_path.read_text())
            api_key = config_data.get('openai_api_key')
            
            if not api_key:
                return jsonify({
                    'success': False,
                    'message': 'OpenAI API key not found in configuration'
                }), 400
            
            # Test the API key
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                'https://api.openai.com/v1/models/gpt-4o',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return jsonify({
                    'success': True,
                    'message': 'ChatGPT connection test successful! API key is valid.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'ChatGPT connection test failed: {response.status_code} - {response.text}'
                }), 400
                
        except Exception as exc:
            if logger:
                logger.error(f"ChatGPT test error: {exc}")
            return jsonify({
                'success': False,
                'message': f"Connection test error: {exc}",
            }), 500

    @app.route('/api/chatgpt/disconnect', methods=['POST'])
    def disconnect_chatgpt():
        """Disconnect ChatGPT by removing the stored API key."""
        try:
            config_path = Path(__file__).parent / 'secure_config' / 'chatgpt_config.json'
            if config_path.exists():
                config_path.unlink()
            
            return jsonify({
                'success': True,
                'message': 'ChatGPT disconnected successfully'
            })
        except Exception as exc:
            if logger:
                logger.error(f"ChatGPT disconnect error: {exc}")
            return jsonify({
                'success': False,
                'message': f"Disconnect error: {exc}",
            }), 500

    return True

def _build_chatgpt_config(app) -> Tuple[str, Dict[str, object], str]:
    """Generate the ChatGPT integration configuration."""
    from setup_wizard import ConfigurationManager
    
    port = app.config.get('PORT', int(os.getenv('FCC_PORT', '8000')))
    server_url = f"https://localhost:{port}"
    
    # Determine which MCP servers are available
    servers = []
    credentials_used = {}
    
    # Check Xero availability
    try:
        from xero_client import has_stored_token
        if has_stored_token():
            servers.append('xero')
            credentials_used['xero_client_id'] = bool(os.getenv('XERO_CLIENT_ID'))
    except ImportError:
        pass
    
    # Check Stripe availability
    if os.getenv('STRIPE_API_KEY'):
        servers.append('stripe')
        credentials_used['stripe_api_key'] = True
    
    # Check Plaid availability
    if os.getenv('PLAID_CLIENT_ID') and os.getenv('PLAID_SECRET'):
        servers.append('plaid')
        credentials_used['plaid_client_id'] = True
        credentials_used['plaid_secret'] = True
    
    # Check Compliance availability
    servers.append('compliance')
    
    # Check Financial Command Center availability
    servers.append('financial_command_center')
    
    # Check Automation availability
    servers.append('automation')
    
    config_summary = {
        'servers': servers,
        'total_servers': len(servers),
        'credentials_used': credentials_used,
        'python_executable': sys.executable,
    }
    
    # Create the configuration JSON
    config_json = json.dumps({
        'name': 'Financial Command Center AI',
        'description': 'Natural language financial commands through ChatGPT',
        'servers': servers,
        'endpoint': server_url,
        'auth_header': 'X-API-Key',
        'auth_type': 'api_key'
    }, indent=2)
    
    return config_json, config_summary, server_url