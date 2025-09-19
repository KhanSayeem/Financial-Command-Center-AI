# Test data
data = {
  "xero_data": {
    "sources": ["xero"],
    "stripe_error": "Expired API Key provided...",
    "xero": {
      "accounts_count": 54,
      "invoices_count": 13,
      "last_invoice": "INV-0011",
      "tenant_id": "94386dc8-8051-4c3d-a427-96cfd1bca892"
    }
  }
}

# Test the exact condition from JavaScript
xero_condition = bool(data.get("xero_data") and not data.get("xero_data", {}).get("error") and data.get("xero_data", {}).get("xero"))
print("Xero condition result:", xero_condition)

if xero_condition:
    print("Should execute Xero branch")
else:
    print("Should NOT execute Xero branch")
    
print("Conclusion: The Xero condition should be TRUE")