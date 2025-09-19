"""
Financial Data Export Module
Exports financial data to Excel format with multiple sheets
"""
import pandas as pd
import json
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, List, Any, Optional
import os

try:
    from xero_client import load_api_client, get_tenant_id
    from xero_python.accounting import AccountingApi
    XERO_AVAILABLE = True
except ImportError:
    XERO_AVAILABLE = False

def fetch_xero_financial_data():
    """Fetch comprehensive financial data from Xero API - REAL DATA ONLY"""
    if not XERO_AVAILABLE:
        return {"error": "Xero SDK not available", "contacts": [], "invoices": [], "accounts": []}

    try:
        api_client = load_api_client()
        if not api_client:
            return {"error": "Xero API client not available", "contacts": [], "invoices": [], "accounts": []}

        accounting_api = AccountingApi(api_client)
        tenant_id = get_tenant_id()

        if not tenant_id:
            return {"error": "No Xero tenant ID found", "contacts": [], "invoices": [], "accounts": []}

        data = {}

        # Fetch contacts
        try:
            contacts_response = accounting_api.get_contacts(tenant_id)
            contacts = []
            for contact in contacts_response.contacts:
                contacts.append({
                    'ID': contact.contact_id,
                    'Name': contact.name,
                    'Email': contact.email_address,
                    'Phone': contact.first_name,
                    'Status': str(contact.contact_status) if contact.contact_status else 'ACTIVE',
                    'Is_Customer': contact.is_customer,
                    'Is_Supplier': contact.is_supplier,
                    'Created_Date': contact.updated_date_utc.strftime('%Y-%m-%d') if contact.updated_date_utc else ''
                })
            data['contacts'] = contacts
        except Exception as e:
            print(f"Error fetching contacts: {e}")
            data['contacts'] = []

        # Fetch invoices
        try:
            invoices_response = accounting_api.get_invoices(tenant_id)
            invoices = []
            for invoice in invoices_response.invoices:
                invoices.append({
                    'Invoice_ID': invoice.invoice_id,
                    'Invoice_Number': invoice.invoice_number,
                    'Contact_Name': invoice.contact.name if invoice.contact else '',
                    'Date': invoice.date.strftime('%Y-%m-%d') if invoice.date else '',
                    'Due_Date': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '',
                    'Status': str(invoice.status) if invoice.status else '',
                    'Total': float(invoice.total) if invoice.total else 0.0,
                    'Amount_Due': float(invoice.amount_due) if invoice.amount_due else 0.0,
                    'Currency': str(invoice.currency_code) if invoice.currency_code else 'USD'
                })
            data['invoices'] = invoices
        except Exception as e:
            print(f"Error fetching invoices: {e}")
            data['invoices'] = []

        # Fetch accounts
        try:
            accounts_response = accounting_api.get_accounts(tenant_id)
            accounts = []
            for account in accounts_response.accounts:
                accounts.append({
                    'Account_ID': account.account_id,
                    'Code': account.code,
                    'Name': account.name,
                    'Type': str(account.type) if account.type else '',
                    'Class': str(getattr(account, 'class_', '')) if hasattr(account, 'class_') else '',
                    'Status': str(account.status) if account.status else '',
                    'Tax_Type': account.tax_type,
                    'Enable_Payments': account.enable_payments_to_account
                })
            data['accounts'] = accounts
        except Exception as e:
            print(f"Error fetching accounts: {e}")
            data['accounts'] = []

        return data

    except Exception as e:
        print(f"Error fetching Xero data: {e}")
        return {"error": f"Failed to fetch Xero data: {str(e)}", "contacts": [], "invoices": [], "accounts": []}

