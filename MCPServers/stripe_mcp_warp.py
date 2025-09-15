# stripe_mcp_warp.py
# Warp-compatible Stripe MCP server for Financial Command Center AI
# Based on the original stripe_mcp.py but adapted for Warp's MCP compatibility

import os
import re
import sys
import json
from uuid import uuid4
from typing import Optional, Dict, Any, List, Literal, Union

import stripe
from mcp.server.fastmcp import FastMCP

# -----------------------------------------------------------------------------
# Config & App
# -----------------------------------------------------------------------------

app = FastMCP("stripe-integration-warp")

# Stripe SDK global tuning (safe to set at import time)
stripe.api_version = os.environ.get("STRIPE_API_VERSION", "2024-06-20")  # pin what you test with
stripe.max_network_retries = int(os.environ.get("STRIPE_MAX_RETRIES", "2"))

# Environment toggles
def _bool_env(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}

PRODUCTION_MODE = _bool_env("MCP_STRIPE_PROD", False)  # Set to 1/true for production defaults
DEFAULT_CURRENCY = os.environ.get("STRIPE_DEFAULT_CURRENCY", "usd").lower()
ALLOWED_CURRENCIES = set(
    (os.environ.get("STRIPE_ALLOWED_CURRENCIES") or
     "usd,eur,gbp,cad,aud,inr,jpy,sgd,nzd,chf,sek,dkk").lower().split(",")
)

