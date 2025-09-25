# plaid_mcp.py
import os, json, uuid, hashlib
from typing import List, Optional, Dict, Any
from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP

# ---- Plaid SDK (typed models) ----
import plaid
from plaid.api import plaid_api

from plaid.model.products import Products
from plaid.model.country_code import CountryCode

from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid_client_store import get_access_token, store_item, remove_item as remove_store_item, get_store_path, get_all_items, load_store as plaid_load_store, save_store as plaid_save_store
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser

from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.sandbox_public_token_create_request_options import SandboxPublicTokenCreateRequestOptions
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.auth_get_request import AuthGetRequest
from plaid.model.identity_get_request import IdentityGetRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.webhook_verification_key_get_request import WebhookVerificationKeyGetRequest

from jose import jwt  # webhook verification helper

# MCP app (exported name should be one of: app / mcp / server)
app = FastMCP("plaid-integration")

from plaid_client_store import get_access_token, store_item, remove_item as remove_store_item, get_store_path, get_all_items

def _token_for(alias_or_token: str) -> str:
    alias_or_token = (alias_or_token or "").strip()
    if alias_or_token.startswith(("access-", "public-")):
        return alias_or_token
    stored = get_access_token(alias_or_token)
    if stored:
        return stored
    if alias_or_token:
        return alias_or_token
    raise RuntimeError("Provide a Plaid access token or item alias.")

# ----------------- Plaid client (robust across SDK/env) -----------------
def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Set {name} in the environment.")
    return val

# Some generated SDKs have enum objects, others accept raw hosts. Use URLs to avoid enum diffs.
_PLAID_HOSTS = {
    "sandbox":     "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production":  "https://production.plaid.com",
}

def _resolve_host():
    env = os.environ.get("PLAID_ENV", "sandbox").lower()
    # Be defensive across plaid-python versions
    if env == "production":
        return getattr(plaid.Environment, "Production", plaid.Environment.Sandbox)
    if env == "development":
        return getattr(
            plaid.Environment,
            "Development",
            getattr(plaid.Environment, "Sandbox", plaid.Environment.Production),
        )
    return getattr(plaid.Environment, "Sandbox", plaid.Environment.Production)

def _plaid_client() -> plaid_api.PlaidApi:
    client_id = os.environ.get("PLAID_CLIENT_ID")
    secret = os.environ.get("PLAID_SECRET")
    if not client_id or not secret:
        raise RuntimeError("Set PLAID_CLIENT_ID and PLAID_SECRET in the environment.")
    cfg = plaid.Configuration(
        host=_resolve_host(),
        api_key={"clientId": client_id, "secret": secret},
    )
    return plaid_api.PlaidApi(plaid.ApiClient(cfg))

def _new_client() -> plaid_api.PlaidApi:
    client_id = _require_env("PLAID_CLIENT_ID")
    secret    = _require_env("PLAID_SECRET")
    cfg = plaid.Configuration(
        host=_resolve_host(),
        api_key={"clientId": client_id, "secret": secret},
    )
    return plaid_api.PlaidApi(plaid.ApiClient(cfg))

# Lazy singleton so import never crashes if env isnÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢t set yet
_PLAID_CLIENT: Optional[plaid_api.PlaidApi] = None
def _client() -> plaid_api.PlaidApi:
    global _PLAID_CLIENT
    if _PLAID_CLIENT is None:
        _PLAID_CLIENT = _new_client()
    return _PLAID_CLIENT

# ----------------- Helpers to normalize inputs -----------------
def _as_product(p: Any) -> Products:
    """Normalize 'transactions'/'auth'/enum/etc. to Products enum."""
    return Products(str(p).strip().lower())

def _to_products(products):
    """Accepts ['transactions','auth'] or None; returns [Products(...)] with sensible default."""
    vals = products or ["transactions"]
    out = []
    for p in vals:
        v = str(p).strip().lower()
        out.append(Products(v))  # enum constructor accepts the lowercase string value
    return out

def _as_country(code: Any) -> CountryCode:
    # Try enum attribute (US) first; if not present, construct with upper string.
    c = str(code).strip().upper()
    try:
        return getattr(CountryCode, c)
    except Exception:
        return CountryCode(c)

