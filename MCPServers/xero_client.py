# xero_client.py
import os, json
from pathlib import Path
from typing import Optional, Dict
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token


TOKENS_DIR = Path(__file__).resolve().parent / "tokens"
TOKENS_DIR.mkdir(exist_ok=True)
TOKEN_FILE = TOKENS_DIR / "xero_token.json"

ALLOWED_KEYS = {"access_token","refresh_token","token_type","expires_in","expires_at","scope","id_token"}

def _sanitize_token(token: Dict) -> Dict:
    return {k: v for k, v in (token or {}).items() if k in ALLOWED_KEYS}

def save_token_and_tenant(token: Dict, tenant_id: str) -> None:
    data = {
        "token": _sanitize_token(token),
        "tenant_id": tenant_id,
        "client_id": os.getenv("XERO_CLIENT_ID", ""),
        "client_secret": os.getenv("XERO_CLIENT_SECRET", "")
    }
    TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def load_store() -> Optional[Dict]:
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

def load_api_client() -> ApiClient:
    store = load_store() or {}
    oauth = OAuth2Token(
        client_id=store.get("client_id") or os.getenv("XERO_CLIENT_ID", ""),
        client_secret=store.get("client_secret") or os.getenv("XERO_CLIENT_SECRET", "")
    )
    api_client = ApiClient(Configuration(oauth2_token=oauth))

    # token getter/saver hooks
    @api_client.oauth2_token_getter
    def _get_token():
        s = load_store() or {}
        return s.get("token")

    @api_client.oauth2_token_saver
    def _save_token(token):
        s = load_store() or {}
        s["token"] = _sanitize_token(token or {})
        TOKEN_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")

    return api_client

def set_tenant_id(tenant_id: str) -> None:
    s = load_store() or {}
    s["tenant_id"] = tenant_id
    TOKEN_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")


def get_tenant_id() -> str:
    store = load_store() or {}
    return store.get("tenant_id", "")
