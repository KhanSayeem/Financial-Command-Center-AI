# webhook_server.py
# Minimal, production-friendly Stripe webhook endpoint (FastAPI)

import os
import json
import logging
from typing import Any, Dict

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse

import stripe

# --- Stripe SDK baseline (pin API version you test with)
stripe.api_version = os.environ.get("STRIPE_API_VERSION", "2024-06-20")
stripe.api_key = os.environ.get("STRIPE_API_KEY", "")  # not required for signature verification

WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")  # whsec_...

app = FastAPI(title="Stripe Webhook Server", version="1.0.0")
log = logging.getLogger("webhook")
logging.basicConfig(level=logging.INFO)


@app.get("/health")
async def health():
    return {"ok": True, "api_version": stripe.api_version}


@app.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, convert_underscores=False),  # optional injection
):
    """
    IMPORTANT:
    - We MUST use the raw request body for signature verification.
    - Do not json() / parse before verifying!
    """
    if not WEBHOOK_SECRET:
        # Fail loudly if misconfigured; Stripe will show 500 in Dashboard.
        raise HTTPException(status_code=500, detail="Missing STRIPE_WEBHOOK_SECRET")

    payload: bytes = await request.body()
    sig_header = request.headers.get("stripe-signature") or stripe_signature
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError as e:
        # Signature didnt match
        raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    evt_type = event.get("type")
    obj: Dict[str, Any] = event.get("data", {}).get("object", {}) or {}

    # --- Idempotency for webhooks:
    # Stripe may deliver events >1 time. In production, store event["id"] and skip if seen.
    # Example (pseudo):
    # if seen_in_db(event["id"]): return JSONResponse({"received": True})
    # mark_seen(event["id"])

    try:
        if evt_type == "payment_intent.succeeded":
            pi_id = obj.get("id")
            amount = obj.get("amount_received")
            currency = obj.get("currency")
            log.info(f"[webhook] PI succeeded: {pi_id} {amount} {currency}")
            # TODO: mark order as paid in your DB, send receipts, etc.

        elif evt_type == "payment_intent.payment_failed":
            pi_id = obj.get("id")
            last_err = obj.get("last_payment_error", {})
            log.warning(f"[webhook] PI failed: {pi_id} error={last_err}")
            # TODO: mark order as failed / notify support

        elif evt_type == "charge.refunded":
            charge_id = obj.get("id")
            amount_refunded = obj.get("amount_refunded")
            log.info(f"[webhook] Charge refunded: {charge_id} amount_refunded={amount_refunded}")
            # TODO: update refund status in your DB

        else:
            # Safe default: log and ack
            log.info(f"[webhook] Unhandled event: {evt_type}")

        # Always ack quickly. Do heavy work async/out-of-band if needed.
        return JSONResponse({"received": True, "id": event["id"], "type": evt_type})
    except Exception as e:
        # If your own handler crashed, return 200 anyway to avoid infinite retries, but log error.
        # Alternatively, return 500 to force retry (be sure your handler is idempotent).
        log.exception(f"Handler error for event {event.get('id')}: {e}")
        return JSONResponse({"received": True, "warning": "handler error was logged"}, status_code=200)
