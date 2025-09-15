#!/usr/bin/env python3
"""
Standalone Warp AI Terminal Integration Module
To be imported into the main application
"""
import os
import json
from datetime import datetime
from flask import jsonify, render_template_string, request, session

def setup_warp_routes(app, logger=None):
    """Setup Warp AI Terminal integration routes on the Flask app"""
    
    @app.route('/warp/setup')
    def warp_setup_page():
        """Warp AI Terminal integration setup page"""
        # Get current server info
        port = app.config.get('PORT', int(os.getenv('FCC_PORT', '8000')))
        server_url = f"https://localhost:{port}"
        
        return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Warp AI Terminal Integration - Financial Command Center AI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <style>
        /* Root variables for consistent color scheme */
        :root {
            --primary-color: #6366f1;
            --primary-hover: #5b21b6;
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
            --warp-purple: #6366f1;
            --warp-purple-hover: #5b21b6;
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
            background: linear-gradient(135deg, var(--warp-purple) 0%, var(--warp-purple-hover) 100%);
            color: white;
            padding: 2rem;
            border-radius: var(--border-radius);
            margin-bottom: 2rem;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"><g fill="none" fill-rule="evenodd"><g fill="%23ffffff" fill-opacity="0.1"><circle cx="30" cy="30" r="2"/></g></svg>');
            opacity: 0.3;
        }
        
        .header h1 {
            font-size: 2rem;
            font-weight: 600;
            margin: 0 0 0.5rem 0;
            position: relative;
            z-index: 1;
        }
        
        .header .subtitle {
            margin: 0;
            opacity: 0.9;
            font-size: 1.1rem;
            position: relative;
            z-index: 1;
        }
        
        .warp-icon {
            display: inline-block;
            margin-right: 0.5rem;
            font-size: 1.2em;
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
            background: var(--warp-purple);
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
            background: var(--warp-purple);
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
            background: var(--warp-purple-hover);
            transform: translateY(-1px);
        }
        
        .btn-primary {
            background: var(--warp-purple);
        }
        
        .btn-primary:hover {
            background: var(--warp-purple-hover);
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
            font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 0.9rem;
        }
        
        .important-step {
            background: var(--warp-purple);
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
            color: var(--warp-purple);
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        
        .feature-card {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 1rem;
            text-align: center;
        }
        
        .feature-icon {
            font-size: 2rem;
            color: var(--warp-purple);
            margin-bottom: 0.5rem;
        }
        
        .warp-logo {
            font-weight: 700;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-terminal warp-icon"></i>Connect to <span class="warp-logo">Warp</span> AI Terminal</h1>
            <p class="subtitle">Enable AI-powered financial operations through the terminal</p>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">1</span>
                Generate Complete Warp MCP Configuration
            </div>
            <p>Your Warp AI Terminal configuration will include <strong>all configured MCP servers</strong> using your stored credentials:</p>
            
            <div class="feature-grid">
                <div class="feature-card">
                    <div class="feature-icon"><i class="fas fa-chart-line"></i></div>
                    <strong>Financial Command Center</strong><br>
                    <small>Core financial operations</small>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"><i class="fab fa-stripe"></i></div>
                    <strong>Stripe Payments</strong><br>
                    <small>Payment processing</small>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"><i class="fas fa-university"></i></div>
                    <strong>Plaid Banking</strong><br>
                    <small>Bank account data</small>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"><i class="fas fa-calculator"></i></div>
                    <strong>Xero Accounting</strong><br>
                    <small>Accounting integration</small>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"><i class="fas fa-shield-alt"></i></div>
                    <strong>Compliance Suite</strong><br>
                    <small>Transaction monitoring</small>
                </div>
            </div>
            
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
                2. Generate their own Warp MCP config from <code>/warp/setup</code><br>
                3. This ensures correct paths for their system (Windows/Mac/Linux)
            </div>
            <br>
            <button class="btn btn-primary" onclick="generateConfig()">
                Generate Complete Config
            </button>
            <button class="btn btn-success" onclick="downloadConfig()" id="downloadBtn" style="display:none;">
                Download Config
            </button>
            <div id="configSummary" style="margin-top: 15px; display: none;"></div>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">2</span>
                Install or Update Warp Terminal
            </div>
            <p>Make sure you have the latest version of Warp with AI features enabled:</p>
            <div class="alert alert-info">
                <strong>Download Warp Terminal:</strong><br>
                <a href="https://www.warp.dev/" target="_blank">https://www.warp.dev/</a><br>
                <small>Available for macOS, Linux, and Windows</small>
            </div>
            
            <div class="alert alert-warning">
                <strong>AI Features Required:</strong><br>
                Ensure your Warp installation includes AI terminal features and MCP support.<br>
                Some features may require Warp Pro or specific versions.
            </div>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">3</span>
                Configure Warp MCP Integration
            </div>
            
            <p>There are two ways to integrate with Warp:</p>
            
            <div class="alert alert-success">
                <strong>Option A: Automatic Discovery (Recommended)</strong><br>
                1. Place the downloaded config file in your project directory<br>
                2. Warp will automatically discover and load the MCP servers<br>
                3. Look for "Financial Command Center" tools in Warp AI features
            </div>
            
            <div class="alert alert-info">
                <strong>Option B: Manual Configuration</strong><br>
                1. Open Warp Terminal settings<br>
                2. Navigate to AI/MCP settings<br>
                3. Add the MCP servers individually using the generated configuration<br>
                4. Ensure all paths and environment variables are correct
            </div>
            
            <div class="command-example">
# Example: Test MCP server connectivity in Warp
cd "{{ user_project_directory }}"
python mcp_server_warp.py  # Test main server
python stripe_mcp_warp.py  # Test Stripe integration
            </div>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">4</span>
                Verify Configuration and Paths
            </div>
            <div class="alert alert-info">
                <strong>Configuration Verification:</strong> Open the downloaded <code>warp_mcp_config.json</code> and verify:<br>
                • Python executable path exists on your computer<br>
                • MCP server script paths point to your project directory<br>
                • All environment variables are properly set<br>
                • Server names match Warp's expected format<br><br>
                <strong>Example:</strong> Paths should look like <code>C:\\Users\\[YourName]\\...\\python.exe</code><br>
                <strong>If paths look wrong:</strong> Re-generate config after ensuring your project is in the right location
            </div>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">5</span>
                Test Warp AI Integration
            </div>
            <div style="text-align: center; margin: 20px 0;">
                <div class="important-step">
                    <h3>Ready to Test</h3>
                    <p style="color: white;">Open Warp Terminal and try AI-powered financial commands</p>
                </div>
            </div>
            
            <div class="alert alert-success">
                <strong>Sample Commands to Try in Warp AI:</strong>
            </div>
            
            <div class="command-example">
                <h4 style="margin-top: 0; color: var(--text-primary);">Financial Health Check</h4>
                <p>"Show me our current financial health and system status"</p>
                
                <h4 style="color: var(--text-primary);">Invoice Management</h4>
                <p>"List all unpaid invoices over $1000 from Xero"</p>
                
                <h4 style="color: var(--text-primary);">Payment Processing</h4>
                <p>"Process a $50 test payment through Stripe"</p>
                
                <h4 style="color: var(--text-primary);">Banking Data</h4>
                <p>"Get account balances from all connected Plaid accounts"</p>
                
                <h4 style="color: var(--text-primary);">Compliance Monitoring</h4>
                <p>"Scan recent transactions for compliance issues"</p>
            </div>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">6</span>
                Advanced Warp Features
            </div>
            
            <div class="alert alert-info">
                <strong>Pro Tips for Warp AI:</strong><br>
                • Use natural language - Warp AI understands context<br>
                • Chain multiple commands together<br>
                • Ask for explanations of financial data<br>
                • Set up custom workflows and aliases<br>
                • Monitor real-time financial metrics
            </div>
            
            <div class="feature-grid">
                <div class="feature-card">
                    <div class="feature-icon"><i class="fas fa-robot"></i></div>
                    <strong>Natural Language</strong><br>
                    <small>Ask questions in plain English</small>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"><i class="fas fa-link"></i></div>
                    <strong>Command Chaining</strong><br>
                    <small>Combine multiple operations</small>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"><i class="fas fa-chart-pie"></i></div>
                    <strong>Live Insights</strong><br>
                    <small>Real-time financial data</small>
                </div>
                <div class="feature-card">
                    <div class="feature-icon"><i class="fas fa-cogs"></i></div>
                    <strong>Custom Workflows</strong><br>
                    <small>Automate repetitive tasks</small>
                </div>
            </div>
        </div>
        
        <div class="setup-card" style="text-align: center;">
            <h3>Ready to Revolutionize Your Terminal?</h3>
            <p>Once configured, your Warp AI Terminal will have direct access to all your financial data and operations!</p>
            <div style="margin-top: 20px;">
                <a href="/admin/dashboard" class="btn btn-primary">
                    Admin Dashboard
                </a>
                <a href="/claude/setup" class="btn" style="background: #2563eb;">
                    Claude Desktop Setup
                </a>
                <a href="/" class="btn">
                    Home
                </a>
            </div>
        </div>
    </div>
    
    <script>
        let configData = null;
        
        async function generateConfig() {
            try {
                const response = await fetch('/api/warp/generate-config');
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
                            • <strong>Warp Integration:</strong> ${summary.portable_instructions.warp_note}<br>
                        `;
                    }
                    
                    summaryDiv.innerHTML = `
                        <div class="alert alert-success">
                            <strong>Warp MCP Configuration Generated Successfully!</strong><br><br>
                            <strong>Summary:</strong><br>
                            • <strong>${summary.total_servers} MCP servers</strong> configured for Warp<br>
                            • <strong>Servers:</strong> ${summary.servers.join(', ')}<br>
                            • <strong>Credentials used:</strong> ${credentialsUsed.join(', ') || 'None (demo mode)'}<br>
                            ${setupInfo}
                            <br><strong>Click Download to save your Warp configuration file!</strong>
                        </div>
                    `;
                    summaryDiv.style.display = 'block';
                } else {
                    const summaryDiv = document.getElementById('configSummary');
                    summaryDiv.innerHTML = `
                        <div class="alert alert-error">
                            <strong>Configuration Generation Failed</strong><br>
                            Error: ${data.message}
                        </div>
                    `;
                    summaryDiv.style.display = 'block';
                }
            } catch (error) {
                const summaryDiv = document.getElementById('configSummary');
                summaryDiv.innerHTML = `
                    <div class="alert alert-error">
                        <strong>Network Error</strong><br>
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
            a.download = 'warp_mcp_config.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
        ''', server_url=server_url)

    @app.route('/api/warp/generate-config')
    def generate_warp_config():
        """Generate Warp AI Terminal MCP configuration with all servers using stored credentials"""
        try:
            # Import configuration manager
            from setup_wizard import ConfigurationManager
            config_manager = ConfigurationManager()
            stored_config = config_manager.load_config() or {}
            
            # Get current server configuration
            port = int(os.getenv('FCC_PORT', '8000'))
            server_url = f"https://localhost:{port}"
            
            # Use project-relative paths that work for any user's download location
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Use simple "python" command like the working config
            python_exe = "python"
            
            # Use MCPServers directory within the project (portable for all users)
            mcp_servers_dir = os.path.join(current_dir, "MCPServers").replace('\\', '/')
            
            # Create portable configuration for Warp
            def get_user_instructions():
                """Generate user-specific instructions for their setup"""
                instructions = {
                    "user_project_directory": current_dir,
                    "detected_python": python_exe,
                    "setup_type": "virtual_environment" if ".venv" in python_exe or "venv" in python_exe else "system_python",
                    "warp_integration": "direct_mcp_discovery"
                }
                return instructions
            
            # Get user setup information
            user_instructions = get_user_instructions()
            
            # Initialize Warp MCP servers configuration (using Warp's expected format)
            warp_servers = {}
            
            # Helper function to get script path (use project MCPServers directory)
            def get_script_path(script_name):
                # Ensure we use the _warp.py version of the script
                if not script_name.endswith("_warp.py"):
                    script_name = script_name.replace(".py", "_warp.py")
                
                # Create path to MCPServers directory within project
                full_mcp_path = f"{mcp_servers_dir}/{script_name}"
                
                # Check if file exists (for validation during development)
                local_file_path = os.path.join(current_dir, "MCPServers", script_name)
                if os.path.exists(local_file_path):
                    return full_mcp_path
                else:
                    # Return path anyway - user might have moved files
                    return full_mcp_path
            
            # 1. Main Financial Command Center MCP (always included)
            fcc_script = get_script_path("mcp_server_warp.py")
            if fcc_script:
                warp_servers["financial-command-center-warp"] = {
                    "command": python_exe,
                    "args": [fcc_script],
                    "working_directory": None,
                    "env": {
                        "FCC_SERVER_URL": server_url,
                        "FCC_API_KEY": "claude-desktop-integration"
                    }
                }
            
            # 2. Stripe MCP (if configured)
            stripe_config = stored_config.get('stripe', {})
            if stripe_config and not stripe_config.get('skipped'):
                stripe_script = get_script_path("stripe_mcp_warp.py")
                if stripe_script:
                    warp_servers["stripe-integration-warp"] = {
                        "command": python_exe,
                        "args": [stripe_script],
                        "working_directory": None,
                        "env": {
                            "STRIPE_API_KEY": stripe_config.get('api_key'),
                            "STRIPE_API_VERSION": "2024-06-20",
                            "STRIPE_DEFAULT_CURRENCY": "usd",
                            "MCP_STRIPE_PROD": "false"
                        }
                    }
            
            # 3. Plaid MCP (if configured)
            plaid_config = stored_config.get('plaid', {})
            if plaid_config and not plaid_config.get('skipped'):
                plaid_script = get_script_path("plaid_mcp_warp.py")
                if plaid_script:
                    warp_servers["plaid-integration-warp"] = {
                        "command": python_exe,
                        "args": [plaid_script],
                        "working_directory": None,
                        "env": {
                            "PLAID_CLIENT_ID": plaid_config.get('client_id'),
                            "PLAID_SECRET": plaid_config.get('secret'),
                            "PLAID_ENV": plaid_config.get('environment', 'sandbox')
                        }
                    }
            
            # 4. Xero MCP (if configured)
            xero_config = stored_config.get('xero', {})
            if xero_config and not xero_config.get('skipped'):
                xero_script = get_script_path("xero_mcp_warp.py")
                if xero_script:
                    warp_servers["xero-mcp-warp"] = {
                        "command": python_exe,
                        "args": [xero_script],
                        "working_directory": None,
                        "env": {
                            "XERO_CLIENT_ID": xero_config.get('client_id'),
                            "XERO_CLIENT_SECRET": xero_config.get('client_secret')
                        }
                    }
            
            # 5. Compliance MCP (always included for monitoring)
            compliance_script = get_script_path("compliance_mcp_warp.py")
            if compliance_script:
                # Use available credentials for compliance monitoring
                compliance_env = {}
                if plaid_config and not plaid_config.get('skipped'):
                    compliance_env.update({
                        "PLAID_CLIENT_ID": plaid_config.get('client_id'),
                        "PLAID_SECRET": plaid_config.get('secret'),
                        "PLAID_ENV": plaid_config.get('environment', 'sandbox')
                    })
                if stripe_config and not stripe_config.get('skipped'):
                    compliance_env["STRIPE_API_KEY"] = stripe_config.get('api_key')
                
                warp_servers["compliance-suite-warp"] = {
                    "command": python_exe,
                    "args": [compliance_script],
                    "working_directory": None,
                    "env": compliance_env
                }
            
            # Create the final configuration in Warp's expected format
            warp_config = {
                "mcpServers": warp_servers
            }
            
            config_json = json.dumps(warp_config, indent=2)
            
            # Generate summary of included servers
            included_servers = list(warp_servers.keys())
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
                    'warp_note': 'Configuration optimized for Warp AI Terminal MCP integration',
                    'python_location': 'Virtual environment detected' if '.venv' in python_exe else 'System Python detected',
                    'paths_are_absolute': 'Paths are specific to your project directory',
                    'sharing_note': 'Other users should generate their own config from their setup'
                }
            }
            
            return jsonify({
                'success': True,
                'config': config_json,
                'server_url': server_url,
                'message': f'Warp MCP configuration generated with {len(included_servers)} servers',
                'summary': server_summary
            })
            
        except Exception as e:
            if logger:
                logger.error(f"Warp config generation error: {e}")
            return jsonify({
                'success': False,
                'message': f'Configuration generation error: {str(e)}'
            }), 500

    return "Warp AI Terminal routes registered successfully"