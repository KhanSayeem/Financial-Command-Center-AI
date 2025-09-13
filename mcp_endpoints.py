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
    """Get comprehensive financial dashboard data"""
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header or request.args.get('format') == 'json'
    
    if not wants_json:
        return "Dashboard endpoint - use Accept: application/json header", 400
    
    # Comprehensive dashboard data
    dashboard_data = {
        'status': 'healthy',
        'overview': {
            'total_revenue_ytd': 245780.50,
            'total_expenses_ytd': 189420.30,
            'net_profit_ytd': 56360.20,
            'profit_margin': 22.9,
            'currency': 'USD'
        },
        'cash_flow': {
            'current_balance': 45750.32,
            'available_credit': 25000.00,
            'monthly_burn_rate': 67200.00,
            'runway_months': 8.5
        },
        'invoices': {
            'total_outstanding': 18850.00,
            'overdue_amount': 15750.00,
            'paid_this_month': 28750.00,
            'pending_count': 3,
            'overdue_count': 1
        },
        'customers': {
            'total_active': 28,
            'new_this_month': 3,
            'top_customer': 'Global Systems Ltd',
            'average_invoice_value': 5456.78
        },
        'integrations': {
            'stripe': {'status': 'connected', 'last_sync': '2025-09-13T15:30:00Z'},
            'xero': {'status': 'connected', 'last_sync': '2025-09-13T15:25:00Z'},
            'plaid': {'status': 'connected', 'last_sync': '2025-09-13T15:20:00Z'}
        },
        'alerts': [
            {
                'type': 'warning',
                'message': 'Invoice INV-003 is overdue by 12 days',
                'action_needed': True
            },
            {
                'type': 'info', 
                'message': '3 invoices due in the next 7 days',
                'action_needed': False
            }
        ],
        'recent_activity': [
            {'date': '2025-09-13', 'type': 'payment_received', 'amount': 5500.00, 'description': 'Payment from TechStart Inc'},
            {'date': '2025-09-12', 'type': 'expense', 'amount': -2800.00, 'description': 'Office rent payment'},
            {'date': '2025-09-11', 'type': 'invoice_sent', 'amount': 3200.00, 'description': 'Invoice INV-005 sent to NewClient Co'}
        ],
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