def get_mock_financial_data():
    """Generate sample financial data for demo purposes"""
    current_date = datetime.now()

    # Mock contacts data
    contacts = [
        {'ID': 'C001', 'Name': 'ABC Corporation', 'Email': 'billing@abc.com', 'Phone': '555-0101',
         'Status': 'ACTIVE', 'Is_Customer': True, 'Is_Supplier': False, 'Created_Date': '2024-01-15'},
        {'ID': 'C002', 'Name': 'XYZ Industries', 'Email': 'ap@xyz.com', 'Phone': '555-0102',
         'Status': 'ACTIVE', 'Is_Customer': True, 'Is_Supplier': False, 'Created_Date': '2024-02-20'},
        {'ID': 'C003', 'Name': 'Tech Solutions Ltd', 'Email': 'finance@techsol.com', 'Phone': '555-0103',
         'Status': 'ACTIVE', 'Is_Customer': True, 'Is_Supplier': False, 'Created_Date': '2024-03-10'},
        {'ID': 'S001', 'Name': 'Office Supplies Co', 'Email': 'orders@supplies.com', 'Phone': '555-0201',
         'Status': 'ACTIVE', 'Is_Customer': False, 'Is_Supplier': True, 'Created_Date': '2024-01-05'},
        {'ID': 'S002', 'Name': 'CloudTech Services', 'Email': 'billing@cloudtech.com', 'Phone': '555-0202',
         'Status': 'ACTIVE', 'Is_Customer': False, 'Is_Supplier': True, 'Created_Date': '2024-01-20'}
    ]

    # Mock invoices data
    invoices = [
        {'Invoice_ID': 'INV-001', 'Invoice_Number': '2024-001', 'Contact_Name': 'ABC Corporation',
         'Date': '2024-09-01', 'Due_Date': '2024-10-01', 'Status': 'PAID', 'Total': 15000.00, 'Amount_Due': 0.00, 'Currency': 'USD'},
        {'Invoice_ID': 'INV-002', 'Invoice_Number': '2024-002', 'Contact_Name': 'XYZ Industries',
         'Date': '2024-09-05', 'Due_Date': '2024-10-05', 'Status': 'AUTHORISED', 'Total': 8500.00, 'Amount_Due': 8500.00, 'Currency': 'USD'},
        {'Invoice_ID': 'INV-003', 'Invoice_Number': '2024-003', 'Contact_Name': 'Tech Solutions Ltd',
         'Date': '2024-09-10', 'Due_Date': '2024-10-10', 'Status': 'PAID', 'Total': 22500.00, 'Amount_Due': 0.00, 'Currency': 'USD'},
        {'Invoice_ID': 'INV-004', 'Invoice_Number': '2024-004', 'Contact_Name': 'ABC Corporation',
         'Date': '2024-09-15', 'Due_Date': '2024-10-15', 'Status': 'AUTHORISED', 'Total': 12000.00, 'Amount_Due': 12000.00, 'Currency': 'USD'},
        {'Invoice_ID': 'INV-005', 'Invoice_Number': '2024-005', 'Contact_Name': 'XYZ Industries',
         'Date': '2024-09-18', 'Due_Date': '2024-10-18', 'Status': 'DRAFT', 'Total': 6750.00, 'Amount_Due': 6750.00, 'Currency': 'USD'}
    ]

    # Mock accounts data
    accounts = [
        {'Account_ID': 'A001', 'Code': '1001', 'Name': 'Checking Account', 'Type': 'BANK', 'Class': 'ASSET', 'Status': 'ACTIVE', 'Tax_Type': '', 'Enable_Payments': True},
        {'Account_ID': 'A002', 'Code': '1100', 'Name': 'Accounts Receivable', 'Type': 'CURRENT', 'Class': 'ASSET', 'Status': 'ACTIVE', 'Tax_Type': '', 'Enable_Payments': False},
        {'Account_ID': 'A003', 'Code': '4000', 'Name': 'Sales Revenue', 'Type': 'REVENUE', 'Class': 'REVENUE', 'Status': 'ACTIVE', 'Tax_Type': 'OUTPUT', 'Enable_Payments': False},
        {'Account_ID': 'A004', 'Code': '6000', 'Name': 'Office Supplies', 'Type': 'EXPENSE', 'Class': 'EXPENSE', 'Status': 'ACTIVE', 'Tax_Type': 'INPUT', 'Enable_Payments': False},
        {'Account_ID': 'A005', 'Code': '2100', 'Name': 'Accounts Payable', 'Type': 'CURRENT', 'Class': 'LIABILITY', 'Status': 'ACTIVE', 'Tax_Type': '', 'Enable_Payments': False}
    ]

    return {
        'contacts': contacts,
        'invoices': invoices,
        'accounts': accounts
    }

