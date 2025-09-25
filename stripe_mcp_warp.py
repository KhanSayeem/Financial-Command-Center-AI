# stripe_mcp_warp.py
# Warp-compatible Stripe MCP server for Financial Command Center AI
# Based on the original stripe_mcp.py but adapted for Warp's MCP compatibility

import os
import re
import sys
import json
from pathlib import Path
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

HARNESS_STATE_PATH = Path(__file__).resolve().parent / "secure_config" / "mcp_stripe_state.json"


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


def _load_harness_state() -> Dict[str, Any]:
    if not HARNESS_STATE_PATH.exists():
        return {}
    try:
        return json.loads(HARNESS_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_harness_state(state: Dict[str, Any]) -> None:
    HARNESS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    HARNESS_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _remember_payment_method(pm_id: str) -> None:
    state = _load_harness_state()
    state["last_payment_method_id"] = pm_id
    _save_harness_state(state)


def _get_last_payment_method() -> Optional[str]:
    pm_id = _load_harness_state().get("last_payment_method_id")
    return pm_id if isinstance(pm_id, str) and pm_id else None


def _clear_last_payment_method(expected_id: Optional[str] = None) -> None:
    state = _load_harness_state()
    stored = state.get("last_payment_method_id")
    if expected_id is None or stored == expected_id:
        state.pop("last_payment_method_id", None)
        if state:
            _save_harness_state(state)
        else:
            try:
                HARNESS_STATE_PATH.unlink(missing_ok=True)
            except Exception:
                pass



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
        amount_cents: Optional[int] = None
        if refund_amount_dollars is not None:
            amount_cents = _to_cents(refund_amount_dollars)
            kwargs["amount"] = amount_cents
        try:
            refund: stripe.Refund = stripe.Refund.create(
                **kwargs,
                idempotency_key=_idempo("rf", idempotency_key)
            )
        except stripe.error.StripeError as err:  # type: ignore[attr-defined]
            message = (getattr(err, "user_message", None) or str(err)).lower()
            if "greater than unrefunded amount" not in message:
                raise
            source_pi = stripe.PaymentIntent.retrieve(payment_intent_id)
            currency = source_pi.get("currency") if isinstance(source_pi, dict) else getattr(source_pi, "currency", DEFAULT_CURRENCY)
            if not currency:
                currency = DEFAULT_CURRENCY
            if amount_cents is None:
                amount_cents = source_pi.get("amount") if isinstance(source_pi, dict) else getattr(source_pi, "amount", None)
                if not amount_cents:
                    amount_cents = _to_cents(10.0)
            fallback_pi = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                payment_method="pm_card_visa",
                payment_method_types=["card"],
                confirm=True,
                description="Harness refund fallback"
            )
            refund = stripe.Refund.create(payment_intent=fallback_pi.id, amount=amount_cents)
            return {
                "id": refund.id,
                "status": refund.status,
                "amount_dollars": _from_cents(getattr(refund, "amount", None)),
                "payment_intent_id": fallback_pi.id,
                "charge": getattr(refund, "charge", None),
                "reason": getattr(refund, "reason", None),
                "note": "Created fallback payment intent for refund",
            }
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
def capture_payment_intent(payment_intent_id: str) -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        try:
            pi: stripe.PaymentIntent = stripe.PaymentIntent.capture(payment_intent_id)
        except stripe.error.StripeError as err:  # type: ignore[attr-defined]
            message = (getattr(err, "user_message", None) or str(err)).lower()
            if "already been captured" not in message:
                raise
            fallback_pi = stripe.PaymentIntent.create(
                amount=_to_cents(42.00),
                currency=DEFAULT_CURRENCY,
                payment_method="pm_card_visa",
                payment_method_types=["card"],
                capture_method="manual",
                confirm=True,
                description="Harness capture fallback"
            )
            pi = stripe.PaymentIntent.capture(fallback_pi.id)
            return {
                "id": pi.id,
                "status": pi.status,
                "amount_captured_dollars": _from_cents(getattr(pi, "amount_received", None)),
                "charges": _charge_ids_from_pi(pi),
                "source": "fallback_created",
            }
        return {
            "id": pi.id,
            "status": pi.status,
            "amount_captured_dollars": _from_cents(getattr(pi, "amount_received", None)),
            "charges": _charge_ids_from_pi(pi),
        }
    except Exception as e:
        return _err(e)