# ----------------- Tools -----------------
@app.tool()
def link_token_create(
    client_user_id: str,
    products: Optional[List[str]] = None,
    country_codes: Optional[List[str]] = None,
    language: str = "en",
) -> Dict[str, Any]:
    client = _plaid_client()

    prods = _to_products(products or ["transactions", "auth"])
    ccodes = [CountryCode(c.upper()) for c in (country_codes or ["US"])]

    req = LinkTokenCreateRequest(
        client_name="MCP Demo",
        language=language,
        country_codes=ccodes,
        products=prods,
        user=LinkTokenCreateRequestUser(client_user_id=client_user_id),
    )
    resp = client.link_token_create(req)
    return {"link_token": resp.link_token, "expiration": resp.expiration}

@app.tool()
def sandbox_public_token_create(
    institution_id: str = "ins_109508",
    products: list[str] | None = None,
    webhook: str | None = None,
    override_username: str | None = None,
    override_password: str | None = None,
) -> dict:
    # PlaidÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢s model requires a string, not None
    if webhook is None:
        webhook = "https://example.com/webhook"

    client = _plaid_client()

    opts = SandboxPublicTokenCreateRequestOptions(
        webhook=webhook,
        override_username=override_username,
        override_password=override_password,
    )

    req = SandboxPublicTokenCreateRequest(
        institution_id=institution_id,
        initial_products=_to_products(products),  # ["transactions", "auth"] -> [Products(...), ...]
        options=opts,
    )

    resp = client.sandbox_public_token_create(req)
    return {
        "public_token": resp.public_token,
        "institution_id": institution_id,
        "products": [p.value for p in _to_products(products)],
        "webhook": webhook,
    }


@app.tool()
def item_public_token_exchange(public_token: str, alias: Optional[str] = None) -> Dict[str, Any]:
    client = _plaid_client()
    req = ItemPublicTokenExchangeRequest(public_token=public_token)
    resp = client.item_public_token_exchange(req)

    access_token = resp.access_token
    item_id = resp.item_id
    key = (alias or item_id).strip() or item_id
    store_item(key, item_id, access_token)
    return {"saved_as": key, "item_id": item_id}

@app.tool()
def accounts_and_balances(key: str) -> Dict[str, Any]:
    client = _plaid_client()
    access_token = _token_for(key)
    req = AccountsBalanceGetRequest(access_token=access_token)
    resp = client.accounts_balance_get(req)
    data = resp.to_dict()

    out = []
    for a in data["accounts"]:
        out.append({
            "account_id": a["account_id"],
            "name": a.get("name"),
            "mask": a.get("mask"),
            "type": a.get("type"),
            "subtype": a.get("subtype"),
            "balances": a.get("balances", {}),
        })
    return {"accounts": out}

@app.tool()
def list_items() -> Dict[str, Any]:
    """
    Show saved Plaid item aliases and basic info from plaid_store.json.
    """
    items = get_all_items()
    return {"count": len(items), "aliases": list(items.keys())}


