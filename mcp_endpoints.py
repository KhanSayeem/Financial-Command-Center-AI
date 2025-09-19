#!/usr/bin/env python3
"""
Additional API endpoints for MCP server integration
These endpoints should be added to app_with_setup_wizard.py
"""

# Add these routes before the "if __name__ == '__main__':" line in app_with_setup_wizard.py

MCP_ENDPOINTS = '''
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
    
    # Mock invoice data
    all_invoices = [
        {
            'invoice_id': 'INV-2025-001',
            'invoice_number': 'INV-001',
            'customer': 'Acme Corporation',
            'amount': 8750.00,
            'currency': 'USD',
            'status': 'paid',
            'date': '2025-09-01',
            'due_date': '2025-09-15',
            'description': 'Consulting Services Q3 2025'
        },
        {
            'invoice_id': 'INV-2025-002', 
            'invoice_number': 'INV-002',
            'customer': 'TechStart Inc',
            'amount': 2450.00,
            'currency': 'USD',
            'status': 'pending',
            'date': '2025-09-05',
            'due_date': '2025-09-20',
            'description': 'Software Development'
        },
        {
            'invoice_id': 'INV-2025-003',
            'invoice_number': 'INV-003', 
            'customer': 'Global Systems Ltd',
            'amount': 15750.00,
            'currency': 'USD',
            'status': 'overdue',
            'date': '2025-08-15',
            'due_date': '2025-09-01',
            'description': 'Infrastructure Migration'
        },
        {
            'invoice_id': 'INV-2025-004',
            'invoice_number': 'INV-004',
            'customer': 'StartupXYZ',
            'amount': 650.00,
            'currency': 'USD', 
            'status': 'draft',
            'date': '2025-09-10',
            'due_date': '2025-09-25',
            'description': 'Website Maintenance'
        }
    ]
    
    # Apply filters
    filtered_invoices = all_invoices
    
    if status != 'all':
        filtered_invoices = [inv for inv in filtered_invoices if inv['status'].lower() == status]
    
    if amount_min is not None:
        filtered_invoices = [inv for inv in filtered_invoices if inv['amount'] >= amount_min]
    
    if customer:
        filtered_invoices = [inv for inv in filtered_invoices if customer in inv['customer'].lower()]
    
    return jsonify({
        'status': 'success',
        'invoices': filtered_invoices,
        'total_count': len(filtered_invoices),
        'filters_applied': {
            'status': status,
            'amount_min': amount_min,
            'customer': customer
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """Get customer/supplier contacts"""
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'
    
    if not wants_json:
        return "Contacts endpoint - use Accept: application/json header", 400
    
    # Get search parameter
    search_term = request.args.get('search', '').lower()
    
    # Mock contacts data
    all_contacts = [
        {
            'contact_id': 'CNT-001',
            'name': 'Acme Corporation',
            'email': 'billing@acme-corp.com',
            'phone': '+1-555-0123',
            'type': 'customer',
            'address': '123 Business Ave, New York, NY 10001',
            'status': 'active',
            'total_invoices': 15,
            'total_amount_owed': 0.00
        },
        {
            'contact_id': 'CNT-002',
            'name': 'TechStart Inc',
            'email': 'accounts@techstart.io',
            'phone': '+1-555-0456',
            'type': 'customer',
            'address': '456 Innovation Dr, San Francisco, CA 94105',
            'status': 'active',
            'total_invoices': 8,
            'total_amount_owed': 2450.00
        },
        {
            'contact_id': 'CNT-003',
            'name': 'Global Systems Ltd',
            'email': 'finance@globalsys.com',
            'phone': '+1-555-0789',
            'type': 'customer',
            'address': '789 Enterprise Blvd, Austin, TX 73301',
            'status': 'active',
            'total_invoices': 12,
            'total_amount_owed': 15750.00
        },
        {
            'contact_id': 'CNT-004',
            'name': 'Office Supply Plus',
            'email': 'sales@officesupply.com',
            'phone': '+1-555-0321',
            'type': 'supplier',
            'address': '321 Commerce St, Chicago, IL 60601',
            'status': 'active',
            'total_invoices': 0,
            'total_amount_owed': 0.00
        },
        {
            'contact_id': 'CNT-005',
            'name': 'StartupXYZ',
            'email': 'hello@startupxyz.com',
            'phone': '+1-555-0654',
            'type': 'customer',
            'address': '654 Venture Way, Seattle, WA 98101',
            'status': 'active',
            'total_invoices': 3,
            'total_amount_owed': 650.00
        }
    ]
    
    # Apply search filter
    if search_term:
        filtered_contacts = [
            contact for contact in all_contacts 
            if (search_term in contact['name'].lower() or 
                search_term in contact['email'].lower() or
                search_term in contact.get('phone', '').lower())
        ]
    else:
        filtered_contacts = all_contacts
    
    return jsonify({
        'status': 'success',
        'contacts': filtered_contacts,
        'total_count': len(filtered_contacts),
        'search_term': search_term,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/dashboard', methods=['GET']) 
def get_dashboard():
    """Get comprehensive financial dashboard data from real sources"""
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'
    
    if not wants_json:
        return "Dashboard endpoint - use Accept: application/json header", 400
    
    # Import the Xero dashboard function
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
            cfg = plaid.Configuration(
                host=plaid.Environment.Sandbox,  # Change to Production for live data
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

# End of MCP Integration endpoints
# =============================================================================
'''

if __name__ == "__main__":
    print("This file contains MCP endpoint definitions.")
    print("Copy the MCP_ENDPOINTS string content and add it to app_with_setup_wizard.py")
    print("Place it before the 'if __name__ == '__main__':' line.")