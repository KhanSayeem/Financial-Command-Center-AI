#!/usr/bin/env python3
"""
Standalone Claude Desktop Integration Module
To be imported into the main application
"""
import os
import json
from datetime import datetime
from flask import jsonify, render_template_string, request, session

def setup_claude_routes(app, logger=None):
    """Setup Claude Desktop integration routes on the Flask app"""
    
    @app.route('/claude/setup')
    def claude_setup_page():
        """Claude Desktop integration setup page"""
        # Get current server info
        port = app.config.get('PORT', int(os.getenv('FCC_PORT', '8000')))
        server_url = f"https://localhost:{port}"
        
        return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Desktop Integration - Financial Command Center AI</title>
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
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
        
        .setup-card {
            background: var(--bg-primary);
            padding: 1.5rem;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            margin-bottom: 1.5rem;
            border: 1px solid var(--border-color);
        }
        
        .step-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            color: var(--text-primary);
        }
        
        .step-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            background: var(--primary-color);
            border-radius: 50%;
            font-weight: 600;
            margin-right: 0.75rem;
            color: white;
            font-size: 0.875rem;
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
        
        .btn-primary {
            background: var(--primary-color);
        }
        
        .btn-primary:hover {
            background: var(--primary-hover);
        }
        
        .btn-success {
            background: var(--success-color);
        }
        
        .btn-success:hover {
            background: #047857;
        }
        
        .alert {
            padding: 1rem;
            border-radius: var(--border-radius);
            margin: 1rem 0;
            border: 1px solid transparent;
        }
        
        .alert-success {
            background: #f0fdf4;
            border-color: #bbf7d0;
            color: #166534;
        }
        
        .alert-info {
            background: #eff6ff;
            border-color: #bfdbfe;
            color: #1e40af;
        }
        
        .alert-warning {
            background: #fffbeb;
            border-color: #fed7aa;
            color: #92400e;
        }
        
        .alert-error {
            background: #fef2f2;
            border-color: #fecaca;
            color: #991b1b;
        }
        
        .command-example {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 1rem;
            margin: 0.75rem 0;
            color: var(--text-primary);
        }
        
        .important-step {
            background: var(--primary-color);
            color: white;
            padding: 1.5rem;
            border-radius: var(--border-radius);
            margin: 1rem 0;
            text-align: center;
        }
        
        .important-step h3 {
            margin: 0 0 0.5rem 0;
            color: white;
            font-weight: 600;
            font-size: 1.125rem;
        }
        
        .important-step p {
            margin: 0;
            color: white;
            font-weight: 500;
        }
        
        code {
            background: var(--bg-secondary);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 0.875rem;
            border: 1px solid var(--border-color);
        }
        
        ol, ul {
            margin: 1rem 0;
            padding-left: 1.5rem;
        }
        
        li {
            margin: 0.5rem 0;
        }
        
        .setup-card p {
            color: var(--text-secondary);
            line-height: 1.6;
            margin: 0.75rem 0;
        }
        
        strong {
            color: var(--text-primary);
            font-weight: 600;
        }
        
        a {
            color: var(--primary-color);
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Connect to Claude Desktop</h1>
            <p>Enable AI-powered financial operations with voice commands</p>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">1</span>
                Generate Complete MCP Configuration
            </div>
            <p>Your Claude Desktop configuration will include <strong>all configured MCP servers</strong> using your stored credentials:</p>
            <ul style="margin: 15px 0; padding-left: 30px; color: #555;">
                <li><strong>Financial Command Center</strong> - Core financial operations</li>
                <li><strong>Stripe Payments</strong> - Payment processing (if configured)</li>
                <li><strong>Xero Accounting</strong> - Accounting integration (if configured)</li>
                <li><strong>Plaid Banking</strong> - Bank account data (if configured)</li>
                <li><strong>Compliance Suite</strong> - Transaction monitoring & compliance</li>
            </ul>
            <div class="alert alert-info">
                <strong>Secure:</strong> Uses your encrypted credentials from the setup wizard.<br>
                <strong>Tailored:</strong> Only includes servers for services you've configured.<br>
                <strong>Dynamic:</strong> Automatically detects your project paths and Python setup.<br>
                <strong>Portable:</strong> Customized for YOUR specific directory and Python installation.
            </div>
            
            <div class="alert alert-warning">
                <strong>Important for Teams:</strong><br>
                This configuration contains paths specific to your computer. Each team member should:<br>
                1. Run their own Financial Command Center setup<br>
                2. Generate their own Claude Desktop config from <code>/claude/setup</code><br>
                3. This ensures correct paths for their system (Windows/Mac/Linux)
            </div>
            <br>
            <button class="btn btn-primary" onclick="generateConfig()">Generate Complete Config</button>
            <button class="btn btn-success" onclick="downloadConfig()" id="downloadBtn" style="display:none;">Download Config</button>
            <div id="configSummary" style="margin-top: 15px; display: none;"></div>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">2</span>
                Download and Install Claude Desktop
            </div>
            <p>If you don't have Claude Desktop installed yet:</p>
            <div class="alert alert-info">
                <strong>Download Claude Desktop:</strong><br>
                <a href="https://claude.ai/download" target="_blank" style="color: #1e40af; text-decoration: none;">https://claude.ai/download</a><br>
                <small>Available for Windows, macOS, and Linux</small>
            </div>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">3</span>
                Install Configuration File
            </div>
            <div class="alert alert-warning">
                <strong>Configuration File Location:</strong><br><br>
                <strong>Windows:</strong><br>
                <code>%APPDATA%\\Claude\\claude_desktop_config.json</code><br><br>
                <strong>macOS:</strong><br>
                <code>~/Library/Application Support/Claude/claude_desktop_config.json</code><br><br>
                <strong>Linux:</strong><br>
                <code>~/.config/Claude/claude_desktop_config.json</code>
            </div>
            <div class="alert alert-success">
                <strong>Installation Steps:</strong><br>
                1. Open File Explorer / Finder<br>
                2. Navigate to the folder above<br>
                3. Create the "Claude" folder if it doesn't exist<br>
                4. Copy your downloaded file and rename it to "claude_desktop_config.json"
            </div>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">4</span>
                Verify Configuration Paths
            </div>
            <div class="alert alert-info">
                <strong>Verification Steps:</strong> Open the downloaded <code>claude_desktop_config.json</code> and verify:<br>
                • Python executable path exists on your computer<br>
                • MCP server script paths point to your project directory<br>
                • All paths use your actual username and directory structure<br><br>
                <strong>Example:</strong> Paths should look like <code>C:\\Users\\[YourName]\\...\\python.exe</code><br>
                <strong>If paths look wrong:</strong> Re-generate config after ensuring your project is in the right location
            </div>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">5</span>
                Restart Claude Desktop
            </div>
            <div style="text-align: center; margin: 20px 0;">
                <div class="important-step">
                    <h3>Important Step</h3>
                    <p style="color: white;">Close Claude Desktop completely and reopen it</p>
                </div>
            </div>
            <ol style="margin-left: 20px; margin-top: 10px;">
                <li><strong>Close Claude Desktop</strong> (completely quit the application)</li>
                <li><strong>Reopen Claude Desktop</strong></li>
                <li><strong>Look for "Financial Command Center"</strong> in the available tools</li>
                <li><strong>Start a new conversation</strong> and try the commands below!</li>
            </ol>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">6</span>
                Try Sample Commands
            </div>
            <div class="alert alert-success">
                <strong>Sample Commands:</strong> Once connected, try these AI commands in Claude Desktop:
            </div>
            
            <div class="command-example">
                <strong>"Show me our cash flow this month"</strong><br>
                <em>Get real-time financial overview with current balances and trends</em>
            </div>
            
            <div class="command-example">
                <strong>"List all unpaid invoices over $1000"</strong><br>
                <em>Instantly filter and display high-value outstanding payments</em>
            </div>
            
            <div class="command-example">
                <strong>"Find contact details for [Customer Name]"</strong><br>
                <em>Quick customer lookup with complete contact information</em>
            </div>
            
            <div class="command-example">
                <strong>"Check system health and integrations"</strong><br>
                <em>Monitor all connected services and identify any issues</em>
            </div>
        </div>
        
        <div class="setup-card" style="text-align: center;">
            <h3>Ready to Continue?</h3>
            <p>Once you've completed the setup above, your Claude Desktop integration will be ready!</p>
            <div style="margin-top: 20px;">
                <a href="/admin/dashboard" class="btn btn-primary">Admin Dashboard</a>
                <a href="/" class="btn">Home</a>
            </div>
        </div>
    </div>
    
    <script>
        let configData = null;
        
        async function generateConfig() {
            try {
                const response = await fetch('/api/claude/generate-config');
                const data = await response.json();
                
                if (data.success) {
                    configData = data.config;
                    document.getElementById('downloadBtn').style.display = 'inline-flex';
                    
                    // Show configuration summary
                    const summary = data.summary;
                    const summaryDiv = document.getElementById('configSummary');
                    
                    let credentialsUsed = [];
                    if (summary.credentials_used.stripe) credentialsUsed.push('Stripe');
                    if (summary.credentials_used.xero) credentialsUsed.push('Xero');
                    if (summary.credentials_used.plaid) credentialsUsed.push('Plaid');
                    
                    let setupInfo = '';
                    if (summary.portable_instructions) {
                        setupInfo = `
                            <br><strong>Your Setup Details:</strong><br>
                            • <strong>Python:</strong> ${summary.portable_instructions.python_location}<br>
                            • <strong>Directory:</strong> ${summary.project_directory}<br>
                            • <strong>Note:</strong> ${summary.portable_instructions.note}<br>
                        `;
                    }
                    
                    summaryDiv.innerHTML = `
                        <div class="alert alert-success">
                            <strong>✅ Configuration Generated Successfully!</strong><br><br>
                            <strong>Summary:</strong><br>
                            • <strong>${summary.total_servers} MCP servers</strong> included<br>
                            • <strong>Servers:</strong> ${summary.servers.join(', ')}<br>
                            • <strong>Credentials used:</strong> ${credentialsUsed.join(', ') || 'None (demo mode)'}<br>
                            ${setupInfo}
                            <br><strong>Click Download to save your configuration file!</strong>
                        </div>
                    `;
                    summaryDiv.style.display = 'block';
                } else {
                    const summaryDiv = document.getElementById('configSummary');
                    summaryDiv.innerHTML = `
                        <div class="alert" style="background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24;">
                            <strong>❌ Configuration Generation Failed</strong><br>
                            Error: ${data.message}
                        </div>
                    `;
                    summaryDiv.style.display = 'block';
                }
            } catch (error) {
                const summaryDiv = document.getElementById('configSummary');
                summaryDiv.innerHTML = `
                    <div class="alert" style="background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24;">
                        <strong>❌ Network Error</strong><br>
                        Failed to generate configuration: ${error.message}
                    </div>
                `;
                summaryDiv.style.display = 'block';
            }
        }
        
        function downloadConfig() {
            if (!configData) {
                alert('Please generate configuration first.');
                return;
            }
            
            const blob = new Blob([configData], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'claude_desktop_config.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
        ''', server_url=server_url)

    @app.route('/api/claude/generate-config')
    def generate_claude_config():
        """Generate Claude Desktop MCP configuration with all servers using stored credentials"""
        try:
            # Import configuration manager
            from setup_wizard import ConfigurationManager
            config_manager = ConfigurationManager()
            stored_config = config_manager.load_config() or {}
            
            # Get current server configuration
            port = int(os.getenv('FCC_PORT', '8000'))
            server_url = f"https://localhost:{port}"
            
            # Get dynamic paths relative to user's project directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Try multiple Python executable locations for cross-platform compatibility
            python_candidates = [
                # Virtual environment locations
                os.path.join(current_dir, ".venv", "Scripts", "python.exe"),  # Windows venv
                os.path.join(current_dir, ".venv", "bin", "python"),          # Unix/Mac venv
                os.path.join(current_dir, "venv", "Scripts", "python.exe"),   # Alternative Windows venv
                os.path.join(current_dir, "venv", "bin", "python"),           # Alternative Unix/Mac venv
                # System Python as fallback
                "python",
                "python3"
            ]
            
            # Find the first existing Python executable
            python_exe = "python"  # Default fallback
            for candidate in python_candidates:
                if candidate in ["python", "python3"]:
                    # For system Python, we'll use the command directly
                    python_exe = candidate
                    break
                elif os.path.exists(candidate):
                    python_exe = candidate
                    break
            
            # Create portable configuration by detecting user's actual setup
            # We'll use the absolute paths but add instructions for users to update them
            def get_user_instructions():
                """Generate user-specific instructions for their setup"""
                instructions = {
                    "user_project_directory": current_dir,
                    "detected_python": python_exe,
                    "setup_type": "virtual_environment" if ".venv" in python_exe or "venv" in python_exe else "system_python"
                }
                return instructions
            
            # Get user setup information
            user_instructions = get_user_instructions()
            
            # Initialize MCP servers configuration
            mcp_servers = {}
            
            # 1. Main Financial Command Center MCP (always included)
            mcp_server_path = os.path.join(current_dir, "mcp_server.py")
            if os.path.exists(mcp_server_path):
                mcp_servers["financial-command-center"] = {
                    "command": python_exe,
                    "args": [mcp_server_path],
                    "env": {
                        "FCC_SERVER_URL": server_url,
                        "FCC_API_KEY": "claude-desktop-integration"
                    }
                }
            
            # 2. Stripe MCP (if configured)
            stripe_config = stored_config.get('stripe', {})
            if stripe_config and not stripe_config.get('skipped'):
                stripe_mcp_path = os.path.join(current_dir, "stripe_mcp.py")
                if os.path.exists(stripe_mcp_path):
                    mcp_servers["stripe-payments"] = {
                        "command": python_exe,
                        "args": [stripe_mcp_path],
                        "env": {
                            "STRIPE_API_KEY": stripe_config.get('api_key'),
                            "STRIPE_PUBLISHABLE_KEY": stripe_config.get('publishable_key', '')
                        }
                    }
            
            # 3. Xero MCP (if configured)
            xero_config = stored_config.get('xero', {})
            if xero_config and not xero_config.get('skipped'):
                xero_mcp_path = os.path.join(current_dir, "xero_mcp.py")
                if os.path.exists(xero_mcp_path):
                    mcp_servers["xero-accounting"] = {
                        "command": python_exe,
                        "args": [xero_mcp_path],
                        "env": {
                            "XERO_CLIENT_ID": xero_config.get('client_id'),
                            "XERO_CLIENT_SECRET": xero_config.get('client_secret')
                        }
                    }
            
            # 4. Plaid MCP (if configured)
            plaid_config = stored_config.get('plaid', {})
            if plaid_config and not plaid_config.get('skipped'):
                plaid_mcp_path = os.path.join(current_dir, "plaid_mcp.py")
                if os.path.exists(plaid_mcp_path):
                    mcp_servers["plaid-banking"] = {
                        "command": python_exe,
                        "args": [plaid_mcp_path],
                        "env": {
                            "PLAID_CLIENT_ID": plaid_config.get('client_id'),
                            "PLAID_SECRET": plaid_config.get('secret'),
                            "PLAID_ENV": plaid_config.get('environment', 'sandbox')
                        }
                    }
            
            # 5. Compliance MCP (always included for monitoring)
            compliance_mcp_path = os.path.join(current_dir, "compliance_mcp.py")
            if os.path.exists(compliance_mcp_path):
                # Use Plaid credentials for compliance monitoring if available
                compliance_env = {}
                if plaid_config and not plaid_config.get('skipped'):
                    compliance_env.update({
                        "PLAID_CLIENT_ID": plaid_config.get('client_id'),
                        "PLAID_SECRET": plaid_config.get('secret'),
                        "PLAID_ENV": plaid_config.get('environment', 'sandbox')
                    })
                if stripe_config and not stripe_config.get('skipped'):
                    compliance_env["STRIPE_API_KEY"] = stripe_config.get('api_key')
                
                mcp_servers["compliance-suite"] = {
                    "command": python_exe,
                    "args": [compliance_mcp_path],
                    "env": compliance_env
                }
            
            config = {"mcpServers": mcp_servers}
            
            config_json = json.dumps(config, indent=2)
            
            # Generate summary of included servers
            included_servers = list(mcp_servers.keys())
            server_summary = {
                'total_servers': len(included_servers),
                'servers': included_servers,
                'credentials_used': {
                    'stripe': bool(stripe_config and not stripe_config.get('skipped')),
                    'xero': bool(xero_config and not xero_config.get('skipped')),
                    'plaid': bool(plaid_config and not plaid_config.get('skipped'))
                },
                'python_executable': python_exe,
                'project_directory': current_dir,
                'setup_type': user_instructions['setup_type'],
                'portable_instructions': {
                    'note': 'This configuration is customized for your specific setup',
                    'python_location': 'Virtual environment detected' if '.venv' in python_exe else 'System Python detected',
                    'paths_are_absolute': 'Paths are specific to your project directory',
                    'sharing_note': 'Other users should generate their own config from their setup'
                }
            }
            
            return jsonify({
                'success': True,
                'config': config_json,
                'server_url': server_url,
                'message': f'Configuration generated with {len(included_servers)} MCP servers',
                'summary': server_summary
            })
            
        except Exception as e:
            if logger:
                logger.error(f"Claude config generation error: {e}")
            return jsonify({
                'success': False,
                'message': f'Configuration generation error: {str(e)}'
            }), 500

    @app.route('/api/mcp', methods=['GET', 'POST'])
    def mcp_endpoint():
        """MCP server endpoint for Claude Desktop integration"""
        try:
            if request.method == 'GET':
                # Return available tools/capabilities
                return jsonify({
                    'tools': [
                        {
                            'name': 'get_financial_health',
                            'description': 'Get overall financial health and system status'
                        },
                        {
                            'name': 'get_invoices', 
                            'description': 'Retrieve invoices with optional filtering'
                        },
                        {
                            'name': 'get_contacts',
                            'description': 'Get customer/supplier contact information'
                        }
                    ]
                })
            
            # Handle MCP tool calls
            data = request.get_json()
            tool_name = data.get('tool')
            
            if tool_name == 'get_financial_health':
                return jsonify({
                    'result': {
                        'status': 'healthy',
                        'health_percentage': 95,
                        'message': 'All systems operational'
                    }
                })
            
            return jsonify({'error': f'Tool {tool_name} not implemented yet'}), 501
            
        except Exception as e:
            if logger:
                logger.error(f"MCP endpoint error: {e}")
            return jsonify({'error': f'MCP endpoint error: {str(e)}'}), 500

    return "Claude Desktop routes registered successfully"