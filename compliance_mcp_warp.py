# compliance_mcp_warp.py
# Warp-compatible compliance MCP server for Financial Command Center AI
# Based on the original compliance_mcp.py but adapted for Warp's MCP compatibility

from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import date, timedelta, datetime

from mcp.server.fastmcp import FastMCP

# -------- Optional Stripe (won't crash if unavailable) --------
try:
    import stripe  # type: ignore
except Exception:
    stripe = None  # we guard any usage

# -------- Plaid SDK (required for Plaid tools) --------
import plaid
from plaid.api import plaid_api

from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.auth_get_request import AuthGetRequest
from plaid.model.identity_get_request import IdentityGetRequest
from plaid.model.webhook_verification_key_get_request import WebhookVerificationKeyGetRequest

# ------------- App -------------
app = FastMCP("compliance-suite-warp")

# ------------- Paths (Pathlib-only, no duplicate assignments) -------------
ROOT = Path(__file__).resolve().parent

REPORTS_DIR = ROOT / "reports_warp"
AUDIT_DIR   = ROOT / "audit_warp"
REPORTS_DIR.mkdir(exist_ok=True)
AUDIT_DIR.mkdir(exist_ok=True)

PLAID_STORE_FILE       = ROOT / "plaid_store_warp.json"        # produced by your Plaid MCP
COMPLIANCE_STORE_FILE  = ROOT / "compliance_store_warp.json"   # state local to compliance
CONF_FILE              = ROOT / "compliance_config_warp.json"
BLACKLIST_FILE         = ROOT / "compliance_blacklist_warp.json"
RULES_FILE             = ROOT / "compliance_rules_warp.json"
ALERTS_FILE            = ROOT / "alerts_warp.jsonl"
AUDIT_LOG              = AUDIT_DIR / "audit_log_warp.jsonl"

# Back-compat alias if other code expects STORE_PATH (points to compliance store)
STORE_PATH = COMPLIANCE_STORE_FILE


# ------------- Small JSON helpers -------------
def _load_json(p: Path, default: Any) -> Any:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def _json_default(o):
    # make anything awkward JSON-safe
    from datetime import date, datetime
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, Path):
        return str(o)
    return str(o)



def _save_json(p: Path, data: Any) -> None:
    p.write_text(json.dumps(data, indent=2, default=_json_default), encoding="utf-8")


# ------------- Configuration / State -------------
DEFAULT_CONFIG: Dict[str, Any] = {
    "min_amount_flag_usd": 1000.0,
    "include_pending": False,
    "risk_categories": [],   # e.g., ["gambling", "crypto_exchange"]
    "currencies": ["USD"],
}