def create_financial_excel_export():
    """Create Excel file with REAL Xero financial data in multiple sheets"""
    # Fetch real financial data from Xero
    financial_data = fetch_xero_financial_data()

    # Check if we have real data or errors
    if "error" in financial_data:
        # Create a minimal Excel with error information
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            error_data = {
                'Status': ['Error'],
                'Message': [financial_data["error"]],
                'Timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            }
            error_df = pd.DataFrame(error_data)
            error_df.to_excel(writer, sheet_name='Error', index=False)
        output.seek(0)
        return output

    # Create Excel writer object
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        # Summary Sheet
        summary_data = {
            'Metric': [
                'Total Outstanding Invoices',
                'Total Invoice Amount',
                'Total Customers',
                'Total Suppliers',
                'Total Accounts',
                'Export Date'
            ],
            'Value': [
                len([inv for inv in financial_data['invoices'] if inv['Status'] != 'PAID']),
                f"${sum(inv['Total'] for inv in financial_data['invoices']):,.2f}",
                len([c for c in financial_data['contacts'] if c['Is_Customer']]),
                len([c for c in financial_data['contacts'] if c['Is_Supplier']]),
                len(financial_data['accounts']),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Contacts Sheet
        if financial_data['contacts']:
            contacts_df = pd.DataFrame(financial_data['contacts'])
            contacts_df.to_excel(writer, sheet_name='Contacts', index=False)

        # Invoices Sheet
        if financial_data['invoices']:
            invoices_df = pd.DataFrame(financial_data['invoices'])
            invoices_df.to_excel(writer, sheet_name='Invoices', index=False)

        # Accounts Sheet
        if financial_data['accounts']:
            accounts_df = pd.DataFrame(financial_data['accounts'])
            accounts_df.to_excel(writer, sheet_name='Accounts', index=False)

        # Outstanding Invoices Analysis
        outstanding_invoices = [inv for inv in financial_data['invoices'] if inv['Amount_Due'] > 0]
        if outstanding_invoices:
            outstanding_df = pd.DataFrame(outstanding_invoices)
            outstanding_df = outstanding_df.sort_values('Due_Date')
            outstanding_df.to_excel(writer, sheet_name='Outstanding Invoices', index=False)

        # Revenue Analysis by Customer
        revenue_by_customer = {}
        for inv in financial_data['invoices']:
            customer = inv['Contact_Name']
            if customer not in revenue_by_customer:
                revenue_by_customer[customer] = 0
            revenue_by_customer[customer] += inv['Total']

        revenue_data = {
            'Customer': list(revenue_by_customer.keys()),
            'Total_Revenue': list(revenue_by_customer.values())
        }
        revenue_df = pd.DataFrame(revenue_data)
        revenue_df = revenue_df.sort_values('Total_Revenue', ascending=False)
        revenue_df.to_excel(writer, sheet_name='Revenue by Customer', index=False)

    output.seek(0)
    return output

def save_financial_export_to_file():
    """Save financial export to exports directory"""
    exports_dir = os.path.join(os.path.dirname(__file__), 'exports')
    os.makedirs(exports_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'financial_export_{timestamp}.xlsx'
    filepath = os.path.join(exports_dir, filename)

    excel_data = create_financial_excel_export()

    with open(filepath, 'wb') as f:
        f.write(excel_data.getvalue())

    return filepath, filename