# compliance_mcp.py
# A lightweight compliance MCP: scan Plaid transactions, manage rules/blacklist,
# write audit logs & JSON reports. Stripe usage is optional (loaded lazily).

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
from plaid_client_store import get_access_token as get_stored_plaid_token, store_item as store_plaid_item, load_store as plaid_load_store, save_store as plaid_save_store, get_all_items as plaid_get_all_items

from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.auth_get_request import AuthGetRequest
from plaid.model.identity_get_request import IdentityGetRequest
from plaid.model.webhook_verification_key_get_request import WebhookVerificationKeyGetRequest

# ------------- App -------------
app = FastMCP("compliance-suite")

# ------------- Paths (Pathlib-only, no duplicate assignments) -------------
ROOT = Path(__file__).resolve().parent

REPORTS_DIR = ROOT / "reports"
AUDIT_DIR   = ROOT / "audit"
REPORTS_DIR.mkdir(exist_ok=True)
AUDIT_DIR.mkdir(exist_ok=True)

PLAID_STORE_FILE       = ROOT / "plaid_store.json"        # produced by your Plaid MCP
COMPLIANCE_STORE_FILE  = ROOT / "compliance_store.json"   # state local to compliance
CONF_FILE              = ROOT / "compliance_config.json"
BLACKLIST_FILE         = ROOT / "compliance_blacklist.json"
RULES_FILE             = ROOT / "compliance_rules.json"
ALERTS_FILE            = ROOT / "alerts.jsonl"
AUDIT_LOG              = AUDIT_DIR / "audit_log.jsonl"

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
    Try to load compliance_rules.json; if missing, seed a minimal default.
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
    """Lazy singleton so import never explodes if env isnÃ¢â‚¬â„¢t set until runtime."""
    global _PLAID_CLIENT
    if _PLAID_CLIENT is None:
        _PLAID_CLIENT = _new_plaid_client()
    return _PLAID_CLIENT


def _plaid_token_for(alias_or_token: str) -> str:
    """Resolve Plaid access token from key or alias."""
    alias = (alias_or_token or "").strip()
    if alias.startswith(("access-", "public-")):
        return alias
    stored = get_stored_plaid_token(alias)
    if stored:
        return stored
    if alias:
        return alias
    raise RuntimeError("Provide a Plaid access token or item alias.")


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
    BLACKLIST = ROOT / "compliance_blacklist.json"

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
        "name": "compliance-suite",
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
    out_path = (REPORTS_DIR if 'REPORTS_DIR' in globals() else Path(__file__).with_name("reports"))
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


# (Optional) Plaid webhook verification helper for server routes (not a tool)
def verify_plaid_webhook(plaid_verification_jwt: str, raw_body: bytes) -> bool:
    """
    Example of verifying Plaid webhook JWT (for use in your HTTP server).
    """
    try:
        unverified_header = jwt.get_unverified_header(plaid_verification_jwt)  # type: ignore[name-defined]
        if unverified_header.get("alg") != "ES256":
            return False
        kid = unverified_header["kid"]
        key_resp = _plaid().webhook_verification_key_get(
            WebhookVerificationKeyGetRequest(key_id=kid)
        )
        jwk = key_resp.to_dict().get("key")
        from jose import jwt as _jwt  # local import to avoid hard dependency if unused
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


# ------------- Advanced Compliance & Monitoring Tools -------------

