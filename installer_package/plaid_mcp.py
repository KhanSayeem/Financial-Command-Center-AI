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

# ----------------- Local store (demo only) -----------------
STORE_PATH = os.path.join(os.path.dirname(__file__), "plaid_store.json")

def _load_store() -> Dict[str, Any]:
    if not os.path.exists(STORE_PATH):
        return {}
    with open(STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_store(d: Dict[str, Any]) -> None:
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

def _token_for(alias_or_token: str) -> str:
    store = _load_store()
    if alias_or_token.startswith(("access-", "public-")):
        return alias_or_token
    return store.get("items", {}).get(alias_or_token, {}).get("access_token") or alias_or_token

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

# Lazy singleton so import never crashes if env isnt set yet
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
    # Plaids model requires a string, not None
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
    store = _load_store()
    key = alias or item_id
    store.setdefault("items", {})[key] = {"item_id": item_id, "access_token": access_token}
    _save_store(store)
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
    store = _load_store()
    items = store.get("items", {})
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

    store = _load_store()
    if "items" in store:
        store["items"].pop(key, None)
        _save_store(store)
    return {"removed": key}

@app.tool()
def whoami() -> Dict[str, Any]:
    """
    Basic environment sanity for Plaid MCP.
    """
    return {
        "env": os.environ.get("PLAID_ENV", "sandbox"),
        "PLAID_CLIENT_ID_set": bool(os.environ.get("PLAID_CLIENT_ID")),
        "PLAID_SECRET_set": bool(os.environ.get("PLAID_SECRET")),
        "store_path": STORE_PATH,
    }


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