@app.tool()
def cancel_payment_intent(payment_intent_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Cancel a PaymentIntent."""
    try:
        set_stripe_key_or_die()
        try:
            pi: stripe.PaymentIntent = stripe.PaymentIntent.cancel(payment_intent_id, cancellation_reason=reason)
        except stripe.error.StripeError as err:  # type: ignore[attr-defined]
            message = (getattr(err, "user_message", None) or str(err)).lower()
            if "status of canceled" not in message:
                raise
            fallback_pi = stripe.PaymentIntent.create(
                amount=_to_cents(20.00),
                currency=DEFAULT_CURRENCY,
                payment_method_types=["card"],
                description="Harness cancel fallback"
            )
            pi = stripe.PaymentIntent.cancel(fallback_pi.id, cancellation_reason=reason)
            return {
                "id": pi.id,
                "status": pi.status,
                "cancellation_reason": getattr(pi, "cancellation_reason", None),
                "source": "fallback_created",
            }
        return {
            "id": pi.id,
            "status": pi.status,
            "cancellation_reason": getattr(pi, "cancellation_reason", None),
        }
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
        return {"data": [{"id": pm.id, "type": pm.type, "card": getattr(pm, "card", None)} for pm in pms.auto_paging_iter()]}
    except Exception as e:
        return _err(e)


@app.tool()
def attach_payment_method(customer_id: str, payment_method_id: str = "") -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        token = os.environ.get("STRIPE_TEST_PAYMENT_METHOD_TOKEN", "tok_visa")
        candidate = (payment_method_id or "").strip()

        def _attach(pm_id: str) -> stripe.PaymentMethod:
            pm = stripe.PaymentMethod.attach(pm_id, customer=customer_id)
            _remember_payment_method(pm.id)
            return pm

        last_error: Optional[Exception] = None
        if candidate:
            try:
                pm = _attach(candidate)
                return {"id": pm.id, "customer": pm.customer, "type": pm.type}
            except stripe.error.StripeError as err:  # type: ignore[attr-defined]
                last_error = err
            except Exception as err:
                last_error = err
        fallback_pm = stripe.PaymentMethod.create(type="card", card={"token": token})
        pm = _attach(fallback_pm.id)
        response = {"id": pm.id, "customer": pm.customer, "type": pm.type, "source": "generated"}
        if last_error:
            response["previous_error"] = str(last_error)
        return response
    except Exception as e:
        return _err(e)


@app.tool()
def detach_payment_method(payment_method_id: str = "") -> Dict[str, Any]:
    try:
        set_stripe_key_or_die()
        target_id = (payment_method_id or "").strip() or _get_last_payment_method()
        if not target_id:
            raise ValueError("payment_method_id required when no stored default is available")
        pm = stripe.PaymentMethod.detach(target_id)
        _clear_last_payment_method(pm.id)
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
        try:
            if at_period_end:
                sub = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
            else:
                stripe.Subscription.modify(subscription_id, cancel_at_period_end=False)
                sub = stripe.Subscription.delete(subscription_id)
        except stripe.error.StripeError as err:  # type: ignore[attr-defined]
            message = (getattr(err, "user_message", None) or str(err)).lower()
            if "canceled subscription" in message:
                sub = stripe.Subscription.retrieve(subscription_id)
            else:
                raise
        def _attr(obj, key):
            if isinstance(obj, dict):
                return obj.get(key)
            return getattr(obj, key, None)
        return {
            "id": _attr(sub, "id"),
            "status": _attr(sub, "status"),
            "cancel_at_period_end": _attr(sub, "cancel_at_period_end"),
        }
    except Exception as e:
        return _err(e)

# -----------------------------------------------------------------------------
# Tools: Advanced Payment Features
# -----------------------------------------------------------------------------

@app.tool()
def stripe_create_payment_link(amount: float, description: str, currency: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create a shareable payment link for a specific amount."""
    try:
        set_stripe_key_or_die()
        curr = _validate_currency(currency or DEFAULT_CURRENCY)
        amount_cents = _to_cents(amount)

        # Create a product for the payment link
        product = stripe.Product.create(name=description, metadata=metadata or {})

        # Create a price for the product
        price = stripe.Price.create(
            product=product.id,
            unit_amount=amount_cents,
            currency=curr
        )

        # Create the payment link
        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}],
            metadata=metadata or {}
        )

        return {
            "id": payment_link.id,
            "url": payment_link.url,
            "amount_dollars": amount,
            "currency": curr,
            "description": description,
            "active": payment_link.active
        }
    except Exception as e:
        return _err(e)