@app.tool()
def compliance_generate_tax_report(
    year: int,
    key: Optional[str] = None,
    include_categories: Optional[List[str]] = None,
    format: str = "json"
) -> Dict[str, Any]:
    """
    Generate tax compliance report from transaction data.

    Args:
        year: Tax year to generate report for
        key: Plaid access token or alias (optional, uses all available if not provided)
        include_categories: List of transaction categories to include
        format: Output format (json, csv)
    """
    try:
        import csv
        from io import StringIO

        # Date range for the tax year
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        # Get transactions for the year
        if key:
            access_token = _plaid_token_for(key)
            client = _plaid()

            req = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(count=500)
            )
            resp = client.transactions_get(req).to_dict()
            transactions = resp.get("transactions", [])
        else:
            transactions = []

        # Process transactions for tax purposes
        tax_data = {
            "year": year,
            "total_income": 0.0,
            "total_expenses": 0.0,
            "deductible_expenses": 0.0,
            "business_expenses": 0.0,
            "categories": {},
            "summary": {}
        }

        deductible_categories = ["Professional Services", "Office Supplies", "Travel", "Business"]

        for tx in transactions:
            amount = abs(float(tx.get("amount", 0)))
            category = tx.get("category", ["Other"])
            category_main = category[0] if isinstance(category, list) and category else str(category)

            # Filter by categories if specified
            if include_categories and category_main not in include_categories:
                continue

            # Income vs expense classification
            if float(tx.get("amount", 0)) < 0:  # Negative amounts are typically income
                tax_data["total_income"] += amount
            else:
                tax_data["total_expenses"] += amount

                # Check if deductible
                if any(cat in category_main for cat in deductible_categories):
                    tax_data["deductible_expenses"] += amount
                    tax_data["business_expenses"] += amount

            # Category breakdown
            if category_main not in tax_data["categories"]:
                tax_data["categories"][category_main] = {"count": 0, "total": 0.0}
            tax_data["categories"][category_main]["count"] += 1
            tax_data["categories"][category_main]["total"] += amount

        # Summary calculations
        tax_data["summary"] = {
            "net_income": tax_data["total_income"] - tax_data["total_expenses"],
            "potential_tax_savings": tax_data["deductible_expenses"] * 0.25,  # Estimated 25% tax rate
            "transaction_count": len(transactions)
        }

        # Generate report file
        report_filename = f"tax_report_{year}_{_now_ts()}.{format}"
        report_path = REPORTS_DIR / report_filename

        if format.lower() == "csv":
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["Category", "Count", "Total Amount", "Type"])
            for cat, data in tax_data["categories"].items():
                writer.writerow([cat, data["count"], data["total"], "Business" if cat in deductible_categories else "Personal"])
            report_content = output.getvalue()
            report_path.write_text(report_content, encoding="utf-8")
        else:
            _save_json(report_path, tax_data)

        _append_audit({"event": "tax_report_generated", "year": year, "format": format, "report_file": str(report_path)})

        return {
            "ok": True,
            "year": year,
            "report_file": str(report_path),
            "format": format,
            "summary": tax_data["summary"],
            "deductible_expenses": tax_data["deductible_expenses"],
            "total_transactions": len(transactions)
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
def compliance_detect_suspicious_patterns(
    key: str,
    days: int = 30,
    min_frequency: int = 5,
    amount_threshold: float = 1000.0,
    velocity_threshold: float = 5000.0
) -> Dict[str, Any]:
    """
    Advanced fraud detection using pattern analysis.

    Args:
        key: Plaid access token or alias
        days: Number of days to analyze
        min_frequency: Minimum frequency for pattern detection
        amount_threshold: Threshold for large transaction alerts
        velocity_threshold: Threshold for high-velocity spending alerts
    """
    try:
        # Get transaction data
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=max(1, int(days)))

        access_token = _plaid_token_for(key)
        client = _plaid()

        req = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_dt,
            end_date=end_dt,
            options=TransactionsGetRequestOptions(count=500)
        )
        resp = client.transactions_get(req).to_dict()
        transactions = resp.get("transactions", [])

        suspicious_patterns = {
            "round_number_transactions": [],
            "high_frequency_merchants": [],
            "large_transactions": [],
            "high_velocity_periods": [],
            "unusual_time_patterns": [],
            "duplicate_amounts": []
        }

        # Pattern 1: Round number transactions (potential card testing)
        for tx in transactions:
            amount = abs(float(tx.get("amount", 0)))
            if amount % 10 == 0 and amount >= 100:  # Round amounts over $100
                suspicious_patterns["round_number_transactions"].append({
                    "transaction_id": tx.get("transaction_id"),
                    "amount": amount,
                    "merchant": tx.get("merchant_name") or tx.get("name"),
                    "date": tx.get("date")
                })

        # Pattern 2: High frequency merchants
        merchant_counts = {}
        for tx in transactions:
            merchant = tx.get("merchant_name") or tx.get("name", "Unknown")
            merchant_counts[merchant] = merchant_counts.get(merchant, 0) + 1

        for merchant, count in merchant_counts.items():
            if count >= min_frequency:
                total_amount = sum(abs(float(tx.get("amount", 0))) for tx in transactions
                                 if (tx.get("merchant_name") or tx.get("name")) == merchant)
                suspicious_patterns["high_frequency_merchants"].append({
                    "merchant": merchant,
                    "transaction_count": count,
                    "total_amount": total_amount
                })

        # Pattern 3: Large transactions
        for tx in transactions:
            amount = abs(float(tx.get("amount", 0)))
            if amount >= amount_threshold:
                suspicious_patterns["large_transactions"].append({
                    "transaction_id": tx.get("transaction_id"),
                    "amount": amount,
                    "merchant": tx.get("merchant_name") or tx.get("name"),
                    "date": tx.get("date"),
                    "category": tx.get("category")
                })

        # Pattern 4: High velocity spending (daily)
        daily_spending = {}
        for tx in transactions:
            tx_date = tx.get("date")
            amount = abs(float(tx.get("amount", 0)))
            if tx_date:
                daily_spending[tx_date] = daily_spending.get(tx_date, 0) + amount

        for date_str, amount in daily_spending.items():
            if amount >= velocity_threshold:
                suspicious_patterns["high_velocity_periods"].append({
                    "date": date_str,
                    "total_amount": amount,
                    "transaction_count": sum(1 for tx in transactions if tx.get("date") == date_str)
                })

        # Pattern 5: Duplicate amounts (potential duplicate charges)
        amount_counts = {}
        for tx in transactions:
            amount = abs(float(tx.get("amount", 0)))
            amount_key = f"{amount}_{tx.get('merchant_name') or tx.get('name', 'Unknown')}"
            if amount_key not in amount_counts:
                amount_counts[amount_key] = []
            amount_counts[amount_key].append(tx)

        for amount_key, txs in amount_counts.items():
            if len(txs) >= 2:  # Same amount from same merchant multiple times
                suspicious_patterns["duplicate_amounts"].append({
                    "amount": abs(float(txs[0].get("amount", 0))),
                    "merchant": txs[0].get("merchant_name") or txs[0].get("name"),
                    "occurrences": len(txs),
                    "dates": [tx.get("date") for tx in txs]
                })

        # Calculate risk score
        risk_score = 0
        risk_score += len(suspicious_patterns["round_number_transactions"]) * 2
        risk_score += len(suspicious_patterns["high_frequency_merchants"]) * 3
        risk_score += len(suspicious_patterns["large_transactions"]) * 5
        risk_score += len(suspicious_patterns["high_velocity_periods"]) * 10
        risk_score += len(suspicious_patterns["duplicate_amounts"]) * 4

        # Generate alert file
        alert_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "account_key": key,
            "analysis_period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "risk_score": risk_score,
            "patterns": suspicious_patterns,
            "total_transactions_analyzed": len(transactions)
        }

        alert_file = REPORTS_DIR / f"fraud_analysis_{key}_{_now_ts()}.json"
        _save_json(alert_file, alert_data)

        _append_audit({"event": "fraud_detection", "risk_score": risk_score, "patterns_found": sum(len(p) for p in suspicious_patterns.values())})

        return {
            "ok": True,
            "risk_score": risk_score,
            "alert_file": str(alert_file),
            "patterns_detected": {k: len(v) for k, v in suspicious_patterns.items()},
            "recommendations": _generate_fraud_recommendations(risk_score, suspicious_patterns)
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


def _generate_fraud_recommendations(risk_score: int, patterns: dict) -> List[str]:
    """Generate fraud prevention recommendations based on detected patterns."""
    recommendations = []

    if risk_score >= 50:
        recommendations.append("HIGH RISK: Review account immediately and consider temporary spending limits")
    elif risk_score >= 20:
        recommendations.append("MEDIUM RISK: Monitor account closely for additional suspicious activity")

    if patterns["round_number_transactions"]:
        recommendations.append("Consider blocking round-number transactions over $100 from new merchants")

    if patterns["high_frequency_merchants"]:
        recommendations.append("Review high-frequency merchant relationships and set transaction limits")

    if patterns["large_transactions"]:
        recommendations.append("Implement mandatory approval for transactions over threshold")

    if patterns["duplicate_amounts"]:
        recommendations.append("Enable duplicate transaction detection and alerts")

    return recommendations


@app.tool()
def compliance_export_audit_trail(
    days: int = 30,
    format: str = "json",
    include_pii: bool = False
) -> Dict[str, Any]:
    """
    Export comprehensive audit trail for regulatory compliance.

    Args:
        days: Number of days of audit data to export
        format: Export format (json, csv)
        include_pii: Whether to include personally identifiable information
    """
    try:
        # Read audit log
        audit_events = []
        try:
            with AUDIT_LOG.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        event_date = datetime.fromisoformat(event.get("ts", "").replace("Z", "+00:00"))
                        if (datetime.utcnow() - event_date.replace(tzinfo=None)).days <= days:
                            if not include_pii:
                                # Remove PII fields
                                event.pop("email", None)
                                event.pop("customer_email", None)
                                if "config" in event and isinstance(event["config"], dict):
                                    event["config"].pop("email", None)
                            audit_events.append(event)
                    except (json.JSONDecodeError, ValueError):
                        continue
        except FileNotFoundError:
            audit_events = []

        # Generate compliance report
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat() + "Z",
            "period": {
                "start": (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z",
                "end": datetime.utcnow().isoformat() + "Z"
            },
            "total_events": len(audit_events),
            "events": audit_events,
            "event_summary": {},
            "compliance_metadata": {
                "data_retention_policy": f"{days} days",
                "pii_included": include_pii,
                "export_format": format,
                "regulatory_framework": "SOX, PCI-DSS, GDPR"
            }
        }

        # Event summary
        event_types = {}
        for event in audit_events:
            event_type = event.get("event", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
        export_data["event_summary"] = event_types

        # Generate export file
        export_filename = f"audit_trail_export_{_now_ts()}.{format}"
        export_path = REPORTS_DIR / export_filename

        if format.lower() == "csv":
            import csv
            from io import StringIO
            output = StringIO()
            writer = csv.writer(output)

            # CSV headers
            headers = ["timestamp", "event", "user", "action", "result", "details"]
            writer.writerow(headers)

            for event in audit_events:
                writer.writerow([
                    event.get("ts", ""),
                    event.get("event", ""),
                    event.get("user", "system"),
                    event.get("action", ""),
                    event.get("result", ""),
                    json.dumps({k: v for k, v in event.items() if k not in headers})
                ])

            export_path.write_text(output.getvalue(), encoding="utf-8")
        else:
            _save_json(export_path, export_data)

        _append_audit({"event": "audit_export", "days": days, "format": format, "total_events": len(audit_events)})

        return {
            "ok": True,
            "export_file": str(export_path),
            "total_events": len(audit_events),
            "period_days": days,
            "format": format,
            "file_size_bytes": export_path.stat().st_size if export_path.exists() else 0
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
def compliance_set_spending_limits(
    daily_limit: Optional[float] = None,
    monthly_limit: Optional[float] = None,
    merchant_limits: Optional[Dict[str, float]] = None,
    category_limits: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Set and manage spending limits for budget monitoring.

    Args:
        daily_limit: Maximum daily spending limit
        monthly_limit: Maximum monthly spending limit
        merchant_limits: Per-merchant spending limits
        category_limits: Per-category spending limits
    """
    try:
        # Load existing limits
        limits_file = ROOT / "spending_limits.json"
        current_limits = _load_json(limits_file, {
            "daily_limit": None,
            "monthly_limit": None,
            "merchant_limits": {},
            "category_limits": {},
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_updated": None
        })

        # Update limits
        if daily_limit is not None:
            current_limits["daily_limit"] = float(daily_limit)
        if monthly_limit is not None:
            current_limits["monthly_limit"] = float(monthly_limit)
        if merchant_limits:
            current_limits["merchant_limits"].update({k: float(v) for k, v in merchant_limits.items()})
        if category_limits:
            current_limits["category_limits"].update({k: float(v) for k, v in category_limits.items()})

        current_limits["last_updated"] = datetime.utcnow().isoformat() + "Z"

        # Save updated limits
        _save_json(limits_file, current_limits)

        _append_audit({
            "event": "spending_limits_updated",
            "daily_limit": current_limits.get("daily_limit"),
            "monthly_limit": current_limits.get("monthly_limit"),
            "merchant_limits_count": len(current_limits.get("merchant_limits", {})),
            "category_limits_count": len(current_limits.get("category_limits", {}))
        })

        return {
            "ok": True,
            "limits": current_limits,
            "limits_file": str(limits_file)
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------- Business Intelligence Tools -------------

@app.tool()
def generate_cash_flow_forecast(
    key: str,
    forecast_days: int = 30,
    historical_days: int = 90
) -> Dict[str, Any]:
    """
    Generate predictive cash flow forecast based on historical transaction patterns.

    Args:
        key: Plaid access token or alias
        forecast_days: Number of days to forecast
        historical_days: Number of historical days to analyze for patterns
    """
    try:
        # Get historical transaction data
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=historical_days)

        access_token = _plaid_token_for(key)
        client = _plaid()

        req = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_dt,
            end_date=end_dt,
            options=TransactionsGetRequestOptions(count=500)
        )
        resp = client.transactions_get(req).to_dict()
        transactions = resp.get("transactions", [])

        def _parse_tx_date(raw: str):
            raw = (raw or '').strip()
            if not raw:
                raise ValueError
            cleaned = raw.replace('Z', '').strip()
            try:
                return datetime.fromisoformat(cleaned).date()
            except ValueError:
                pass
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%m/%d/%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(cleaned, fmt).date()
                except ValueError:
                    continue
            raise ValueError

        # Analyze patterns
        daily_inflow = {}
        daily_outflow = {}
        weekly_patterns = {}
        monthly_patterns = {}

        for tx in transactions:
            tx_date = tx.get("date")
            amount = float(tx.get("amount", 0))

            if tx_date:
                try:
                    date_obj = _parse_tx_date(tx_date)
                except ValueError:
                    continue
                day_of_week = date_obj.weekday()
                day_of_month = date_obj.day

                if amount < 0:  # Income
                    daily_inflow[tx_date] = daily_inflow.get(tx_date, 0) + abs(amount)
                else:  # Expense
                    daily_outflow[tx_date] = daily_outflow.get(tx_date, 0) + amount

                # Weekly patterns
                if day_of_week not in weekly_patterns:
                    weekly_patterns[day_of_week] = {"inflow": [], "outflow": []}
                if amount < 0:
                    weekly_patterns[day_of_week]["inflow"].append(abs(amount))
                else:
                    weekly_patterns[day_of_week]["outflow"].append(amount)

                # Monthly patterns
                if day_of_month not in monthly_patterns:
                    monthly_patterns[day_of_month] = {"inflow": [], "outflow": []}
                if amount < 0:
                    monthly_patterns[day_of_month]["inflow"].append(abs(amount))
                else:
                    monthly_patterns[day_of_month]["outflow"].append(amount)

        # Calculate averages
        avg_weekly_inflow = {}
        avg_weekly_outflow = {}
        for day, data in weekly_patterns.items():
            avg_weekly_inflow[day] = sum(data["inflow"]) / len(data["inflow"]) if data["inflow"] else 0
            avg_weekly_outflow[day] = sum(data["outflow"]) / len(data["outflow"]) if data["outflow"] else 0

        # Generate forecast
        forecast = []
        current_balance = sum(daily_inflow.values()) - sum(daily_outflow.values())

        for i in range(forecast_days):
            forecast_date = end_dt + timedelta(days=i + 1)
            day_of_week = forecast_date.weekday()

            predicted_inflow = avg_weekly_inflow.get(day_of_week, 0)
            predicted_outflow = avg_weekly_outflow.get(day_of_week, 0)
            predicted_net = predicted_inflow - predicted_outflow
            current_balance += predicted_net

            forecast.append({
                "date": forecast_date.isoformat(),
                "predicted_inflow": round(predicted_inflow, 2),
                "predicted_outflow": round(predicted_outflow, 2),
                "predicted_net": round(predicted_net, 2),
                "projected_balance": round(current_balance, 2),
                "confidence": "medium"  # Could be enhanced with statistical models
            })

        # Generate insights
        insights = []
        if any(day["projected_balance"] < 0 for day in forecast):
            insights.append("WARNING: Negative balance projected in forecast period")

        avg_daily_net = sum(day["predicted_net"] for day in forecast) / len(forecast)
        if avg_daily_net < -100:
            insights.append("ALERT: High average daily outflow projected")

        # Save forecast report
        forecast_data = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "account_key": key,
            "analysis_period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "forecast_period": forecast_days,
            "historical_transactions": len(transactions),
            "current_balance_estimate": round(current_balance - sum(day["predicted_net"] for day in forecast), 2),
            "forecast": forecast,
            "insights": insights,
            "patterns": {
                "weekly_inflow_avg": {str(k): round(v, 2) for k, v in avg_weekly_inflow.items()},
                "weekly_outflow_avg": {str(k): round(v, 2) for k, v in avg_weekly_outflow.items()}
            }
        }

        forecast_file = REPORTS_DIR / f"cash_flow_forecast_{key}_{_now_ts()}.json"
        _save_json(forecast_file, forecast_data)

        _append_audit({"event": "cash_flow_forecast", "forecast_days": forecast_days, "historical_days": historical_days})

        return {
            "ok": True,
            "forecast_file": str(forecast_file),
            "forecast_days": forecast_days,
            "insights": insights,
            "projected_balance_end": forecast[-1]["projected_balance"] if forecast else 0,
            "avg_daily_net": round(avg_daily_net, 2) if forecast else 0
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
def analyze_customer_payment_behavior(
    key: str,
    days: int = 90,
    min_transactions: int = 3
) -> Dict[str, Any]:
    """
    Analyze customer payment patterns and behavior insights.

    Args:
        key: Plaid access token or alias
        days: Number of days to analyze
        min_transactions: Minimum transactions required for pattern analysis
    """
    try:
        # Get transaction data
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=days)

        access_token = _plaid_token_for(key)
        client = _plaid()

        req = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_dt,
            end_date=end_dt,
            options=TransactionsGetRequestOptions(count=500)
        )
        resp = client.transactions_get(req).to_dict()
        transactions = resp.get("transactions", [])

        # Analyze payment behavior patterns
        merchant_analysis = {}
        category_analysis = {}
        time_patterns = {"hourly": {}, "daily": {}, "weekly": {}}
        payment_methods = {}

        for tx in transactions:
            merchant = tx.get("merchant_name") or tx.get("name", "Unknown")
            category = tx.get("category", ["Other"])
            category_main = category[0] if isinstance(category, list) and category else str(category)
            amount = abs(float(tx.get("amount", 0)))
            tx_date = tx.get("date")
            account_id = tx.get("account_id", "unknown")

            # Merchant analysis
            if merchant not in merchant_analysis:
                merchant_analysis[merchant] = {
                    "transaction_count": 0,
                    "total_amount": 0,
                    "avg_amount": 0,
                    "frequency_days": [],
                    "categories": set()
                }

            merchant_analysis[merchant]["transaction_count"] += 1
            merchant_analysis[merchant]["total_amount"] += amount
            merchant_analysis[merchant]["categories"].add(category_main)
            if tx_date:
                merchant_analysis[merchant]["frequency_days"].append(tx_date)

            # Category analysis
            if category_main not in category_analysis:
                category_analysis[category_main] = {
                    "transaction_count": 0,
                    "total_amount": 0,
                    "merchants": set(),
                    "avg_amount": 0
                }

            category_analysis[category_main]["transaction_count"] += 1
            category_analysis[category_main]["total_amount"] += amount
            category_analysis[category_main]["merchants"].add(merchant)

            # Payment method analysis (simplified)
            payment_methods[account_id] = payment_methods.get(account_id, 0) + 1

            # Time pattern analysis
            if tx_date:
                try:
                    date_obj = datetime.strptime(tx_date, "%Y-%m-%d")
                    day_of_week = date_obj.strftime("%A")

                    time_patterns["daily"][tx_date] = time_patterns["daily"].get(tx_date, 0) + 1
                    time_patterns["weekly"][day_of_week] = time_patterns["weekly"].get(day_of_week, 0) + 1
                except ValueError:
                    continue

        # Calculate averages and insights
        for merchant, data in merchant_analysis.items():
            if data["transaction_count"] > 0:
                data["avg_amount"] = data["total_amount"] / data["transaction_count"]
                data["categories"] = list(data["categories"])

                # Calculate frequency pattern
                if len(data["frequency_days"]) >= 2:
                    dates = sorted(data["frequency_days"])
                    intervals = []
                    for i in range(1, len(dates)):
                        try:
                            date1 = datetime.strptime(dates[i-1], "%Y-%m-%d")
                            date2 = datetime.strptime(dates[i], "%Y-%m-%d")
                            intervals.append((date2 - date1).days)
                        except ValueError:
                            continue
                    data["avg_frequency_days"] = sum(intervals) / len(intervals) if intervals else 0
                else:
                    data["avg_frequency_days"] = 0

        for category, data in category_analysis.items():
            if data["transaction_count"] > 0:
                data["avg_amount"] = data["total_amount"] / data["transaction_count"]
                data["merchants"] = list(data["merchants"])

        # Generate insights
        insights = []

        # Top spending categories
        top_categories = sorted(category_analysis.items(), key=lambda x: x[1]["total_amount"], reverse=True)[:5]
        insights.append(f"Top spending category: {top_categories[0][0]} (${top_categories[0][1]['total_amount']:.2f})")

        # Frequent merchants
        frequent_merchants = [m for m, data in merchant_analysis.items() if data["transaction_count"] >= min_transactions]
        insights.append(f"Frequent merchants (3+ transactions): {len(frequent_merchants)}")

        # Spending patterns
        total_amount = sum(data["total_amount"] for data in category_analysis.values())
        avg_transaction = total_amount / len(transactions) if transactions else 0
        insights.append(f"Average transaction amount: ${avg_transaction:.2f}")

        # Most active day
        if time_patterns["weekly"]:
            most_active_day = max(time_patterns["weekly"], key=time_patterns["weekly"].get)
            insights.append(f"Most active day: {most_active_day}")

        # Generate behavior report
        behavior_data = {
            "analysis_timestamp": datetime.utcnow().isoformat() + "Z",
            "account_key": key,
            "analysis_period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "total_transactions": len(transactions),
            "total_amount": round(total_amount, 2),
            "avg_transaction_amount": round(avg_transaction, 2),
            "merchant_analysis": {k: {**v, "categories": v["categories"]} for k, v in merchant_analysis.items() if v["transaction_count"] >= min_transactions},
            "category_analysis": {k: {**v, "merchants": v["merchants"]} for k, v in category_analysis.items()},
            "time_patterns": time_patterns,
            "payment_methods": payment_methods,
            "insights": insights,
            "behavior_score": min(100, len(frequent_merchants) * 10 + len(category_analysis) * 5)
        }

        behavior_file = REPORTS_DIR / f"payment_behavior_{key}_{_now_ts()}.json"
        _save_json(behavior_file, behavior_data)

        _append_audit({"event": "payment_behavior_analysis", "total_transactions": len(transactions), "analysis_days": days})

        return {
            "ok": True,
            "behavior_file": str(behavior_file),
            "total_transactions": len(transactions),
            "frequent_merchants": len(frequent_merchants),
            "top_category": top_categories[0][0] if top_categories else "None",
            "insights": insights,
            "behavior_score": behavior_data["behavior_score"]
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
def detect_revenue_anomalies(
    key: str,
    days: int = 30,
    threshold_percentage: float = 25.0,
    baseline_days: int = 90
) -> Dict[str, Any]:
    """
    Detect unusual revenue patterns and anomalies.

    Args:
        key: Plaid access token or alias
        days: Number of recent days to analyze for anomalies
        threshold_percentage: Percentage change threshold for anomaly detection
        baseline_days: Number of days to use for baseline calculation
    """
    try:
        # Get extended transaction data for baseline
        end_dt = date.today()
        baseline_start = end_dt - timedelta(days=baseline_days)
        recent_start = end_dt - timedelta(days=days)

        access_token = _plaid_token_for(key)
        client = _plaid()

        # Get baseline data
        baseline_req = TransactionsGetRequest(
            access_token=access_token,
            start_date=baseline_start,
            end_date=recent_start,
            options=TransactionsGetRequestOptions(count=500)
        )
        baseline_resp = client.transactions_get(baseline_req).to_dict()
        baseline_transactions = baseline_resp.get("transactions", [])

        # Get recent data
        recent_req = TransactionsGetRequest(
            access_token=access_token,
            start_date=recent_start,
            end_date=end_dt,
            options=TransactionsGetRequestOptions(count=500)
        )
        recent_resp = client.transactions_get(recent_req).to_dict()
        recent_transactions = recent_resp.get("transactions", [])

        # Calculate baseline metrics
        baseline_revenue = 0
        baseline_by_category = {}
        baseline_by_merchant = {}

        for tx in baseline_transactions:
            amount = float(tx.get("amount", 0))
            if amount < 0:  # Revenue (negative amounts)
                revenue = abs(amount)
                baseline_revenue += revenue

                category = tx.get("category", ["Other"])
                category_main = category[0] if isinstance(category, list) and category else str(category)
                baseline_by_category[category_main] = baseline_by_category.get(category_main, 0) + revenue

                merchant = tx.get("merchant_name") or tx.get("name", "Unknown")
                baseline_by_merchant[merchant] = baseline_by_merchant.get(merchant, 0) + revenue

        # Calculate recent metrics
        recent_revenue = 0
        recent_by_category = {}
        recent_by_merchant = {}

        for tx in recent_transactions:
            amount = float(tx.get("amount", 0))
            if amount < 0:  # Revenue
                revenue = abs(amount)
                recent_revenue += revenue

                category = tx.get("category", ["Other"])
                category_main = category[0] if isinstance(category, list) and category else str(category)
                recent_by_category[category_main] = recent_by_category.get(category_main, 0) + revenue

                merchant = tx.get("merchant_name") or tx.get("name", "Unknown")
                recent_by_merchant[merchant] = recent_by_merchant.get(merchant, 0) + revenue

        # Normalize to daily averages
        baseline_daily_avg = baseline_revenue / (baseline_days - days) if (baseline_days - days) > 0 else 0
        recent_daily_avg = recent_revenue / days if days > 0 else 0

        # Detect anomalies
        anomalies = []

        # Overall revenue anomaly
        if baseline_daily_avg > 0:
            revenue_change = ((recent_daily_avg - baseline_daily_avg) / baseline_daily_avg) * 100
            if abs(revenue_change) >= threshold_percentage:
                anomalies.append({
                    "type": "overall_revenue",
                    "change_percentage": round(revenue_change, 2),
                    "severity": "high" if abs(revenue_change) >= 50 else "medium",
                    "baseline_daily": round(baseline_daily_avg, 2),
                    "recent_daily": round(recent_daily_avg, 2),
                    "description": f"Overall revenue {'increased' if revenue_change > 0 else 'decreased'} by {abs(revenue_change):.1f}%"
                })

        # Category anomalies
        for category in set(list(baseline_by_category.keys()) + list(recent_by_category.keys())):
            baseline_cat = baseline_by_category.get(category, 0) / (baseline_days - days) if (baseline_days - days) > 0 else 0
            recent_cat = recent_by_category.get(category, 0) / days if days > 0 else 0

            if baseline_cat > 0:
                cat_change = ((recent_cat - baseline_cat) / baseline_cat) * 100
                if abs(cat_change) >= threshold_percentage:
                    anomalies.append({
                        "type": "category_revenue",
                        "category": category,
                        "change_percentage": round(cat_change, 2),
                        "severity": "high" if abs(cat_change) >= 75 else "medium",
                        "baseline_daily": round(baseline_cat, 2),
                        "recent_daily": round(recent_cat, 2),
                        "description": f"Category '{category}' revenue {'increased' if cat_change > 0 else 'decreased'} by {abs(cat_change):.1f}%"
                    })
            elif recent_cat > 0:
                # New category with revenue
                anomalies.append({
                    "type": "new_category_revenue",
                    "category": category,
                    "change_percentage": float('inf'),
                    "severity": "medium",
                    "baseline_daily": 0,
                    "recent_daily": round(recent_cat, 2),
                    "description": f"New revenue category detected: '{category}'"
                })

        # Merchant anomalies (top merchants only)
        top_merchants = sorted(baseline_by_merchant.items(), key=lambda x: x[1], reverse=True)[:10]
        for merchant, _ in top_merchants:
            baseline_merch = baseline_by_merchant.get(merchant, 0) / (baseline_days - days) if (baseline_days - days) > 0 else 0
            recent_merch = recent_by_merchant.get(merchant, 0) / days if days > 0 else 0

            if baseline_merch > 0:
                merch_change = ((recent_merch - baseline_merch) / baseline_merch) * 100
                if abs(merch_change) >= threshold_percentage:
                    anomalies.append({
                        "type": "merchant_revenue",
                        "merchant": merchant,
                        "change_percentage": round(merch_change, 2),
                        "severity": "medium",
                        "baseline_daily": round(baseline_merch, 2),
                        "recent_daily": round(recent_merch, 2),
                        "description": f"Merchant '{merchant}' revenue {'increased' if merch_change > 0 else 'decreased'} by {abs(merch_change):.1f}%"
                    })

        # Generate alert score
        alert_score = 0
        for anomaly in anomalies:
            if anomaly["severity"] == "high":
                alert_score += 10
            elif anomaly["severity"] == "medium":
                alert_score += 5

        # Generate recommendations
        recommendations = []
        if alert_score >= 30:
            recommendations.append("URGENT: Investigate major revenue changes immediately")
        elif alert_score >= 15:
            recommendations.append("IMPORTANT: Review significant revenue pattern changes")

        if any(a["type"] == "overall_revenue" and a["change_percentage"] < -30 for a in anomalies):
            recommendations.append("Consider marketing or customer retention initiatives")

        if any(a["type"] == "new_category_revenue" for a in anomalies):
            recommendations.append("Review new revenue sources for compliance and sustainability")

        # Generate anomaly report
        anomaly_data = {
            "analysis_timestamp": datetime.utcnow().isoformat() + "Z",
            "account_key": key,
            "baseline_period": {"start": baseline_start.isoformat(), "end": recent_start.isoformat()},
            "analysis_period": {"start": recent_start.isoformat(), "end": end_dt.isoformat()},
            "threshold_percentage": threshold_percentage,
            "alert_score": alert_score,
            "baseline_daily_revenue": round(baseline_daily_avg, 2),
            "recent_daily_revenue": round(recent_daily_avg, 2),
            "anomalies": anomalies,
            "recommendations": recommendations,
            "summary": {
                "total_anomalies": len(anomalies),
                "high_severity": len([a for a in anomalies if a["severity"] == "high"]),
                "medium_severity": len([a for a in anomalies if a["severity"] == "medium"])
            }
        }

        anomaly_file = REPORTS_DIR / f"revenue_anomalies_{key}_{_now_ts()}.json"
        _save_json(anomaly_file, anomaly_data)

        _append_audit({"event": "revenue_anomaly_detection", "alert_score": alert_score, "anomalies_found": len(anomalies)})

        return {
            "ok": True,
            "anomaly_file": str(anomaly_file),
            "alert_score": alert_score,
            "total_anomalies": len(anomalies),
            "high_severity_anomalies": len([a for a in anomalies if a["severity"] == "high"]),
            "recommendations": recommendations,
            "revenue_change_percentage": round(((recent_daily_avg - baseline_daily_avg) / baseline_daily_avg * 100) if baseline_daily_avg > 0 else 0, 2)
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------- Entry -------------
if __name__ == "__main__":
    app.run()
