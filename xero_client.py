import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token

TOKENS_DIR = Path(__file__).resolve().parent / "tokens"
TOKENS_DIR.mkdir(exist_ok=True)
TOKEN_FILE = TOKENS_DIR / "xero_token.json"
TOKEN_TIME_KEY = "token_saved_at"

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
    sanitized = {k: v for k, v in (token or {}).items() if k in ALLOWED_KEYS}
    if not sanitized:
        return {}
    scope = sanitized.get("scope")
    if isinstance(scope, str):
        sanitized["scope"] = scope.split()
    if sanitized.get("expires_at") is None:
        expires_in = sanitized.get("expires_in")
        try:
            sanitized["expires_at"] = time.time() + float(expires_in) if expires_in else sanitized.get("expires_at")
        except (TypeError, ValueError):
            sanitized.pop("expires_at", None)
    return sanitized


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
        store[TOKEN_TIME_KEY] = time.time()
    else:
        store.pop("token", None)
        store.pop(TOKEN_TIME_KEY, None)
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
    store[TOKEN_TIME_KEY] = time.time()
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

def ensure_valid_token(api_client: ApiClient, threshold_seconds: int = 120) -> None:
    store = load_store() or {}
    token = store.get("token") or {}
    if not token:
        return
    expires_at = token.get("expires_at")
    now = time.time()
    if expires_at is None:
        saved_at = store.get(TOKEN_TIME_KEY)
        expires_in = token.get("expires_in")
        try:
            if saved_at and expires_in:
                expires_at = float(saved_at) + float(expires_in)
                token["expires_at"] = expires_at
                store["token"] = token
                _write_store(store)
        except (TypeError, ValueError):
            expires_at = None
    scope = token.get("scope")
    if isinstance(scope, str):
        scope = scope.split()
    oauth = api_client.configuration.oauth2_token
    oauth.update_token(
        access_token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        scope=scope,
        expires_in=token.get("expires_in"),
        token_type=token.get("token_type", "Bearer"),
        expires_at=token.get("expires_at"),
        id_token=token.get("id_token"),
    )
    api_client.set_oauth2_token({
        "access_token": oauth.access_token,
        "refresh_token": oauth.refresh_token,
        "token_type": oauth.token_type,
        "expires_in": oauth.expires_in,
        "expires_at": oauth.expires_at,
        "scope": oauth.scope,
        "id_token": oauth.id_token,
    })
    need_refresh = expires_at is None
    if expires_at is not None:
        try:
            need_refresh = now >= float(expires_at) - threshold_seconds
        except (TypeError, ValueError):
            need_refresh = True
    if not need_refresh:
        return
    if oauth.refresh_access_token(api_client):
        new_token = {
            "access_token": oauth.access_token,
            "refresh_token": oauth.refresh_token,
            "token_type": oauth.token_type,
            "expires_in": oauth.expires_in,
            "expires_at": oauth.expires_at,
            "scope": oauth.scope,
            "id_token": oauth.id_token,
        }
        store_token(new_token)