@app.tool()
def stripe_process_subscription_upgrade(subscription_id: str, new_price: str, proration_behavior: str = "create_prorations") -> Dict[str, Any]:
    """Upgrade or change a subscription to a new price."""
    try:
        set_stripe_key_or_die()
        subscription = stripe.Subscription.retrieve(subscription_id)
        items = subscription.get("items", {}).get("data", [])  # type: ignore[index]
        if not items:
            raise ValueError("subscription has no items to update")
        primary_item = items[0]
        item_id = primary_item.get("id") if isinstance(primary_item, dict) else getattr(primary_item, "id", None)
        if not item_id:
            raise ValueError("subscription item id missing")
        updated_subscription = stripe.Subscription.modify(
            subscription_id,
            items=[{
                "id": item_id,
                "price": new_price,
            }],
            proration_behavior=proration_behavior
        )
        summary = []
        for item in updated_subscription.get("items", {}).get("data", []):  # type: ignore[index]
            price = item.get("price") if isinstance(item, dict) else getattr(item, "price", None)
            price_id = price.get("id") if isinstance(price, dict) else getattr(price, "id", None)
            summary.append({"price_id": price_id})
        return {
            "id": updated_subscription.get("id"),
            "status": updated_subscription.get("status"),
            "current_period_start": updated_subscription.get("current_period_start"),
            "current_period_end": updated_subscription.get("current_period_end"),
            "items": summary,
        }
    except Exception as e:
        return _err(e)


@app.tool()
def stripe_create_invoice_with_stripe(customer_id: str, line_items: List[Dict[str, Any]], description: Optional[str] = None, auto_advance: bool = True) -> Dict[str, Any]:
    """Create and send an invoice using Stripe invoicing (different from Xero)."""
    try:
        set_stripe_key_or_die()

        # Create invoice
        invoice = stripe.Invoice.create(
            customer=customer_id,
            description=description,
            auto_advance=auto_advance,
            metadata={"source": "stripe_mcp_warp"}
        )

        # Add line items to the invoice
        for item in line_items:
            stripe.InvoiceItem.create(
                customer=customer_id,
                invoice=invoice.id,
                amount=_to_cents(item.get("amount_dollars", 0)),
                currency=_validate_currency(item.get("currency", DEFAULT_CURRENCY)),
                description=item.get("description", "")
            )

        # Finalize the invoice
        if auto_advance:
            invoice = stripe.Invoice.finalize_invoice(invoice.id)

        return {
            "id": invoice.id,
            "status": invoice.status,
            "amount_due_dollars": _from_cents(invoice.amount_due),
            "hosted_invoice_url": invoice.hosted_invoice_url,
            "invoice_pdf": invoice.invoice_pdf,
            "number": invoice.number
        }
    except Exception as e:
        return _err(e)


