import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token

TOKENS_DIR = Path(__file__).resolve().parent / "tokens"
TOKENS_DIR.mkdir(exist_ok=True)
TOKEN_FILE = TOKENS_DIR / "xero_token.json"

ALLOWED_KEYS = {
    "access_token",
    "refresh_token",
    "token_type",
    "expires_in",
    "expires_at",
    "scope",
    "id_token",
}


def _sanitize_token(token: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {k: v for k, v in (token or {}).items() if k in ALLOWED_KEYS}


def load_store() -> Optional[Dict[str, Any]]:
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _write_store(store: Dict[str, Any]) -> None:
    TOKEN_FILE.write_text(json.dumps(store, indent=2), encoding="utf-8")


def store_token(token: Dict[str, Any]) -> None:
    store = load_store() or {}
    sanitized = _sanitize_token(token)
    if sanitized:
        store["token"] = sanitized
    else:
        store.pop("token", None)
    _write_store(store)


def get_stored_token() -> Dict[str, Any]:
    store = load_store() or {}
    token = store.get("token")
    return token if isinstance(token, dict) else {}


def has_stored_token() -> bool:
    token = get_stored_token()
    return bool(token.get("access_token"))


def clear_token_and_tenant() -> None:
    store = load_store() or {}
    store.pop("token", None)
    store.pop("tenant_id", None)
    _write_store(store)


def save_token_and_tenant(
    token: Dict[str, Any],
    tenant_id: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> None:
    store = load_store() or {}
    store["token"] = _sanitize_token(token)
    store["tenant_id"] = tenant_id
    if client_id is None:
        client_id = os.getenv("XERO_CLIENT_ID", store.get("client_id", ""))
    if client_secret is None:
        client_secret = os.getenv("XERO_CLIENT_SECRET", store.get("client_secret", ""))
    store["client_id"] = client_id or ""
    store["client_secret"] = client_secret or ""
    _write_store(store)


def load_api_client() -> ApiClient:
    store = load_store() or {}
    oauth = OAuth2Token(
        client_id=store.get("client_id") or os.getenv("XERO_CLIENT_ID", ""),
        client_secret=store.get("client_secret") or os.getenv("XERO_CLIENT_SECRET", ""),
    )
    api_client = ApiClient(Configuration(oauth2_token=oauth))

    @api_client.oauth2_token_getter
    def _get_token():
        return get_stored_token()

    @api_client.oauth2_token_saver
    def _save_token(token):
        store_token(token or {})

    return api_client


def set_tenant_id(tenant_id: str) -> None:
    store = load_store() or {}
    store["tenant_id"] = tenant_id
    _write_store(store)


def get_tenant_id() -> str:
    store = load_store() or {}
    return store.get("tenant_id", "")