def _get_config() -> Dict[str, Any]:
    cfg = _load_json(CONF_FILE, {})
    if not cfg:
        _save_json(CONF_FILE, DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    # ensure defaults exist without clobbering user-set overrides
    merged = dict(DEFAULT_CONFIG); merged.update(cfg)
    return merged


def _now_ts() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")

def _rotate_if_big(p: Path, max_bytes: int = 5 * 1024 * 1024) -> None:
    try:
        if p.exists() and p.stat().st_size >= max_bytes:
            rotated = p.with_name(p.stem + f"_{_now_ts()}" + p.suffix)
            p.rename(rotated)
    except Exception:
        pass


def _append_audit(event: Dict[str, Any]) -> None:
    event = dict(event)
    event.setdefault("ts", datetime.utcnow().isoformat() + "Z")
    _rotate_if_big(AUDIT_LOG)  # <--- rotate if too large
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

def _load_rules() -> Dict[str, Any]:
    """
    Try to load compliance_rules_warp.json; if missing, seed a minimal default.
    """
    default_rules = {
        "high_risk_categories": ["gambling", "crypto_exchange"],
        "block_if_over_usd": 5000,
        "flag_if_merchant_matches": ["coffee shop", "random llc"]
    }
    try:
        if RULES_FILE.exists():
            return json.loads(RULES_FILE.read_text(encoding="utf-8")) or default_rules
    except Exception:
        pass
    # seed a default file for convenience
    try:
        RULES_FILE.write_text(json.dumps(default_rules, indent=2), encoding="utf-8")
    except Exception:
        pass
    return default_rules


# ------------- Plaid client utilities -------------
def _resolve_plaid_host():
    """Return a Plaid Environment value defensively across SDK versions."""
    env = os.environ.get("PLAID_ENV", "sandbox").lower()
    if env == "production":
        return getattr(plaid.Environment, "Production", plaid.Environment.Sandbox)
    if env == "development":
        return getattr(plaid.Environment, "Development", getattr(plaid.Environment, "Sandbox", plaid.Environment.Production))
    return getattr(plaid.Environment, "Sandbox", plaid.Environment.Production)


def _new_plaid_client() -> plaid_api.PlaidApi:
    client_id = os.environ.get("PLAID_CLIENT_ID")
    secret    = os.environ.get("PLAID_SECRET")
    if not client_id or not secret:
        raise RuntimeError("Set PLAID_CLIENT_ID and PLAID_SECRET in the environment.")
    cfg = plaid.Configuration(host=_resolve_plaid_host(), api_key={"clientId": client_id, "secret": secret})
    return plaid_api.PlaidApi(plaid.ApiClient(cfg))


_PLAID_CLIENT: Optional[plaid_api.PlaidApi] = None
def _plaid() -> plaid_api.PlaidApi:
    """Lazy singleton so import never explodes if env isn't set until runtime."""
    global _PLAID_CLIENT
    if _PLAID_CLIENT is None:
        _PLAID_CLIENT = _new_plaid_client()
    return _PLAID_CLIENT


def _plaid_token_for(alias_or_token: str) -> str:
    """
    Accepts:
      - a real access token (starts with 'access-')
      - an alias saved in plaid_store_warp.json or compliance_store_warp.json
      - a raw token (last resort)
    """
    s = str(alias_or_token).strip()
    if s.startswith("access-"):
        return s

    # Try multiple stores
    candidates: list[Path] = []
    try:
        candidates.append(Path(STORE_PATH))
    except Exception:
        pass

    ROOT = Path(__file__).resolve().parent
    candidates.extend([
        ROOT / "plaid_store_warp.json",
        ROOT / "compliance_store_warp.json",
    ])

    for p in candidates:
        try:
            if not p or not p.exists():
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        items = data.get("items") or {}
        if s in items and isinstance(items[s], dict) and items[s].get("access_token"):
            return items[s]["access_token"]

    # Fallback: treat input as access token
    return s

# ------------- Stripe helper (optional) -------------
def _stripe_ready() -> bool:
    key = os.environ.get("STRIPE_API_KEY")
    return bool(stripe and key)


def _init_stripe():
    if not _stripe_ready():
        raise RuntimeError("Stripe not configured. Set STRIPE_API_KEY (test or live) to enable Stripe checks.")
    stripe.api_key = os.environ["STRIPE_API_KEY"]

def _canon_text(x: Any) -> str:
    """Safe canonicalization: works for None, str, list, dict, etc."""
    if x is None:
        return ""
    if isinstance(x, (list, tuple)):
        x = " ".join(map(str, x))
    elif isinstance(x, dict):
        try:
            x = " ".join(f"{k}:{v}" for k, v in sorted(x.items()))
        except Exception:
            x = str(x)
    return " ".join(str(x).split()).lower()

try:
    BLACKLIST  # reuse if already defined elsewhere
except NameError:
    ROOT = Path(__file__).resolve().parent
    BLACKLIST = ROOT / "compliance_blacklist_warp.json"

def _bl_norm(s: str) -> str:
    return " ".join(str(s).split()).lower()

def _bl_pick_name(merchant_name=None, merchant=None, name=None) -> str:
    for v in (merchant_name, merchant, name):
        if v is not None:
            txt = str(v).strip()
            if txt:
                return txt
    raise ValueError("Provide a merchant name via 'merchant_name' (or 'merchant'/'name').")

def _bl_load() -> dict:
    if not BLACKLIST.exists():
        return {"merchants": []}
    try:
        return json.loads(BLACKLIST.read_text(encoding="utf-8"))
    except Exception:
        # corrupt or empty file; start fresh
        return {"merchants": []}

def _bl_save(data: dict) -> None:
    BLACKLIST.parent.mkdir(parents=True, exist_ok=True)
    BLACKLIST.write_text(json.dumps(data, indent=2), encoding="utf-8")

# ------------- Tools -------------

@app.tool()
def info() -> Dict[str, Any]:
    """
    Show compliance suite status, paths, and which integrations are enabled.
    """
    env = {
        "PLAID_ENV": os.environ.get("PLAID_ENV", "sandbox"),
        "PLAID_CLIENT_ID_set": bool(os.environ.get("PLAID_CLIENT_ID")),
        "PLAID_SECRET_set": bool(os.environ.get("PLAID_SECRET")),
        "STRIPE_API_KEY_set": bool(os.environ.get("STRIPE_API_KEY")),
    }
    paths = {
        "reports_dir": str(REPORTS_DIR),
        "audit_dir": str(AUDIT_DIR),
        "plaid_store_file": str(PLAID_STORE_FILE),
        "compliance_store_file": str(COMPLIANCE_STORE_FILE),
        "config_file": str(CONF_FILE),
        "blacklist_file": str(BLACKLIST_FILE),
        "rules_file": str(RULES_FILE),
        "alerts_file": str(ALERTS_FILE),
        "audit_log": str(AUDIT_LOG),
    }
    out = {
        "name": "compliance-suite-warp",
        "integrations": {
            "plaid": True,
            "stripe": _stripe_ready(),
        },
        "env": env,
        "paths": paths,
        "config": _get_config(),
    }
    _append_audit({"event": "info"})
    return out


@app.tool()
def config_set(
    min_amount_flag_usd: Optional[float] = None,
    include_pending: Optional[bool] = None,
    currencies: Optional[List[str]] = None,
    risk_categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Update compliance configuration. Only provided fields change.
    """
    cfg = _get_config()
    if min_amount_flag_usd is not None:
        cfg["min_amount_flag_usd"] = float(min_amount_flag_usd)
    if include_pending is not None:
        cfg["include_pending"] = bool(include_pending)
    if currencies is not None:
        cfg["currencies"] = [str(c).upper() for c in currencies if c]
    if risk_categories is not None:
        cfg["risk_categories"] = [str(rc).lower() for rc in risk_categories if rc]
    _save_json(CONF_FILE, cfg)
    _append_audit({"event": "config_set", "config": cfg})
    return {"ok": True, "config": cfg}


@app.tool()
def blacklist_add(
    merchant_name: Optional[str] = None,
    merchant: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Add a merchant to the blacklist. Accepts any of: merchant_name, merchant, or name.
    - Normalizes case/spacing for duplicate detection.
    - Creates the blacklist file if missing.
    """
    try:
        nm = _bl_pick_name(merchant_name, merchant, name)
    except ValueError as e:
        return {"added": False, "reason": "validation_error", "message": str(e)}

    canon = _bl_norm(nm)
    data = _bl_load()
    entries = data.get("merchants", [])

    # already present?
    for m in entries:
        if _bl_norm(m.get("name", "")) == canon or m.get("canonical") == canon:
            return {
                "added": False,
                "reason": "already_exists",
                "name": nm,
                "canonical": canon,
                "count": len(entries),
            }

    entries.append({
        "name": nm,
        "canonical": canon,
        "added_at": datetime.utcnow().isoformat() + "Z",
    })
    data["merchants"] = entries
    _bl_save(data)

    return {"added": True, "name": nm, "canonical": canon, "count": len(entries), "file": str(BLACKLIST)}

@app.tool()
def blacklist_list() -> Dict[str, Any]:
    """
    List the current blacklist entries.
    """
    bl = _load_json(BLACKLIST_FILE, {"merchants": []})
    return bl


@app.tool()
def scan_plaid_transactions(
    key: str,
    days: int = 30,
    min_amount: Optional[float] = None,
    include_pending: bool = True,
    count: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Scan Plaid transactions with safe date types, robust merchant normalization,
    blacklist checks, and optional filters.
    """
    # --- dates must be datetime.date objects for typed SDKs ---
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=max(1, int(days)))

    # --- resolve token & get client ---
    access_token = _plaid_token_for(key)
    client = _plaid()  # reuse your existing Plaid client factory

    # --- request (typed model expects date objects) ---
    req = TransactionsGetRequest(
        access_token=access_token,
        start_date=start_dt,          # <-- date object
        end_date=end_dt,              # <-- date object
        options=TransactionsGetRequestOptions(
            count=int(count),
            offset=int(offset),
            # include_personal_finance_category=True  # uncomment if you need PFC
        ),
    )
    resp = client.transactions_get(req).to_dict()
    txs = resp.get("transactions", [])

    # --- filters (safe) ---
    if min_amount is not None:
        try:
            thr = float(min_amount)
            txs = [t for t in txs if abs(float(t.get("amount", 0))) >= thr]
        except Exception:
            pass
    if not include_pending:
        txs = [t for t in txs if not bool(t.get("pending"))]

    # --- blacklist check ---
    bl = _bl_load()
    bl_set = {
        _canon_text(m.get("canonical") or m.get("name", ""))
        for m in bl.get("merchants", [])
    }

    for t in txs:
        # merchant/name can sometimes be None; normalize safely
        mname = t.get("merchant_name") or t.get("name")
        canon = _canon_text(mname)
        t["merchant_canonical"] = canon
        t["is_blacklisted"] = canon in bl_set
    
        # --- rule matching ---
    rules = _load_rules()
    hi_risk_cats = {str(x).strip().lower() for x in rules.get("high_risk_categories", [])}
    merchant_needles = [m.strip().lower() for m in rules.get("flag_if_merchant_matches", []) if m]
    block_over = float(rules.get("block_if_over_usd", 0) or 0)

    def _matches_rules(t: dict) -> list[str]:
        hits: list[str] = []
        # category match (Plaid categories may be list or string)
        cats = t.get("category") or []
        cats = [str(c).strip().lower() for c in (cats if isinstance(cats, list) else [cats])]
        if any(c in hi_risk_cats for c in cats):
            hits.append("high_risk_category")

        # merchant substring match
        canon = t.get("merchant_canonical") or _canon_text(t.get("merchant_name") or t.get("name"))
        for needle in merchant_needles:
            if needle and needle in (canon or ""):
                hits.append(f"merchant_match:{needle}")

        # amount threshold (absolute value)
        try:
            if block_over and abs(float(t.get("amount", 0))) >= block_over:
                hits.append(f"amount_over_usd_{int(block_over)}")
        except Exception:
            pass

        return hits

    for t in txs:
        t["matched_rules"] = _matches_rules(t)


    # --- report out ---
    meta = {
        "key": key,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "requested_count": int(count),
        "returned": len(txs),
        "min_amount": min_amount,
        "include_pending": include_pending,
        "blacklist_hits": sum(1 for t in txs if t.get("is_blacklisted")),
        "total_in_window": resp.get("total_transactions"),
    }

    meta["rule_hits"] = sum(1 for t in txs if t.get("matched_rules"))

    # write report file
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    out_path = (REPORTS_DIR if 'REPORTS_DIR' in globals() else Path(__file__).with_name("reports_warp"))
    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / f"plaid_scan_{key}_{start_dt}_{end_dt}.json"
    out_file.write_text(
    json.dumps({"transactions": txs, "meta": meta}, indent=2, default=_json_default),
    encoding="utf-8")

    # audit (best-effort)
    try:
        _append_audit({"event": "plaid_scan", **meta, "report_file": str(out_file)})
    except Exception:
        pass

    return {"ok": True, "report_file": str(out_file), **meta}


@app.tool()
def audit_log_tail(n: int = 100) -> Dict[str, Any]:
    """
    Return the last n audit events.
    """
    lines: List[str] = []
    try:
        with AUDIT_LOG.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        pass

    tail = [json.loads(x) for x in lines[-max(1, n):]]
    return {"events": tail}


@app.tool()
def stripe_payment_intent_status(payment_intent_id: str) -> Dict[str, Any]:
    """
    Optional: Check a Stripe PaymentIntent status (requires STRIPE_API_KEY).
    """
    _init_stripe()
    pi = stripe.PaymentIntent.retrieve(payment_intent_id)  # type: ignore[attr-defined]
    _append_audit({"event": "stripe_pi_status", "pi": payment_intent_id, "status": pi.get("status")})
    return {
        "id": pi.get("id"),
        "amount": pi.get("amount"),
        "currency": pi.get("currency"),
        "status": pi.get("status"),
        "charges": [{"id": c.get("id"), "paid": c.get("paid"), "status": c.get("status")} for c in pi.get("charges", {}).get("data", [])],
    }

@app.tool()
def ping() -> Dict[str, Any]:
    """Health check for Warp compatibility"""
    return {
        "ok": True,
        "server": app.name,
        "env": os.environ.get("PLAID_ENV", "sandbox"),
        "timestamp": datetime.utcnow().isoformat()
    }

# (Optional) Plaid webhook verification helper for server routes (not a tool)
def verify_plaid_webhook(plaid_verification_jwt: str, raw_body: bytes) -> bool:
    """
    Example of verifying Plaid webhook JWT (for use in your HTTP server).
    """
    try:
        from jose import jwt as _jwt  # local import to avoid hard dependency if unused
        unverified_header = _jwt.get_unverified_header(plaid_verification_jwt)  # type: ignore[name-defined]
        if unverified_header.get("alg") != "ES256":
            return False
        kid = unverified_header["kid"]
        key_resp = _plaid().webhook_verification_key_get(
            WebhookVerificationKeyGetRequest(key_id=kid)
        )
        jwk = key_resp.to_dict().get("key")
        claims = _jwt.decode(
            plaid_verification_jwt,
            key=jwk, algorithms=["ES256"],
            options={"verify_aud": False, "verify_iss": False},
            leeway=0,
        )
        body_hash = hashlib.sha256(raw_body).hexdigest()
        return body_hash == claims.get("request_body_sha256")
    except Exception:
        return False


# ------------- Entry -------------
if __name__ == "__main__":
    app.run()