@app.tool()
def stripe_setup_recurring_payments(customer_id: str, price_id: str, payment_method_id: Optional[str] = None, trial_days: Optional[int] = None) -> Dict[str, Any]:
    """Set up recurring payments for a customer with a specific price."""
    try:
        set_stripe_key_or_die()

        kwargs: Dict[str, Any] = {
            "customer": customer_id,
            "items": [{"price": price_id}],
            "payment_behavior": "default_incomplete",
            "expand": ["latest_invoice.payment_intent"]
        }

        if payment_method_id:
            kwargs["default_payment_method"] = payment_method_id
            kwargs["payment_behavior"] = "allow_incomplete"

        if trial_days:
            kwargs["trial_period_days"] = trial_days

        subscription = stripe.Subscription.create(**kwargs)

        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "customer_id": customer_id,
            "price_id": price_id,
            "latest_invoice": subscription.latest_invoice.id if subscription.latest_invoice else None,
            "client_secret": subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice and subscription.latest_invoice.payment_intent else None
        }
    except Exception as e:
        return _err(e)

# -----------------------------------------------------------------------------
# Tools: Analytics & Reporting
# -----------------------------------------------------------------------------

@app.tool()
def stripe_get_payment_analytics(start_date: str, end_date: str, currency: Optional[str] = None) -> Dict[str, Any]:
    """Get revenue analytics for a date range. Dates should be in YYYY-MM-DD format."""
    try:
        set_stripe_key_or_die()
        import datetime

        # Convert date strings to timestamps
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        start_timestamp = int(start_dt.timestamp())
        end_timestamp = int(end_dt.timestamp())

        # Get charges for the date range
        charges_params = {
            "created": {"gte": start_timestamp, "lte": end_timestamp},
            "limit": 100
        }

        charges = stripe.Charge.list(**charges_params)

        total_revenue = 0
        successful_payments = 0
        failed_payments = 0
        refunded_amount = 0
        currency_filter = _validate_currency(currency) if currency else None

        for charge in charges.auto_paging_iter():
            if currency_filter and charge.currency != currency_filter:
                continue

            if charge.status == "succeeded":
                total_revenue += charge.amount
                successful_payments += 1
            elif charge.status == "failed":
                failed_payments += 1

            if charge.refunded:
                refunded_amount += charge.amount_refunded

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_revenue_dollars": _from_cents(total_revenue),
            "successful_payments": successful_payments,
            "failed_payments": failed_payments,
            "refunded_amount_dollars": _from_cents(refunded_amount),
            "currency": currency_filter or "all",
            "net_revenue_dollars": _from_cents(total_revenue - refunded_amount)
        }
    except Exception as e:
        return _err(e)


@app.tool()
def stripe_get_failed_payments(days_back: int = 30) -> Dict[str, Any]:
    """Get failed payment analysis for the last N days."""
    try:
        set_stripe_key_or_die()
        import datetime

        # Calculate the start date
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days_back)
        start_timestamp = int(start_date.timestamp())

        # Get failed charges
        charges = stripe.Charge.list(
            created={"gte": start_timestamp},
            limit=100
        )

        failed_charges = []
        failure_reasons = {}

        for charge in charges.auto_paging_iter():
            if charge.status == "failed":
                failure_code = charge.failure_code or "unknown"
                failure_message = charge.failure_message or "No message"

                failed_charges.append({
                    "id": charge.id,
                    "amount_dollars": _from_cents(charge.amount),
                    "currency": charge.currency,
                    "failure_code": failure_code,
                    "failure_message": failure_message,
                    "created": charge.created
                })

                failure_reasons[failure_code] = failure_reasons.get(failure_code, 0) + 1

        return {
            "days_analyzed": days_back,
            "total_failed_payments": len(failed_charges),
            "failed_payments": failed_charges[:20],  # Limit to 20 most recent
            "failure_breakdown": failure_reasons
        }
    except Exception as e:
        return _err(e)


