"""
Tool schemas for FCC-AI MCP methods that match GPT-4o function calling format.
These schemas define the interface between OpenAI and the MCP server.
"""

# Xero MCP Tool Schemas
xero_tools = [
    {
        "type": "function",
        "function": {
            "name": "xero_ping",
            "description": "Health check for Xero MCP server",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "xero_whoami",
            "description": "Show current tenant and simple status",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "xero_list_contacts",
            "description": "List first N contacts",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of contacts to list (default: 10)",
                        "default": 10
                    },
                    "order": {
                        "type": "string",
                        "description": "Order by field (default: Name ASC)",
                        "default": "Name ASC"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "xero_create_contact",
            "description": "Create (or upsert) a contact. Xero merges by Name if one exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Contact name"
                    },
                    "email": {
                        "type": "string",
                        "description": "Contact email address"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Contact phone number"
                    },
                    "address_line1": {
                        "type": "string",
                        "description": "Address line 1"
                    },
                    "city": {
                        "type": "string",
                        "description": "City"
                    },
                    "country": {
                        "type": "string",
                        "description": "Country"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "xero_create_invoice",
            "description": "Create a new invoice in Xero",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "The Xero contact ID for the invoice"
                    },
                    "line_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {
                                    "type": "string",
                                    "description": "Line item description"
                                },
                                "quantity": {
                                    "type": "number",
                                    "description": "Quantity (default: 1)"
                                },
                                "unit_amount": {
                                    "type": "number",
                                    "description": "Unit amount (default: 0)"
                                }
                            },
                            "required": ["description"]
                        },
                        "description": "List of line items with description, quantity, and unit_amount"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in YYYY-MM-DD format"
                    },
                    "reference": {
                        "type": "string",
                        "description": "Reference/PO number"
                    },
                    "currency_code": {
                        "type": "string",
                        "description": "Currency code (defaults to org base currency)"
                    }
                },
                "required": ["contact_id", "line_items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "xero_list_invoices",
            "description": "List invoices with optional filters including amount ranges",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "description": "Invoice type: ALL | ACCREC | ACCPAY",
                        "default": "ALL"
                    },
                    "status": {
                        "type": "string",
                        "description": "Invoice status: DRAFT, SUBMITTED, AUTHORISED, PAID, VOIDED"
                    },
                    "contact_name": {
                        "type": "string",
                        "description": "Filter by contact name"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "amount_min": {
                        "type": "number",
                        "description": "Minimum invoice amount (0 = no minimum)",
                        "default": 0.0
                    },
                    "amount_max": {
                        "type": "number",
                        "description": "Maximum invoice amount (0 = no maximum)",
                        "default": 0.0
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of invoices to list (default: 10)",
                        "default": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "xero_get_profit_loss",
            "description": "Get profit and loss statement for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "xero_get_balance_sheet",
            "description": "Get balance sheet for a specific date",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    }
                },
                "required": ["date"]
            }
        }
    }
]

# Financial Command Center Tool Schemas
fcc_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_financial_health",
            "description": "Get overall financial health score and insights",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_dashboard",
            "description": "Get comprehensive financial dashboard with key metrics",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cash_flow",
            "description": "Get cash flow analysis and projections",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Time period: monthly, quarterly, yearly",
                        "default": "monthly"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_invoices",
            "description": "Retrieve invoices with optional status, amount, and customer filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Invoice status filter (e.g., overdue, paid, pending)."
                    },
                    "amount_min": {
                        "type": "number",
                        "description": "Minimum invoice amount to include in the results."
                    },
                    "customer": {
                        "type": "string",
                        "description": "Filter invoices by customer or company name."
                    }
                },
                "required": []
            }
        }
    }
]

# Stripe Tool Schemas
stripe_tools = [
    {
        "type": "function",
        "function": {
            "name": "process_payment",
            "description": "Process a payment through Stripe",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Amount in cents"
                    },
                    "currency": {
                        "type": "string",
                        "description": "Three-letter ISO currency code",
                        "default": "usd"
                    },
                    "customer_id": {
                        "type": "string",
                        "description": "Stripe customer ID"
                    },
                    "description": {
                        "type": "string",
                        "description": "Payment description"
                    }
                },
                "required": ["amount"]
            }
        }
    }
]

# Combined tools for GPT-4o function calling
all_tools = xero_tools + fcc_tools + stripe_tools