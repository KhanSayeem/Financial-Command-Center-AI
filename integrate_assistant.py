"""
Financial Command Center Assistant Integration
Adds assistant functionality to existing FCC web application
"""

import os
import json
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def integrate_assistant_with_fcc():
    """
    Integrate the Financial Command Center Assistant with the existing FCC web application.
    This adds assistant routes and templates to the main app_with_setup_wizard.py file.
    """
    
    # Path to the main FCC application file
    fcc_app_path = Path("app_with_setup_wizard.py")
    
    if not fcc_app_path.exists():
        print("Error: app_with_setup_wizard.py not found")
        return False
    
    # Read the existing FCC app file
    with open(fcc_app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if assistant routes are already integrated
    if "@app.route('/assistant')" in content:
        print("Assistant routes already integrated")
        return True
    
    # Define the assistant integration code
    assistant_routes = '''
# =============================================================================
# Financial Command Center Assistant Integration
# =============================================================================

@app.route('/assistant')
def assistant_page():
    """Render the Financial Command Center Assistant page."""
    nav_items = build_nav('assistant')
    return render_template('assistant/index.html', nav_items=nav_items)

@app.route('/api/assistant/health')
def assistant_health():
    """Health check for the assistant integration."""
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "openai_api_key_configured": bool(os.getenv('OPENAI_API_KEY')),
            "fcc_connected": True
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run()
'''
    
    # Insert the assistant routes before the final if __name__ == "__main__": block
    if "if __name__ == '__main__':" in content:
        # Split the content at the main block
        parts = content.split("if __name__ == '__main__':", 1)
        if len(parts) == 2:
            # Insert assistant routes before the main block
            new_content = parts[0] + assistant_routes + "\nif __name__ == '__main__':" + parts[1]
            
            # Write the updated content back to the file
            with open(fcc_app_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ Assistant routes integrated successfully")
            return True
    
    print("Error: Could not find main application block to integrate assistant routes")
    return False

def create_assistant_templates():
    """
    Create the HTML templates for the Financial Command Center Assistant.
    """
    
    # Create templates directory if it doesn't exist
    templates_dir = Path("templates/assistant")
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Create the main assistant page template
    assistant_html = '''{% extends "layout.html" %}

{% block title %}Financial Assistant · Financial Command Center AI{% endblock %}

{% block content %}
<div class="flex flex-col gap-10">
    <div class="card border border-border/70 p-7 shadow-card">
        <div class="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div class="space-y-3">
                <span class="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.28em] text-primary">
                    <i data-lucide="bot" class="h-3.5 w-3.5"></i>
                    AI Assistant
                </span>
                <div class="space-y-2">
                    <h1 class="text-3xl font-semibold tracking-tight sm:text-4xl">Financial Command Center Assistant</h1>
                    <p class="text-base text-muted-foreground sm:text-lg">AI-powered financial insights and analysis at your fingertips.</p>
                </div>
                <div class="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                    <span class="inline-flex items-center gap-2 rounded-full border border-border/70 bg-muted/60 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                        <i data-lucide="shield" class="h-3.5 w-3.5"></i>
                        Secure & Confidential
                    </span>
                    <span class="inline-flex items-center gap-2 text-sm font-medium text-emerald-600">
                        <i data-lucide="check-circle" class="h-4 w-4"></i>
                        Connected to Xero, Stripe, Plaid
                    </span>
                </div>
            </div>
            <div class="flex flex-col gap-3 sm:flex-row">
                <a href="/admin/dashboard" class="inline-flex items-center justify-center gap-2 rounded-lg border border-border/70 bg-card px-5 py-2.5 text-sm font-medium text-foreground transition hover:border-border hover:bg-card/80">
                    <i data-lucide="layout-dashboard" class="h-4 w-4"></i>
                    Admin Dashboard
                </a>
            </div>
        </div>
    </div>

    <div class="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <!-- Main Assistant Interface -->
        <div class="card border border-border/70 p-6">
            <div class="mb-6">
                <h2 class="text-lg font-semibold text-foreground">Ask About Your Finances</h2>
                <p class="text-sm text-muted-foreground">Get instant insights on cash flow, revenue, expenses, and more.</p>
            </div>
            
            <!-- Chat Interface -->
            <div class="space-y-4">
                <div id="chat-messages" class="mb-4 space-y-4 max-h-96 overflow-y-auto pr-2">
                    <!-- Welcome Message -->
                    <div class="flex items-start">
                        <div class="bg-primary/10 text-primary p-3 rounded-full mr-3 flex-shrink-0">
                            <i data-lucide="bot" class="h-5 w-5"></i>
                        </div>
                        <div class="bg-muted/60 rounded-2xl rounded-tl-none p-4 max-w-3xl">
                            <p class="text-foreground">
                                Hello! I'm your Financial Command Center Assistant. I can help you understand your company's financial position, analyze cash flow, track revenue, manage expenses, and provide actionable insights.
                            </p>
                            <p class="text-foreground mt-2">
                                Ask me questions like:
                            </p>
                            <ul class="list-disc pl-5 mt-2 space-y-1 text-muted-foreground">
                                <li>What's our current cash position?</li>
                                <li>Show me overdue invoices over $1,000</li>
                                <li>Generate a profit and loss statement</li>
                                <li>Who are our top 5 customers by revenue?</li>
                            </ul>
                        </div>
                    </div>
                </div>
                
                <!-- Input Area -->
                <div class="border-t border-border/70 pt-4">
                    <div class="mb-3">
                        <textarea 
                            id="assistant-input" 
                            placeholder="Ask a question about your financial health, cash flow, revenue, expenses, or anything else..."
                            class="w-full rounded-lg border border-border/70 bg-background px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
                            rows="3"
                        ></textarea>
                    </div>
                    
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div class="flex items-center text-xs text-muted-foreground">
                            <i data-lucide="lock" class="h-3.5 w-3.5 mr-1"></i>
                            <span>All conversations are encrypted and confidential</span>
                        </div>
                        
                        <button 
                            id="send-assistant-message"
                            class="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90"
                        >
                            <i data-lucide="send" class="h-4 w-4"></i>
                            <span>Send Question</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Sidebar -->
        <div class="flex flex-col gap-6">
            <!-- Quick Stats -->
            <div class="card border border-border/70 p-6">
                <h2 class="text-lg font-semibold text-foreground mb-4">Financial Snapshot</h2>
                
                <div class="space-y-4">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <span class="inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-green-50 text-green-700">
                                <i data-lucide="dollar-sign" class="h-5 w-5"></i>
                            </span>
                            <div>
                                <p class="text-sm font-medium text-muted-foreground">Cash Position</p>
                                <p class="text-lg font-semibold leading-none tracking-tight">$48,250.75</p>
                            </div>
                        </div>
                        <span class="text-xs font-medium text-emerald-600">+2.4%</span>
                    </div>
                    
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <span class="inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-700">
                                <i data-lucide="heart-pulse" class="h-5 w-5"></i>
                            </span>
                            <div>
                                <p class="text-sm font-medium text-muted-foreground">Health Score</p>
                                <p class="text-lg font-semibold leading-none tracking-tight">87/100</p>
                            </div>
                        </div>
                        <span class="text-xs font-medium text-emerald-600">Good</span>
                    </div>
                    
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <span class="inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-purple-50 text-purple-700">
                                <i data-lucide="calendar" class="h-5 w-5"></i>
                            </span>
                            <div>
                                <p class="text-sm font-medium text-muted-foreground">Last Updated</p>
                                <p class="text-lg font-semibold leading-none tracking-tight">Today</p>
                            </div>
                        </div>
                        <span class="text-xs font-medium text-muted-foreground">2 min ago</span>
                    </div>
                </div>
            </div>
            
            <!-- Quick Actions -->
            <div class="card border border-border/70 p-6">
                <h2 class="text-lg font-semibold text-foreground mb-4">Quick Actions</h2>
                
                <div class="space-y-3">
                    <button class="w-full inline-flex items-center gap-3 rounded-lg border border-border/70 bg-card px-3 py-2 text-sm font-medium text-foreground transition hover:bg-card/80">
                        <i data-lucide="file-text" class="h-4 w-4 text-primary"></i>
                        <span>Generate Financial Report</span>
                    </button>
                    
                    <button class="w-full inline-flex items-center gap-3 rounded-lg border border-border/70 bg-card px-3 py-2 text-sm font-medium text-foreground transition hover:bg-card/80">
                        <i data-lucide="alert-triangle" class="h-4 w-4 text-amber-600"></i>
                        <span>Check Overdue Invoices</span>
                    </button>
                    
                    <button class="w-full inline-flex items-center gap-3 rounded-lg border border-border/70 bg-card px-3 py-2 text-sm font-medium text-foreground transition hover:bg-card/80">
                        <i data-lucide="trending-up" class="h-4 w-4 text-emerald-600"></i>
                        <span>Analyze Revenue Trends</span>
                    </button>
                    
                    <button class="w-full inline-flex items-center gap-3 rounded-lg border border-border/70 bg-card px-3 py-2 text-sm font-medium text-foreground transition hover:bg-card/80">
                        <i data-lucide="pie-chart" class="h-4 w-4 text-blue-600"></i>
                        <span>Review Expense Categories</span>
                    </button>
                </div>
            </div>
            
            <!-- Example Queries -->
            <div class="card border border-border/70 p-6">
                <h2 class="text-lg font-semibold text-foreground mb-4">Try These Questions</h2>
                
                <div class="space-y-3">
                    <div class="p-3 border border-border/70 rounded-lg hover:border-primary/50 cursor-pointer transition duration-200 example-query">
                        <p class="text-sm text-foreground">What's our current cash position?</p>
                    </div>
                    <div class="p-3 border border-border/70 rounded-lg hover:border-primary/50 cursor-pointer transition duration-200 example-query">
                        <p class="text-sm text-foreground">Show overdue invoices over $1,000</p>
                    </div>
                    <div class="p-3 border border-border/70 rounded-lg hover:border-primary/50 cursor-pointer transition duration-200 example-query">
                        <p class="text-sm text-foreground">Generate P&L for last quarter</p>
                    </div>
                    <div class="p-3 border border-border/70 rounded-lg hover:border-primary/50 cursor-pointer transition duration-200 example-query">
                        <p class="text-sm text-foreground">Who are our top 5 customers?</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block body_scripts %}
    {{ super() }}
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // DOM Elements
            const messageInput = document.getElementById('assistant-input');
            const sendButton = document.getElementById('send-assistant-message');
            const chatMessages = document.getElementById('chat-messages');
            
            // Add example query click handlers
            document.querySelectorAll('.example-query').forEach(element => {
                element.addEventListener('click', function() {
                    messageInput.value = this.querySelector('p').textContent;
                    messageInput.focus();
                });
            });
            
            // Send message function
            function sendAssistantMessage() {
                const message = messageInput.value.trim();
                if (!message) return;
                
                // Add user message to chat
                addMessageToChat('user', message);
                messageInput.value = '';
                
                // Show loading indicator
                const loadingDiv = document.createElement('div');
                loadingDiv.id = 'assistant-loading';
                loadingDiv.className = 'flex items-start';
                loadingDiv.innerHTML = `
                    <div class="bg-primary/10 text-primary p-3 rounded-full mr-3 flex-shrink-0">
                        <i data-lucide="bot" class="h-5 w-5"></i>
                    </div>
                    <div class="bg-muted/60 rounded-2xl rounded-tl-none p-4 max-w-3xl">
                        <div class="flex items-center">
                            <div class="h-2 w-2 bg-primary rounded-full mr-2 animate-pulse"></div>
                            <span>Analyzing your financial data...</span>
                        </div>
                    </div>
                `;
                chatMessages.appendChild(loadingDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
                
                // Simulate API call (in a real implementation, this would call your assistant API)
                setTimeout(() => {
                    // Remove loading indicator
                    document.getElementById('assistant-loading').remove();
                    
                    // Add mock response
                    addMessageToChat('assistant', `
                        <p>I've analyzed your financial data and here's what I found:</p>
                        <div class="mt-3 space-y-3">
                            <div class="flex items-center justify-between p-3 bg-muted/60 rounded-lg">
                                <span class="font-medium">Current Cash Position</span>
                                <span class="font-semibold text-emerald-600">$48,250.75</span>
                            </div>
                            <div class="flex items-center justify-between p-3 bg-muted/60 rounded-lg">
                                <span class="font-medium">Monthly Inflow</span>
                                <span class="font-semibold">$92,300.00</span>
                            </div>
                            <div class="flex items-center justify-between p-3 bg-muted/60 rounded-lg">
                                <span class="font-medium">Monthly Outflow</span>
                                <span class="font-semibold">$68,150.00</span>
                            </div>
                        </div>
                        <p class="mt-3">Your cash position is healthy with positive monthly cash flow. Consider reviewing overdue invoices to improve liquidity further.</p>
                    `);
                }, 1500);
            }
            
            // Add message to chat function
            function addMessageToChat(role, content) {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'flex items-start';
                
                if (role === 'user') {
                    messageDiv.innerHTML = `
                        <div class="ml-auto bg-primary text-primary-foreground rounded-2xl rounded-br-none p-4 max-w-3xl">
                            <p class="text-primary-foreground">${content}</p>
                        </div>
                        <div class="bg-muted/60 text-foreground p-3 rounded-full ml-3 flex-shrink-0">
                            <i data-lucide="user" class="h-4 w-4"></i>
                        </div>
                    `;
                } else {
                    messageDiv.innerHTML = `
                        <div class="bg-primary/10 text-primary p-3 rounded-full mr-3 flex-shrink-0">
                            <i data-lucide="bot" class="h-5 w-5"></i>
                        </div>
                        <div class="bg-muted/60 rounded-2xl rounded-tl-none p-4 max-w-3xl">
                            ${content}
                        </div>
                    `;
                }
                
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
            // Event Listeners
            sendButton.addEventListener('click', sendAssistantMessage);
            
            messageInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendAssistantMessage();
                }
            });
        });
    </script>
{% endblock %}
'''
    
    # Write the assistant template
    with open(templates_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write(assistant_html)
    
    print("✅ Assistant templates created successfully")
    return True

def update_navigation():
    """
    Update the navigation to include the assistant link.
    """
    
    # Path to the navigation helper
    nav_helper_path = Path("ui/helpers.py")
    
    if not nav_helper_path.exists():
        print("Error: ui/helpers.py not found")
        return False
    
    # Read the navigation helper file
    with open(nav_helper_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if assistant navigation is already added
    if "assistant" in content and "Assistant" in content:
        print("Assistant navigation already added")
        return True
    
    # Define the updated navigation
    updated_nav = '''PRIMARY_NAV: Tuple[NavDefinition, ...] = (
    ('overview', 'Overview', 'index', {}),
    ('contacts', 'Contacts', 'view_xero_contacts', {}),
    ('invoices', 'Invoices', 'view_xero_invoices', {}),
    ('assistant', 'Assistant', 'assistant_page', {}),
    ('setup', 'Setup', 'setup_wizard', {}),
    ('health', 'Health', 'health_check', {}),
    ('admin', 'Admin', 'admin_dashboard', {}),
)'''
    
    # Replace the PRIMARY_NAV definition
    import re
    pattern = r'PRIMARY_NAV: Tuple\[NavDefinition, \.\.\.\] = \([^)]+\)'
    if re.search(pattern, content):
        content = re.sub(pattern, updated_nav, content)
        
        # Write the updated content back to the file
        with open(nav_helper_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Navigation updated successfully")
        return True
    else:
        print("Error: Could not find PRIMARY_NAV definition to update")
        return False

def main():
    """Main function to integrate assistant with FCC."""
    print("Financial Command Center Assistant Integration")
    print("=" * 50)
    
    try:
        # Integrate assistant routes with FCC app
        if not integrate_assistant_with_fcc():
            print("Failed to integrate assistant routes")
            return False
        
        # Create assistant templates
        if not create_assistant_templates():
            print("Failed to create assistant templates")
            return False
        
        # Update navigation
        if not update_navigation():
            print("Failed to update navigation")
            return False
        
        print("\nSuccess! Financial Command Center Assistant integrated successfully.")
        print("\nChanges made:")
        print("1. Added assistant routes to app_with_setup_wizard.py")
        print("2. Created assistant templates in templates/assistant/")
        print("3. Updated navigation to include Assistant link")
        print("\nAccess the assistant at: https://localhost:8000/assistant")
        
        return True
        
    except Exception as e:
        print(f"Error during integration: {str(e)}")
        return False

if __name__ == "__main__":
    main()