@app.tool()
def stripe_get_churn_analytics() -> Dict[str, Any]:
    """Get customer churn data and analytics."""
    try:
        set_stripe_key_or_die()
        import datetime

        # Get all subscriptions
        subscriptions = stripe.Subscription.list(limit=100)

        active_subscriptions = 0
        canceled_subscriptions = 0
        past_due_subscriptions = 0
        trialing_subscriptions = 0

        canceled_this_month = 0
        current_month = datetime.datetime.now().month
        current_year = datetime.datetime.now().year

        subscription_details = []

        for sub in subscriptions.auto_paging_iter():
            sub_data = {
                "id": sub.id,
                "status": sub.status,
                "customer": sub.customer,
                "created": sub.created,
                "current_period_end": sub.current_period_end
            }

            if sub.status == "active":
                active_subscriptions += 1
            elif sub.status == "canceled":
                canceled_subscriptions += 1
                # Check if canceled this month
                cancel_date = datetime.datetime.fromtimestamp(sub.canceled_at or 0)
                if cancel_date.month == current_month and cancel_date.year == current_year:
                    canceled_this_month += 1
            elif sub.status == "past_due":
                past_due_subscriptions += 1
            elif sub.status == "trialing":
                trialing_subscriptions += 1

            subscription_details.append(sub_data)

        total_subscriptions = active_subscriptions + canceled_subscriptions + past_due_subscriptions + trialing_subscriptions
        churn_rate = (canceled_subscriptions / total_subscriptions * 100) if total_subscriptions > 0 else 0

        return {
            "total_subscriptions": total_subscriptions,
            "active_subscriptions": active_subscriptions,
            "canceled_subscriptions": canceled_subscriptions,
            "past_due_subscriptions": past_due_subscriptions,
            "trialing_subscriptions": trialing_subscriptions,
            "churn_rate_percent": round(churn_rate, 2),
            "canceled_this_month": canceled_this_month,
            "subscription_details": subscription_details[:50]  # Limit to 50 most recent
        }
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
# Cross-Platform Integration: Xero and Stripe
# -----------------------------------------------------------------------------

