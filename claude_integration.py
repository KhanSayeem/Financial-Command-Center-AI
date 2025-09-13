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
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: #f5f7fa; 
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 300;
            margin: 0;
            margin-bottom: 10px;
        }
        
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        
        .setup-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .step-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            color: #333;
        }
        
        .step-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            font-weight: 600;
            margin-right: 15px;
            color: white;
        }
        
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            transition: all 0.3s ease;
            cursor: pointer;
            border: none;
            margin: 5px;
        }
        
        .btn:hover {
            background: #5a6fd8;
        }
        
        .btn-primary {
            background: #667eea;
        }
        
        .btn-success {
            background: #27ae60;
        }
        
        .btn-success:hover {
            background: #229954;
        }
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
        
        .alert-success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        
        .alert-info {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #1e40af;
        }
        
        .alert-warning {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: #b45309;
        }
        
        .command-example {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            color: #155724;
        }
        
        .important-step {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin: 10px 0;
            text-align: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            border: 2px solid rgba(255, 255, 255, 0.1);
        }
        
        .important-step h3 {
            margin: 0 0 10px 0;
            color: #ffffff !important;
            font-weight: 700;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            font-size: 1.1em;
        }
        
        .important-step p {
            margin: 0;
            color: #ffffff !important;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            font-size: 1.05em;
            letter-spacing: 0.5px;
        }
        
        code {
            background: rgba(0,0,0,0.1);
            padding: 4px 8px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
        }
        
        ol {
            margin-left: 20px;
            margin-top: 10px;
        }
        
        .setup-card p {
            color: #666;
            line-height: 1.6;
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
                Generate MCP Server Configuration
            </div>
            <p>Click below to automatically generate your Claude Desktop configuration:</p>
            <br>
            <button class="btn btn-primary" onclick="generateConfig()">📄 Generate Config</button>
            <button class="btn btn-success" onclick="downloadConfig()" id="downloadBtn" style="display:none;">💾 Download Config</button>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">2</span>
                Download and Install Claude Desktop
            </div>
            <p>If you don't have Claude Desktop installed yet:</p>
            <div class="alert alert-info">
                <strong>📥 Download Claude Desktop:</strong><br>
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
                <strong>📁 Place the downloaded config file here:</strong><br><br>
                <strong>Windows:</strong><br>
                <code>%APPDATA%\\Claude\\claude_desktop_config.json</code><br><br>
                <strong>macOS:</strong><br>
                <code>~/Library/Application Support/Claude/claude_desktop_config.json</code><br><br>
                <strong>Linux:</strong><br>
                <code>~/.config/Claude/claude_desktop_config.json</code>
            </div>
            <div class="alert alert-success">
                <strong>💡 Easy Installation:</strong><br>
                1. Open File Explorer / Finder<br>
                2. Navigate to the folder above<br>
                3. Create the "Claude" folder if it doesn't exist<br>
                4. Copy your downloaded file and rename it to "claude_desktop_config.json"
            </div>
        </div>
        
        <div class="setup-card">
            <div class="step-title">
                <span class="step-number">4</span>
                Restart Claude Desktop
            </div>
            <div style="text-align: center; margin: 20px 0;">
                <div class="important-step">
                    <h3>⚠️ Important Step</h3>
                    <p>Close Claude Desktop completely and reopen it</p>
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
                <span class="step-number">5</span>
                Try Sample Commands
            </div>
            <div class="alert alert-success">
                <strong>🎉 Once connected, try these AI commands in Claude Desktop:</strong>
            </div>
            
            <div class="command-example">
                <strong>💰 "Show me our cash flow this month"</strong><br>
                <em>Get real-time financial overview with current balances and trends</em>
            </div>
            
            <div class="command-example">
                <strong>🧾 "List all unpaid invoices over $1000"</strong><br>
                <em>Instantly filter and display high-value outstanding payments</em>
            </div>
            
            <div class="command-example">
                <strong>👥 "Find contact details for [Customer Name]"</strong><br>
                <em>Quick customer lookup with complete contact information</em>
            </div>
            
            <div class="command-example">
                <strong>📊 "Check system health and integrations"</strong><br>
                <em>Monitor all connected services and identify any issues</em>
            </div>
        </div>
        
        <div class="setup-card" style="text-align: center;">
            <h3>🚀 Ready to Continue?</h3>
            <p>Once you've completed the setup above, your Claude Desktop integration will be ready!</p>
            <div style="margin-top: 20px;">
                <a href="/admin/dashboard" class="btn btn-primary">📊 Admin Dashboard</a>
                <a href="/" class="btn">🏠 Home</a>
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
                    
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-success';
                    alert.innerHTML = '✅ Configuration generated! Click Download to save it.';
                    document.querySelector('.setup-card').appendChild(alert);
                }
            } catch (error) {
                alert('Failed to generate configuration: ' + error);
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
        """Generate Claude Desktop MCP configuration"""
        try:
            # Get current server configuration
            port = int(os.getenv('FCC_PORT', '8000'))
            server_url = f"https://localhost:{port}"
            
            # Generate configuration
            # Get the absolute path to the MCP server
            current_dir = os.path.dirname(os.path.abspath(__file__))
            mcp_server_path = os.path.join(current_dir, "mcp_server.py")
            python_exe = os.path.join(current_dir, ".venv", "Scripts", "python.exe")
            
            # Check if virtual environment Python exists, otherwise use system Python
            if not os.path.exists(python_exe):
                python_exe = "python"
            
            config = {
                "mcpServers": {
                    "financial-command-center": {
                        "command": python_exe,
                        "args": [mcp_server_path],
                        "env": {
                            "FCC_SERVER_URL": server_url,
                            "FCC_API_KEY": "claude-desktop-integration"
                        }
                    }
                }
            }
            
            config_json = json.dumps(config, indent=2)
            
            return jsonify({
                'success': True,
                'config': config_json,
                'server_url': server_url,
                'message': 'Configuration generated successfully'
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