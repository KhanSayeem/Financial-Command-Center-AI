#!/usr/bin/env python3
"""
Server Mode Manager for Financial Command Center AI
Handles HTTP/HTTPS modes with professional warnings and upgrade prompts
"""

import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from datetime import datetime


class ServerModeManager:
    """Manages server modes (HTTP/HTTPS) with professional warnings"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.force_https = os.getenv('FORCE_HTTPS', 'false').lower() == 'true'
        self.allow_http = os.getenv('ALLOW_HTTP', 'true').lower() == 'true'
        self.setup_middleware()
    
    def setup_middleware(self):
        """Setup middleware for handling HTTP/HTTPS redirects and warnings"""
        
        @self.app.before_request
        def check_https():
            """Check HTTPS and redirect/warn if needed"""
            
            # Skip for health checks and static files
            if request.endpoint in ['health_check', 'static']:
                return None
            
            # Check if we're running in HTTPS mode
            is_https = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
            
            if self.force_https and not is_https:
                # Redirect to HTTPS if forced
                https_url = request.url.replace('http://', 'https://', 1)
                return redirect(https_url, code=301)
            
            elif not is_https and not self.allow_http:
                # Block HTTP entirely if not allowed
                return self.render_https_required()
            
            elif not is_https and request.endpoint not in ['http_warning', 'upgrade_to_https']:
                # Show warning for HTTP connections
                return self.render_http_warning()
            
            return None
    
    def render_https_required(self):
        """Render HTTPS required page"""
        template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>HTTPS Required - Financial Command Center AI</title>
            <style>
                body {
                    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
                    margin: 0;
                    padding: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    max-width: 600px;
                    text-align: center;
                }
                .icon {
                    font-size: 4rem;
                    margin-bottom: 20px;
                    color: #e74c3c;
                }
                h1 {
                    color: #2c3e50;
                    margin-bottom: 15px;
                    font-size: 2rem;
                }
                .subtitle {
                    color: #7f8c8d;
                    margin-bottom: 30px;
                    font-size: 1.1rem;
                }
                .security-notice {
                    background: #fff5f5;
                    border: 2px solid #fed7d7;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                }
                .security-notice h3 {
                    color: #e53e3e;
                    margin-top: 0;
                }
                .btn {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 30px;
                    border: none;
                    border-radius: 8px;
                    font-size: 1.1rem;
                    text-decoration: none;
                    display: inline-block;
                    margin: 10px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                .btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
                }
                .https-url {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    font-family: 'Monaco', 'Menlo', monospace;
                    font-size: 1.1rem;
                    color: #2c3e50;
                    margin: 20px 0;
                    border: 2px solid #e9ecef;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon"></div>
                <h1>HTTPS Required</h1>
                <p class="subtitle">Financial Command Center AI requires a secure connection</p>
                
                <div class="security-notice">
                    <h3> Security Notice</h3>
                    <p>This application handles sensitive financial data and requires encrypted connections for your protection.</p>
                </div>
                
                <p><strong>Please access the application using HTTPS:</strong></p>
                <div class="https-url">
                    {{ https_url }}
                </div>
                
                <a href="{{ https_url }}" class="btn"> Continue with HTTPS</a>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef;">
                    <p style="color: #6c757d; font-size: 0.9rem;">
                        If you're having certificate issues, check our 
                        <a href="{{ https_url }}/admin/ssl-help">SSL setup guide</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        https_url = request.url.replace('http://', 'https://', 1)
        return render_template_string(template, https_url=https_url), 426  # Upgrade Required
    
    def render_http_warning(self):
        """Render HTTP warning page with upgrade prompt"""
        template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Security Warning - Financial Command Center AI</title>
            <style>
                body {
                    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
                    margin: 0;
                    padding: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    max-width: 700px;
                    text-align: center;
                }
                .warning-icon {
                    font-size: 4rem;
                    margin-bottom: 20px;
                    color: #f39c12;
                    animation: pulse 2s infinite;
                }
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                    100% { transform: scale(1); }
                }
                h1 {
                    color: #e74c3c;
                    margin-bottom: 15px;
                    font-size: 2rem;
                }
                .subtitle {
                    color: #7f8c8d;
                    margin-bottom: 30px;
                    font-size: 1.1rem;
                }
                .risk-notice {
                    background: #fff3cd;
                    border: 2px solid #ffeaa7;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    text-align: left;
                }
                .risk-notice h3 {
                    color: #856404;
                    margin-top: 0;
                }
                .risk-list {
                    color: #856404;
                    margin: 15px 0;
                }
                .risk-list li {
                    margin: 8px 0;
                }
                .btn-primary {
                    background: linear-gradient(135deg, #00b894 0%, #00cec9 100%);
                    color: white;
                    padding: 15px 35px;
                    border: none;
                    border-radius: 8px;
                    font-size: 1.2rem;
                    text-decoration: none;
                    display: inline-block;
                    margin: 10px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                .btn-secondary {
                    background: #6c757d;
                    color: white;
                    padding: 12px 25px;
                    border: none;
                    border-radius: 6px;
                    font-size: 1rem;
                    text-decoration: none;
                    display: inline-block;
                    margin: 5px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                .btn-primary:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0, 184, 148, 0.3);
                }
                .btn-secondary:hover {
                    background: #5a6268;
                }
                .https-url {
                    background: #d4edda;
                    padding: 15px;
                    border-radius: 5px;
                    font-family: 'Monaco', 'Menlo', monospace;
                    font-size: 1.1rem;
                    color: #155724;
                    margin: 20px 0;
                    border: 2px solid #c3e6cb;
                }
                .countdown {
                    font-size: 1.2rem;
                    color: #e74c3c;
                    font-weight: bold;
                    margin: 15px 0;
                }
            </style>
            <script>
                let countdown = 10;
                function updateCountdown() {
                    const element = document.getElementById('countdown');
                    if (element) {
                        element.textContent = countdown;
                        if (countdown <= 0) {
                            window.location.href = '{{ https_url }}';
                        }
                        countdown--;
                        setTimeout(updateCountdown, 1000);
                    }
                }
                document.addEventListener('DOMContentLoaded', updateCountdown);
            </script>
        </head>
        <body>
            <div class="container">
                <div class="warning-icon"></div>
                <h1>Unsecured Connection Warning</h1>
                <p class="subtitle">You are accessing Financial Command Center AI over an unsecured HTTP connection</p>
                
                <div class="risk-notice">
                    <h3> Security Risks</h3>
                    <ul class="risk-list">
                        <li><strong>Data Interception:</strong> Your financial data could be intercepted by third parties</li>
                        <li><strong>Man-in-the-Middle Attacks:</strong> Attackers could modify requests and responses</li>
                        <li><strong>Credential Exposure:</strong> API keys and authentication tokens are transmitted in plain text</li>
                        <li><strong>Compliance Issues:</strong> Unsecured connections may violate financial regulations</li>
                    </ul>
                </div>
                
                <p><strong>For your security, please switch to HTTPS:</strong></p>
                <div class="https-url">
                    {{ https_url }}
                </div>
                
                <div class="countdown">
                    Auto-redirecting to HTTPS in <span id="countdown">10</span> seconds...
                </div>
                
                <div style="margin: 30px 0;">
                    <a href="{{ https_url }}" class="btn-primary"> Switch to HTTPS Now</a>
                    <a href="{{ current_url }}" class="btn-secondary"> Continue with HTTP (Not Recommended)</a>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef;">
                    <p style="color: #6c757d; font-size: 0.9rem;">
                        Having certificate issues? 
                        <a href="{{ https_url }}/admin/ssl-help" target="_blank">View our SSL setup guide</a> |
                        <a href="{{ https_url }}/admin/certificate-bundle" target="_blank">Download certificate installer</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        https_url = request.url.replace('http://', 'https://', 1)
        return render_template_string(template, https_url=https_url, current_url=request.url), 200
    
    def add_ssl_help_routes(self):
        """Add SSL help and certificate management routes"""
        
        @self.app.route('/admin/ssl-help')
        def ssl_help():
            """SSL help and troubleshooting page"""
            from cert_manager import CertificateManager
            cert_manager = CertificateManager()
            
            template = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>SSL Setup Guide - Financial Command Center AI</title>
                <style>
                    body { 
                        font-family: 'Segoe UI', sans-serif; 
                        margin: 0; 
                        padding: 20px; 
                        background: #f8f9fa; 
                        line-height: 1.6;
                    }
                    .container { 
                        max-width: 1000px; 
                        margin: 0 auto; 
                        background: white; 
                        padding: 40px; 
                        border-radius: 10px; 
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                    }
                    h1, h2, h3 { color: #2c3e50; }
                    .alert { 
                        padding: 15px; 
                        border-radius: 5px; 
                        margin: 20px 0; 
                    }
                    .alert-info { 
                        background: #d1ecf1; 
                        border: 1px solid #bee5eb; 
                        color: #0c5460; 
                    }
                    .alert-success { 
                        background: #d4edda; 
                        border: 1px solid #c3e6cb; 
                        color: #155724; 
                    }
                    .code { 
                        background: #f8f9fa; 
                        padding: 10px; 
                        border-radius: 5px; 
                        font-family: 'Courier New', monospace; 
                        overflow-x: auto; 
                        border: 1px solid #e9ecef; 
                        margin: 10px 0;
                    }
                    .btn { 
                        background: #007bff; 
                        color: white; 
                        padding: 10px 20px; 
                        border: none; 
                        border-radius: 5px; 
                        text-decoration: none; 
                        display: inline-block; 
                        margin: 5px; 
                    }
                    .btn:hover { 
                        background: #0056b3; 
                    }
                    .step { 
                        background: #f8f9fa; 
                        padding: 20px; 
                        border-radius: 8px; 
                        margin: 15px 0; 
                        border-left: 4px solid #007bff; 
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1> SSL Certificate Setup Guide</h1>
                    
                    <div class="alert alert-info">
                        <h3> Current Certificate Status</h3>
                        <pre>{{ health_status }}</pre>
                    </div>
                    
                    <h2> Quick Setup</h2>
                    
                    <div class="step">
                        <h3>Step 1: Generate Certificates</h3>
                        <p>Run the certificate manager to create SSL certificates:</p>
                        <div class="code">python cert_manager.py --generate</div>
                    </div>
                    
                    <div class="step">
                        <h3>Step 2: Trust the Certificate Authority</h3>
                        <p>Install the CA certificate to eliminate browser warnings:</p>
                        <div class="code">python cert_manager.py --bundle</div>
                        <p>Then run the installer from the created bundle.</p>
                    </div>
                    
                    <div class="step">
                        <h3>Step 3: Restart the Application</h3>
                        <p>Restart Financial Command Center AI to use the new certificates:</p>
                        <div class="code">python app.py</div>
                    </div>
                    
                    <h2> Troubleshooting</h2>
                    
                    <h3>Certificate Warnings in Browser</h3>
                    <div class="alert alert-info">
                        <p><strong>Chrome/Edge:</strong> Click "Advanced"  "Proceed to localhost (unsafe)"</p>
                        <p><strong>Firefox:</strong> Click "Advanced"  "Accept the Risk and Continue"</p>
                        <p><strong>Permanent Fix:</strong> Install the CA certificate using the bundle installer</p>
                    </div>
                    
                    <h3>Connection Refused Errors</h3>
                    <ul>
                        <li>Ensure the application is running on port 8000</li>
                        <li>Check firewall settings</li>
                        <li>Verify certificate files exist in the certs/ directory</li>
                    </ul>
                    
                    <h3>Certificate Expired</h3>
                    <div class="code">python cert_manager.py --generate</div>
                    <p>This will create new certificates valid for 365 days.</p>
                    
                    <h2> Enterprise Setup</h2>
                    
                    <div class="step">
                        <h3>Custom Certificate Authority</h3>
                        <p>For enterprise deployments, you can use your organization's CA:</p>
                        <ol>
                            <li>Replace <code>certs/ca.crt</code> with your CA certificate</li>
                            <li>Replace <code>certs/ca.key</code> with your CA private key</li>
                            <li>Generate new server certificates: <code>python cert_manager.py --generate</code></li>
                        </ol>
                    </div>
                    
                    <div class="step">
                        <h3>Load Balancer / Reverse Proxy</h3>
                        <p>If using a load balancer (nginx, Apache, etc.), configure SSL termination there and run the app in HTTP mode:</p>
                        <div class="code">ALLOW_HTTP=true python app.py</div>
                    </div>
                    
                    <h2> Docker Setup</h2>
                    
                    <div class="step">
                        <h3>Docker Compose with SSL</h3>
                        <div class="code">
# Add to docker-compose.yml
volumes:
  - ./certs:/app/certs:ro
environment:
  - FORCE_HTTPS=true
ports:
  - "443:8000"
                        </div>
                    </div>
                    
                    <div style="margin-top: 40px; text-align: center;">
                        <a href="/admin/certificate-bundle" class="btn"> Download Certificate Bundle</a>
                        <a href="/health" class="btn"> System Health Check</a>
                        <a href="/" class="btn"> Home</a>
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef; color: #6c757d; font-size: 0.9rem;">
                        <p><strong>Need Help?</strong> Check the project documentation or create an issue in the GitHub repository.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            health_status = "\n".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in cert_manager.health_check().items()])
            return render_template_string(template, health_status=health_status)
        
        @self.app.route('/admin/certificate-bundle')
        def certificate_bundle():
            """Provide certificate bundle for download"""
            from cert_manager import CertificateManager
            cert_manager = CertificateManager()
            bundle_dir = cert_manager.create_client_bundle()
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Certificate Bundle - Financial Command Center AI</title>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f5f7fa; }}
                    .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }}
                    .success {{ background: #d4edda; padding: 20px; border-radius: 8px; border: 1px solid #c3e6cb; color: #155724; margin: 20px 0; }}
                    .warning {{ background: #fff3cd; padding: 20px; border-radius: 8px; border: 1px solid #ffeaa7; color: #856404; margin: 20px 0; }}
                    .code {{ background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: 'Courier New', monospace; margin: 10px 0; word-break: break-all; }}
                    .btn {{ background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 6px; text-decoration: none; display: inline-block; margin: 5px; }}
                    .btn:hover {{ background: #0056b3; }}
                    .install-steps {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .step {{ margin: 15px 0; padding: 10px; background: white; border-radius: 5px; border-left: 4px solid #007bff; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Certificate Bundle Created</h1>
                    
                    <div class="success">
                        <h3>Bundle Ready!</h3>
                        <p>Certificate installation bundle created at:</p>
                        <div class="code">{str(bundle_dir.absolute()).replace(chr(92), chr(92)+chr(92))}</div>
                    </div>
                    
                    <div class="warning">
                        <h3>Important: Browser Restart Required</h3>
                        <p>After installing the certificate, you must <strong>completely restart your browser</strong> for the changes to take effect.</p>
                    </div>
                    
                    <h3>Bundle Contents:</h3>
                    <ul>
                        <li><strong>ca_certificate.crt</strong> - Root certificate to install</li>
                        <li><strong>install_certificate_windows.bat</strong> - Windows installer (Run as Administrator)</li>
                        <li><strong>install_certificate_unix.sh</strong> - macOS/Linux installer</li>
                        <li><strong>README.md</strong> - Detailed installation instructions</li>
                    </ul>
                    
                    <div class="install-steps">
                        <h3>Quick Installation Steps:</h3>
                        
                        <div class="step">
                            <h4>Windows:</h4>
                            <ol>
                                <li>Navigate to the bundle folder</li>
                                <li>Right-click <strong>install_certificate_windows.bat</strong></li>
                                <li>Select "Run as administrator"</li>
                                <li>Follow the prompts</li>
                                <li>Restart your browser completely</li>
                            </ol>
                        </div>
                        
                        <div class="step">
                            <h4>macOS/Linux:</h4>
                            <ol>
                                <li>Open Terminal</li>
                                <li>Navigate to the bundle folder</li>
                                <li>Run: <code>./install_certificate_unix.sh</code></li>
                                <li>Enter your password when prompted</li>
                                <li>Restart your browser completely</li>
                            </ol>
                        </div>
                    </div>
                    
                    <h3>Manual Installation (if scripts fail):</h3>
                    <div class="step">
                        <h4>Chrome/Edge:</h4>
                        <ol>
                            <li>Go to Settings > Privacy and Security > Security</li>
                            <li>Click "Manage certificates"</li>
                            <li>Go to "Trusted Root Certification Authorities" tab</li>
                            <li>Click "Import" and select <strong>ca_certificate.crt</strong></li>
                        </ol>
                    </div>
                    
                    <div class="step">
                        <h4>Firefox:</h4>
                        <ol>
                            <li>Go to Settings > Privacy & Security</li>
                            <li>Scroll to "Certificates" and click "View Certificates"</li>
                            <li>Go to "Authorities" tab</li>
                            <li>Click "Import" and select <strong>ca_certificate.crt</strong></li>
                            <li>Check "Trust this CA to identify websites"</li>
                        </ol>
                    </div>
                    
                    <div style="margin-top: 30px; text-align: center;">
                        <a href="/admin/ssl-help" class="btn">Full Setup Guide</a>
                        <a href="/admin/dashboard" class="btn">Dashboard</a>
                        <a href="/" class="btn">Home</a>
                    </div>
                    
                    <div style="margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 5px; font-size: 0.9em;">
                        <strong>Still seeing warnings?</strong> Make sure to:
                        <ul>
                            <li>Restart your browser completely (close all windows)</li>
                            <li>Clear browser cache and cookies for localhost</li>
                            <li>Wait a few seconds after restarting before testing</li>
                        </ul>
                    </div>
                </div>
            </body>
            </html>
            """
            return html_content


def configure_server_mode(app: Flask):
    """Configure server mode management for Flask app"""
    mode_manager = ServerModeManager(app)
    mode_manager.add_ssl_help_routes()
    return mode_manager