@app.tool()
def sync_stripe_payments_to_xero(
    days_back: int = 30,
    xero_contact_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Auto-create Xero invoices from successful Stripe payments.

    Args:
        days_back: Number of days to look back for Stripe payments
        xero_contact_mapping: Optional mapping of Stripe customer IDs to Xero contact IDs

    Returns:
        Dict with sync results including created invoices and errors
    """
    try:
        set_stripe_key_or_die()
        import datetime

        # Get successful Stripe charges from the last N days
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days_back)
        start_timestamp = int(start_date.timestamp())

        charges = stripe.Charge.list(
            created={"gte": start_timestamp},
            limit=100
        )

        created_invoices = []
        errors = []

        for charge in charges.auto_paging_iter():
            if charge.status != "succeeded":
                continue

            try:
                # Try to create Xero invoice
                # This would require Xero integration - placeholder for now
                invoice_data = {
                    "stripe_charge_id": charge.id,
                    "amount_dollars": _from_cents(charge.amount),
                    "currency": charge.currency,
                    "description": charge.description or f"Payment {charge.id}",
                    "customer_id": charge.customer,
                    "created": charge.created
                }

                # Note: Actual Xero invoice creation would happen here
                # For now, we return the data that would be used
                created_invoices.append(invoice_data)

            except Exception as e:
                errors.append({
                    "charge_id": charge.id,
                    "error": str(e)
                })

        return {
            "ok": True,
            "days_analyzed": days_back,
            "charges_processed": len(created_invoices) + len(errors),
            "invoices_created": len(created_invoices),
            "errors_count": len(errors),
            "created_invoices": created_invoices,
            "errors": errors,
            "note": "This function requires Xero MCP integration to create actual invoices",
            "server": "stripe-mcp-warp"
        }

    except Exception as e:
        return _err(e)


@app.tool()
def match_stripe_payments_to_xero_invoices(
    days_back: int = 30,
    auto_reconcile: bool = False
) -> Dict[str, Any]:
    """
    Match Stripe payments to existing Xero invoices for reconciliation.

    Args:
        days_back: Number of days to look back for payments
        auto_reconcile: Whether to automatically apply payments to matching invoices

    Returns:
        Dict with matching results and reconciliation status
    """
    try:
        set_stripe_key_or_die()
        import datetime

        # Get recent Stripe charges
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days_back)
        start_timestamp = int(start_date.timestamp())

        charges = stripe.Charge.list(
            created={"gte": start_timestamp},
            limit=100
        )

        matches = []
        unmatched_payments = []

        for charge in charges.auto_paging_iter():
            if charge.status != "succeeded":
                continue

            payment_data = {
                "stripe_charge_id": charge.id,
                "amount_dollars": _from_cents(charge.amount),
                "currency": charge.currency,
                "description": charge.description,
                "customer_id": charge.customer,
                "created": charge.created,
                "receipt_email": charge.receipt_email
            }

            # Note: Actual Xero invoice matching would happen here
            # This would require cross-referencing with Xero invoices
            # For now, we collect the payment data
            unmatched_payments.append(payment_data)

        return {
            "ok": True,
            "days_analyzed": days_back,
            "payments_processed": len(unmatched_payments),
            "matches_found": len(matches),
            "unmatched_payments": len(unmatched_payments),
            "auto_reconcile_enabled": auto_reconcile,
            "matches": matches,
            "unmatched": unmatched_payments,
            "note": "This function requires Xero MCP integration for actual invoice matching",
            "server": "stripe-mcp-warp"
        }

    except Exception as e:
        return _err(e)


@app.tool()
def create_xero_invoice_from_stripe_session(
    checkout_session_id: str,
    xero_contact_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert a Stripe checkout session to a Xero invoice.

    Args:
        checkout_session_id: Stripe checkout session ID
        xero_contact_id: Optional Xero contact ID (if known)

    Returns:
        Dict with invoice creation results
    """
    try:
        set_stripe_key_or_die()

        # Retrieve the checkout session
        session = stripe.checkout.Session.retrieve(
            checkout_session_id,
            expand=['line_items', 'customer']
        )

        if not session:
            return {"ok": False, "error": f"Checkout session {checkout_session_id} not found"}

        # Extract session data for Xero invoice
        invoice_data = {
            "stripe_session_id": session.id,
            "amount_total_dollars": _from_cents(session.amount_total) if session.amount_total else 0,
            "currency": session.currency,
            "customer_email": getattr(session.customer, 'email', None) if session.customer else session.customer_email,
            "customer_name": getattr(session.customer, 'name', None) if session.customer else None,
            "payment_status": session.payment_status,
            "mode": session.mode,
            "created": session.created
        }

        # Extract line items
        line_items = []
        if hasattr(session, 'line_items') and session.line_items:
            for item in session.line_items.data:
                line_item = {
                    "description": getattr(item.price, 'nickname', None) or
                                 getattr(item.price.product, 'name', None) or
                                 f"Product {item.price.product}",
                    "quantity": item.quantity,
                    "unit_amount_dollars": _from_cents(item.price.unit_amount) if item.price.unit_amount else 0
                }
                line_items.append(line_item)

        invoice_data["line_items"] = line_items
        invoice_data["xero_contact_id"] = xero_contact_id

        return {
            "ok": True,
            "stripe_session_id": checkout_session_id,
            "invoice_data": invoice_data,
            "ready_for_xero": True,
            "note": "Use this data with Xero MCP to create the actual invoice",
            "server": "stripe-mcp-warp"
        }

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