# quick start log
print(
    json.dumps({
        "msg": "stripe_mcp_warp starting",
        "prod": PRODUCTION_MODE,
        "api_version": stripe.api_version,
        "default_currency": DEFAULT_CURRENCY,
    }),
    file=sys.stderr,
    flush=True,
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _err(e: Exception) -> Dict[str, Any]:
    """Normalize Stripe and non-Stripe exceptions."""
    resp: Dict[str, Any] = {"error": str(e)}
    for attr in ("user_message", "code", "param", "http_status"):
        if getattr(e, attr, None):
            resp[attr] = getattr(e, attr)
    try:
        jb = getattr(e, "json_body", None)
        if jb:
            resp["json_body"] = jb
    except Exception:
        pass
    return resp

def _to_cents(amount_dollars: float) -> int:
    if amount_dollars is None:
        raise ValueError("amount_dollars is required")
    if amount_dollars <= 0:
        raise ValueError("amount_dollars must be > 0")
    return int(round(float(amount_dollars) * 100))

def _from_cents(amount_cents: Optional[int]) -> Optional[float]:
    return None if amount_cents is None else amount_cents / 100.0

def _charge_ids_from_pi(pi: stripe.PaymentIntent) -> List[str]:
    try:
        data = getattr(getattr(pi, "charges", None), "data", None)
        return [c.id for c in (data or [])]
    except Exception:
        return []

def _validate_currency(currency: str) -> str:
    c = (currency or DEFAULT_CURRENCY).lower()
    if c not in ALLOWED_CURRENCIES:
        raise ValueError(f"currency '{c}' not allowed; allowed={sorted(ALLOWED_CURRENCIES)}")
    return c

def _validate_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    if not EMAIL_RE.match(email):
        raise ValueError("customer_email is not a valid email")
    return email

def _idempo(prefix: str, provided: Optional[str] = None) -> str:
    return provided or f"{prefix}-{uuid4()}"

def set_stripe_key_or_die() -> None:
    key = os.environ.get("STRIPE_API_KEY")
    if not key:
        raise RuntimeError(
            "Set STRIPE_API_KEY in the environment before running. "
            "Example (PowerShell):  $env:STRIPE_API_KEY='sk_test_...'"
        )
    stripe.api_key = key

# -----------------------------------------------------------------------------
# Tools: Payments core
# -----------------------------------------------------------------------------

@app.tool()
def process_payment(
    amount_dollars: float,
    description: str,
    customer_email: Optional[str] = None,
    confirm_now: Optional[bool] = None,  # default depends on PRODUCTION_MODE
    payment_method_types: Optional[List[str]] = None,
    allow_redirects: Literal["always", "never", "follow_required_action"] = "never",
    test_payment_method: str = "pm_card_visa",
    currency: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
    # Connect / platform (optional)
    on_behalf_of: Optional[str] = None,
    transfer_destination: Optional[str] = None,
    application_fee_amount_dollars: Optional[float] = None,
    # Auth/Capture toggle
    capture_method: Literal["automatic", "manual"] = "automatic",
    # Future usage hint
    setup_future_usage: Optional[Literal["on_session", "off_session"]] = None,
) -> Dict[str, Any]:
    """
    Create a PaymentIntent. By default (prod), returns client_secret for client confirmation.
    In test/dev, you can set confirm_now=True to confirm server-side with a test PM.
    """
    try:
        set_stripe_key_or_die()
        amount_cents = _to_cents(amount_dollars)
        curr = _validate_currency(currency or DEFAULT_CURRENCY)
        email = _validate_email(customer_email)

        # Default confirm behavior: prod=False -> confirm by default for tests; prod=True -> client-side confirm
        if confirm_now is None:
            confirm_now = not PRODUCTION_MODE

        kwargs: Dict[str, Any] = dict(
            amount=amount_cents,
            currency=curr,
            description=description,
            capture_method=capture_method,
            metadata=metadata or {},
            automatic_payment_methods={"enabled": True, "allow_redirects": allow_redirects},
        )

        # If user specified explicit payment_method_types, DO NOT include automatic_payment_methods
        if payment_method_types:
            kwargs.pop("automatic_payment_methods", None)
            kwargs["payment_method_types"] = payment_method_types

        if email:
            kwargs["receipt_email"] = email

        # Platform / Connect fields
        if on_behalf_of:
            kwargs["on_behalf_of"] = on_behalf_of
        if transfer_destination:
            kwargs.setdefault("transfer_data", {})["destination"] = transfer_destination
        if application_fee_amount_dollars is not None:
            fee_cents = _to_cents(application_fee_amount_dollars)
            kwargs["application_fee_amount"] = fee_cents

        if setup_future_usage:
            kwargs["setup_future_usage"] = setup_future_usage

        # Confirm server-side (mostly for tests) with a test PM
        if confirm_now:
            kwargs["payment_method"] = test_payment_method
            kwargs["confirm"] = True

        pi: stripe.PaymentIntent = stripe.PaymentIntent.create(
            **kwargs,
            idempotency_key=_idempo("pi", idempotency_key)
        )

        return {
            "id": pi.id,
            "status": pi.status,
            "amount_dollars": amount_dollars,
            "currency": curr,
            "client_secret": getattr(pi, "client_secret", None),
            "description": description,
            "confirmed": bool(confirm_now),
            "charges": _charge_ids_from_pi(pi),
            "capture_method": getattr(pi, "capture_method", None),
            "message": (
                "PaymentIntent created and confirmed."
                if confirm_now else
                "PaymentIntent created. Confirm client-side."
            ),
        }

    except Exception as e:
        return _err(e)


@app.tool()
def check_payment_status(payment_intent_id: str) -> Dict[str, Any]:
    """Retrieve a PaymentIntent and return details."""
    try:
        set_stripe_key_or_die()
        pi: stripe.PaymentIntent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return {
            "id": pi.id,
            "status": pi.status,
            "amount_dollars": _from_cents(getattr(pi, "amount", None)),
            "currency": getattr(pi, "currency", None),
            "description": getattr(pi, "description", None),
            "charges": _charge_ids_from_pi(pi),
            "confirmation_method": getattr(pi, "confirmation_method", None),
            "latest_charge": getattr(pi, "latest_charge", None),
            "capture_method": getattr(pi, "capture_method", None),
        }
    except Exception as e:
        return _err(e)


@app.tool()
def process_refund(
    payment_intent_id: str,
    refund_amount_dollars: Optional[float] = None,
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """Refund a PaymentIntent (full if no amount specified)."""
    try:
        set_stripe_key_or_die()
        kwargs: Dict[str, Any] = {"payment_intent": payment_intent_id}
        if refund_amount_dollars is not None:
            cents = _to_cents(refund_amount_dollars)
            kwargs["amount"] = cents

        refund: stripe.Refund = stripe.Refund.create(
            **kwargs,
            idempotency_key=_idempo("rf", idempotency_key)
        )
        return {
            "id": refund.id,
            "status": refund.status,
            "amount_dollars": _from_cents(getattr(refund, "amount", None)),
            "payment_intent_id": payment_intent_id,
            "charge": getattr(refund, "charge", None),
            "reason": getattr(refund, "reason", None),
        }
    except Exception as e:
        return _err(e)


@app.tool()
def capture_payment_intent(
    payment_intent_id: str,
    amount_to_capture_dollars: Optional[float] = None,
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """Capture funds for a previously authorized PaymentIntent."""
    try:
        set_stripe_key_or_die()
        kwargs: Dict[str, Any] = {}
        if amount_to_capture_dollars is not None:
            kwargs["amount_to_capture"] = _to_cents(amount_to_capture_dollars)

        pi: stripe.PaymentIntent = stripe.PaymentIntent.capture(
            payment_intent_id,
            **kwargs,
            idempotency_key=_idempo("cap", idempotency_key)
        )
        return {"id": pi.id, "status": pi.status, "amount_received": _from_cents(getattr(pi, "amount_received", None))}
    except Exception as e:
        return _err(e)


@app.tool()
def cancel_payment_intent(payment_intent_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Cancel a PaymentIntent."""
    try:
        set_stripe_key_or_die()
        pi: stripe.PaymentIntent = stripe.PaymentIntent.cancel(payment_intent_id, cancellation_reason=reason)
        return {"id": pi.id, "status": pi.status, "cancellation_reason": getattr(pi, "cancellation_reason", None)}
    except Exception as e:
        return _err(e)

# -----------------------------------------------------------------------------
# Tools: Customers & Payment Methods
# -----------------------------------------------------------------------------

@app.tool()
def create_customer(email: Optional[str] = None, name: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        if email:
            _validate_email(email)
        cust: stripe.Customer = stripe.Customer.create(email=email, name=name, metadata=metadata or {})
        return {"id": cust.id, "email": cust.email, "name": cust.name}
    except Exception as e:
        return _err(e)


@app.tool()
def create_setup_intent(customer_id: Optional[str] = None, payment_method_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """Create a SetupIntent to save a card for future use."""
    try:
        set_stripe_key_or_die()
        kwargs: Dict[str, Any] = {}
        if customer_id:
            kwargs["customer"] = customer_id
        if payment_method_types:
            kwargs["payment_method_types"] = payment_method_types
        si: stripe.SetupIntent = stripe.SetupIntent.create(**kwargs)
        return {"id": si.id, "status": si.status, "client_secret": getattr(si, "client_secret", None)}
    except Exception as e:
        return _err(e)


@app.tool()
def list_payment_methods(customer_id: str, type: Literal["card", "us_bank_account", "sepa_debit"] = "card") -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        pms = stripe.PaymentMethod.list(customer=customer_id, type=type)
        return {"data": [{"id": pm.id, "type": pm.type, "card": getattr(pm, "card", None)} for pm in pms.auto_paging_iter(limit=20)]}
    except Exception as e:
        return _err(e)


@app.tool()
def attach_payment_method(customer_id: str, payment_method_id: str) -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        pm = stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
        return {"id": pm.id, "customer": pm.customer, "type": pm.type}
    except Exception as e:
        return _err(e)


@app.tool()
def detach_payment_method(payment_method_id: str) -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        pm = stripe.PaymentMethod.detach(payment_method_id)
        return {"id": pm.id, "customer": pm.customer, "type": pm.type}
    except Exception as e:
        return _err(e)

# -----------------------------------------------------------------------------
# Tools: Products, Prices, Checkout, Subscriptions
# -----------------------------------------------------------------------------

@app.tool()
def create_product(name: str, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        p: stripe.Product = stripe.Product.create(name=name, metadata=metadata or {})
        return {"id": p.id, "name": p.name}
    except Exception as e:
        return _err(e)


@app.tool()
def create_price(product_id: str, unit_amount_dollars: float, currency: Optional[str] = None, recurring_interval: Optional[str] = None) -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        curr = _validate_currency(currency or DEFAULT_CURRENCY)
        kwargs: Dict[str, Any] = {"product": product_id, "unit_amount": _to_cents(unit_amount_dollars), "currency": curr}
        if recurring_interval:
            kwargs["recurring"] = {"interval": recurring_interval}
        price: stripe.Price = stripe.Price.create(**kwargs)
        return {"id": price.id, "unit_amount_dollars": _from_cents(price.unit_amount), "currency": price.currency, "recurring": getattr(price, "recurring", None)}
    except Exception as e:
        return _err(e)


@app.tool()
def create_checkout_session(
    mode: Literal["payment", "subscription"],
    line_items: List[Dict[str, Any]],
    success_url: str,
    cancel_url: str,
    customer_id: Optional[str] = None,
    allow_promotion_codes: bool = False,
    metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Hosted Checkout (handles redirects automatically)."""
    try:
        set_stripe_key_or_die()
        kwargs: Dict[str, Any] = {
            "mode": mode,
            "line_items": line_items,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "allow_promotion_codes": allow_promotion_codes,
            "metadata": metadata or {},
        }
        if customer_id:
            kwargs["customer"] = customer_id
        cs: stripe.checkout.Session = stripe.checkout.Session.create(**kwargs)
        return {"id": cs.id, "url": getattr(cs, "url", None), "mode": cs.mode}
    except Exception as e:
        return _err(e)


@app.tool()
def create_subscription(customer_id: str, price_id: str, trial_days: Optional[int] = None, payment_behavior: str = "default_incomplete") -> Dict[str, Any]:
    """Create a subscription (incomplete until payment is confirmed)."""
    try:
        set_stripe_key_or_die()
        kwargs: Dict[str, Any] = {"customer": customer_id, "items": [{"price": price_id}], "payment_behavior": payment_behavior}
        if trial_days:
            kwargs["trial_period_days"] = trial_days
        sub: stripe.Subscription = stripe.Subscription.create(**kwargs)
        return {"id": sub.id, "status": sub.status, "latest_invoice": getattr(sub, "latest_invoice", None)}
    except Exception as e:
        return _err(e)


@app.tool()
def cancel_subscription(subscription_id: str, at_period_end: bool = False) -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        sub: stripe.Subscription = stripe.Subscription.modify(subscription_id, cancel_at_period_end=at_period_end)
        if not at_period_end:
            sub = stripe.Subscription.delete(subscription_id)
        return {"id": sub.id, "status": sub.status, "cancel_at_period_end": getattr(sub, "cancel_at_period_end", None)}
    except Exception as e:
        return _err(e)

# -----------------------------------------------------------------------------
# Tools: Search & Reporting
# -----------------------------------------------------------------------------

@app.tool()
def list_payments(limit: int = 10, customer_id: Optional[str] = None) -> Dict[str, Any]:
    """List recent charges (Payments)."""
    try:
        set_stripe_key_or_die()
        kwargs: Dict[str, Any] = {"limit": min(max(limit, 1), 100)}
        if customer_id:
            kwargs["customer"] = customer_id
        charges = stripe.Charge.list(**kwargs)
        out = []
        for ch in charges:
            out.append({
                "id": ch.id,
                "amount_dollars": _from_cents(ch.amount),
                "currency": ch.currency,
                "status": ch.status,
                "payment_intent": getattr(ch, "payment_intent", None),
                "created": ch.created,
            })
        return {"data": out}
    except Exception as e:
        return _err(e)


@app.tool()
def retrieve_charge(charge_id: str) -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        ch = stripe.Charge.retrieve(charge_id)
        return {"id": ch.id, "amount_dollars": _from_cents(ch.amount), "currency": ch.currency, "status": ch.status}
    except Exception as e:
        return _err(e)


@app.tool()
def retrieve_refund(refund_id: str) -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        rf = stripe.Refund.retrieve(refund_id)
        return {"id": rf.id, "amount_dollars": _from_cents(rf.amount), "status": rf.status, "charge": getattr(rf, "charge", None)}
    except Exception as e:
        return _err(e)

# -----------------------------------------------------------------------------
# Tools: Webhook verification (paste payload + header)
# -----------------------------------------------------------------------------

@app.tool()
def verify_webhook(payload: str, signature_header: str, webhook_secret: str) -> Dict[str, Any]:
    """
    Verify a Stripe webhook payload & signature. Returns event summary if valid.
    Use this to validate incoming events from your HTTP endpoint.
    """
    try:
        set_stripe_key_or_die()  # not strictly needed for verification, but keeps env consistent
        event = stripe.Webhook.construct_event(payload=payload, sig_header=signature_header, secret=webhook_secret)
        return {"ok": True, "id": event["id"], "type": event["type"], "created": event["created"]}
    except Exception as e:
        return _err(e)

# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------

@app.tool()
def ping() -> Dict[str, Any]:
    return {"ok": True, "server": app.name, "prod": PRODUCTION_MODE}

# -----------------------------------------------------------------------------
# Entry
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Optional early validation if running directly (uv run python stripe_mcp_warp.py)
    set_stripe_key_or_die()
    app.run()  # stdio transport by default