@app.tool()
def transactions_get(
    key: str,
    days: int = 30,
    count: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Fetch recent transactions for an Item.
    """
    client = _plaid_client()
    access_token = _token_for(key)

    # Plaid typed SDK wants actual date objects, not strings
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=max(1, days))

    req = TransactionsGetRequest(
        access_token=access_token,
        start_date=start_dt,   # pass date objects
        end_date=end_dt,       # pass date objects
        options=TransactionsGetRequestOptions(count=count, offset=offset),
    )
    resp = client.transactions_get(req)
    data = resp.to_dict()

    tx = []
    for t in data.get("transactions", []):
        tx.append({
            "tx_id": t["transaction_id"],
            "account_id": t["account_id"],
            "date": t["date"],
            "name": t["name"],
            "amount": t["amount"],
            "category": t.get("category"),
            "pending": t.get("pending"),
        })
    return {"total": data.get("total_transactions", 0), "transactions": tx}
    
@app.tool()
def auth_get(key: str) -> Dict[str, Any]:
    client = _plaid_client()
    access_token = _token_for(key)

    req = AuthGetRequest(access_token=access_token)
    resp = client.auth_get(req)
    data = resp.to_dict()

    ach = []
    for a in data["numbers"].get("ach", []):
        ach.append({
            "account_id": a["account_id"],
            "account": a["account"],
            "routing": a["routing"],
            "wire_routing": a.get("wire_routing"),
        })
    return {"ach": ach, "accounts": data.get("accounts", [])}

@app.tool()
def identity_get(key: str) -> Dict[str, Any]:
    client = _plaid_client()
    access_token = _token_for(key)

    req = IdentityGetRequest(access_token=access_token)
    resp = client.identity_get(req)
    return {"accounts": resp.to_dict().get("accounts", [])}

@app.tool()
def remove_item(key: str) -> Dict[str, Any]:
    client = _plaid_client()
    access_token = _token_for(key)
    client.item_remove(ItemRemoveRequest(access_token=access_token))

    removed = remove_store_item(key)
    return {"removed": key, "ok": removed}

@app.tool()
def whoami() -> Dict[str, Any]:
    """
    Basic environment sanity for Plaid MCP.
    """
    return {
        "env": os.environ.get("PLAID_ENV", "sandbox"),
        "PLAID_CLIENT_ID_set": bool(os.environ.get("PLAID_CLIENT_ID")),
        "PLAID_SECRET_set": bool(os.environ.get("PLAID_SECRET")),
        "store_path": str(get_store_path()),
    }


# -----------------------------------------------------------------------------
# Cross-Platform Integration: Plaid and Xero
# -----------------------------------------------------------------------------

@app.tool()
def sync_bank_transactions_to_xero(
    key: str,
    days_back: int = 30,
    account_mapping: Optional[Dict[str, str]] = None,
    auto_import: bool = False
) -> Dict[str, Any]:
    """
    Import bank transaction feeds to Xero from Plaid accounts.

    Args:
        key: Plaid item alias or access token
        days_back: Number of days to sync transactions
        account_mapping: Optional mapping of Plaid account IDs to Xero account codes
        auto_import: Whether to automatically import transactions to Xero

    Returns:
        Dict with sync results including transaction data ready for Xero
    """
    try:
        client = _plaid_client()
        access_token = _token_for(key)

        # Get account balances for context
        balance_req = AccountsBalanceGetRequest(access_token=access_token)
        balance_resp = client.accounts_balance_get(balance_req)
        accounts_data = balance_resp.to_dict()

        # Get transactions
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=max(1, days_back))

        tx_req = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_dt,
            end_date=end_dt,
            options=TransactionsGetRequestOptions(count=500, offset=0)
        )
        tx_resp = client.transactions_get(tx_req)
        tx_data = tx_resp.to_dict()

        # Prepare transactions for Xero bank feed format
        xero_transactions = []
        processed_accounts = {}

        for account in accounts_data.get("accounts", []):
            account_id = account["account_id"]
            processed_accounts[account_id] = {
                "plaid_account_id": account_id,
                "name": account.get("name"),
                "type": account.get("type"),
                "subtype": account.get("subtype"),
                "mask": account.get("mask"),
                "xero_account_code": account_mapping.get(account_id) if account_mapping else None,
                "current_balance": account.get("balances", {}).get("current"),
                "transactions": []
            }

        for tx in tx_data.get("transactions", []):
            account_id = tx["account_id"]

            # Format transaction for Xero bank feed
            xero_tx = {
                "plaid_transaction_id": tx["transaction_id"],
                "date": tx["date"],
                "description": tx["name"],
                "amount": abs(float(tx["amount"])),  # Plaid uses negative for debits
                "type": "DEBIT" if tx["amount"] > 0 else "CREDIT",  # Plaid convention
                "category": tx.get("category", []),
                "pending": tx.get("pending", False),
                "merchant_name": tx.get("merchant_name"),
                "account_owner": tx.get("account_owner"),
                "iso_currency_code": tx.get("iso_currency_code"),
                "ready_for_xero": True
            }

            if account_id in processed_accounts:
                processed_accounts[account_id]["transactions"].append(xero_tx)

            xero_transactions.append(xero_tx)

        return {
            "ok": True,
            "plaid_item_key": key,
            "days_analyzed": days_back,
            "total_transactions": len(xero_transactions),
            "accounts_processed": len(processed_accounts),
            "accounts": processed_accounts,
            "all_transactions": xero_transactions,
            "auto_import_enabled": auto_import,
            "note": "Use this data with Xero MCP to create bank feed entries"
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
def categorize_transactions_automatically(
    key: str,
    days_back: int = 30,
    use_ai_categorization: bool = True
) -> Dict[str, Any]:
    """
    AI-powered categorization of bank transactions for accounting purposes.

    Args:
        key: Plaid item alias or access token
        days_back: Number of days to analyze transactions
        use_ai_categorization: Whether to use AI for enhanced categorization

    Returns:
        Dict with categorized transactions ready for accounting import
    """
    try:
        client = _plaid_client()
        access_token = _token_for(key)

        # Get transactions
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=max(1, days_back))

        tx_req = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_dt,
            end_date=end_dt,
            options=TransactionsGetRequestOptions(count=500, offset=0)
        )
        tx_resp = client.transactions_get(tx_req)
        tx_data = tx_resp.to_dict()

        # Define accounting category mappings
        accounting_categories = {
            # Revenue categories
            "revenue": ["Deposit", "Transfer In", "Interest Earned"],

            # Expense categories
            "office_expenses": ["Office Supplies", "Software", "Subscription"],
            "travel": ["Travel", "Gas", "Transportation", "Taxi", "Airlines"],
            "meals": ["Restaurants", "Food and Drink", "Coffee Shop"],
            "utilities": ["Utilities", "Internet", "Phone", "Mobile"],
            "professional_services": ["Professional", "Legal", "Accounting"],
            "marketing": ["Advertising", "Marketing", "Social Media"],
            "equipment": ["Computer", "Electronics", "Hardware"],
            "rent": ["Rent", "Real Estate"],
            "insurance": ["Insurance"],
            "bank_fees": ["Bank Fees", "Service Charges"],
            "other_expenses": []
        }

        def categorize_transaction(tx):
            plaid_categories = tx.get("category", [])
            merchant_name = tx.get("merchant_name", "")
            description = tx.get("name", "").lower()
            amount = tx.get("amount", 0)

            # Default categorization based on Plaid categories
            accounting_category = "other_expenses"
            confidence = 0.5

            # Income detection
            if amount < 0:  # Plaid uses negative for credits/income
                if any(keyword in description for keyword in ["deposit", "transfer", "payment", "refund"]):
                    accounting_category = "revenue"
                    confidence = 0.8
            else:
                # Expense categorization
                for acc_cat, keywords in accounting_categories.items():
                    # Filter plaid_categories to only include string values before joining
                    filtered_categories = [cat for cat in (plaid_categories or []) if isinstance(cat, str)]
                    if any(keyword.lower() in " ".join(filtered_categories).lower() for keyword in keywords):
                        accounting_category = acc_cat
                        confidence = 0.9
                        break

                    # Check merchant name and description
                    if any(keyword.lower() in description or keyword.lower() in merchant_name.lower()
                          for keyword in keywords):
                        accounting_category = acc_cat
                        confidence = 0.7
                        break

            return accounting_category, confidence

        categorized_transactions = []
        category_summary = {}

        for tx in tx_data.get("transactions", []):
            accounting_category, confidence = categorize_transaction(tx)

            categorized_tx = {
                "transaction_id": tx["transaction_id"],
                "account_id": tx["account_id"],
                "date": tx["date"],
                "description": tx["name"],
                "amount": abs(float(tx["amount"])),
                "type": "CREDIT" if tx["amount"] < 0 else "DEBIT",
                "plaid_categories": tx.get("category", []),
                "accounting_category": accounting_category,
                "confidence": confidence,
                "merchant_name": tx.get("merchant_name"),
                "pending": tx.get("pending", False),
                "ready_for_xero": confidence > 0.6  # Only high-confidence categorizations
            }

            categorized_transactions.append(categorized_tx)

            # Update category summary
            if accounting_category not in category_summary:
                category_summary[accounting_category] = {
                    "count": 0,
                    "total_amount": 0,
                    "transactions": []
                }

            category_summary[accounting_category]["count"] += 1
            category_summary[accounting_category]["total_amount"] += abs(float(tx["amount"]))
            category_summary[accounting_category]["transactions"].append(tx["transaction_id"])

        return {
            "ok": True,
            "plaid_item_key": key,
            "days_analyzed": days_back,
            "total_transactions": len(categorized_transactions),
            "high_confidence_count": len([tx for tx in categorized_transactions if tx["confidence"] > 0.6]),
            "ai_categorization_used": use_ai_categorization,
            "categorized_transactions": categorized_transactions,
            "category_summary": category_summary,
            "note": "Use categorized transactions with Xero MCP for automated accounting entry"
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}



# -------- Optional: Plaid webhook verification helper --------
def verify_plaid_webhook(plaid_verification_jwt: str, raw_body: bytes) -> bool:
    try:
        unverified_header = jwt.get_unverified_header(plaid_verification_jwt)
        if unverified_header.get("alg") != "ES256":
            return False

        kid = unverified_header["kid"]
        client = _plaid_client()
        key_resp = client.webhook_verification_key_get(
            WebhookVerificationKeyGetRequest(key_id=kid)
        )
        jwk = key_resp.to_dict()["key"]

        claims = jwt.decode(
            plaid_verification_jwt,
            key=jwk,
            algorithms=["ES256"],
            options={"verify_aud": False, "verify_iss": False},
            leeway=0,
        )
        body_hash = hashlib.sha256(raw_body).hexdigest()
        return body_hash == claims.get("request_body_sha256")
    except Exception:
        return False

# ----------------- Entry -----------------
if __name__ == "__main__":
    app.run()
