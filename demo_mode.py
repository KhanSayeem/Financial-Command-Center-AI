import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Literal, Optional


Mode = Literal["demo", "live"]


class DemoModeManager:
    """Centralized demo/live mode manager with Flask helpers and mock data.

    - Persists mode in `secure_config/app_mode.json`
    - Defaults to demo mode if not configured
    - Provides lightweight helpers for UI banners and response headers
    - Exposes simple Flask routes for toggling modes
    """

    MODE_FILE = Path("secure_config/app_mode.json")

    def __init__(self, app=None):
        self._mode: Mode = self._load_initial_mode()
        self._ensure_persisted()
        if app is not None:
            self.init_app(app)

    # ------------------------- Persistence -------------------------
    def _load_initial_mode(self) -> Mode:
        # Check if we have credentials configured first
        try:
            from setup_wizard import get_configured_credentials
            credentials = get_configured_credentials()
            has_xero = bool(credentials.get('XERO_CLIENT_ID') and credentials.get('XERO_CLIENT_SECRET'))
            has_stripe = bool(credentials.get('STRIPE_API_KEY'))
            
            # If we have credentials, default to live mode
            if has_xero or has_stripe:
                # Check if persisted file explicitly sets demo mode
                if self.MODE_FILE.exists():
                    data = json.loads(self.MODE_FILE.read_text(encoding="utf-8"))
                    m = str(data.get("mode", "live")).lower()
                    # Only honor demo mode if explicitly set
                    if m == "demo":
                        return "demo"
                return "live"
        except:
            pass
        
        # If no credentials, default to demo mode
        try:
            if self.MODE_FILE.exists():
                data = json.loads(self.MODE_FILE.read_text(encoding="utf-8"))
                m = str(data.get("mode", "demo")).lower()
                return "live" if m == "live" else "demo"
        except Exception:
            pass

        env_mode = (os.getenv("APP_MODE") or os.getenv("DEMO_MODE") or "demo").lower()
        return "live" if env_mode == "live" else "demo"

    def _ensure_persisted(self) -> None:
        try:
            self.MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.MODE_FILE.write_text(json.dumps({
                "mode": self._mode,
                "updated_at": datetime.utcnow().isoformat()
            }, indent=2), encoding="utf-8")
        except Exception:
            # Fail silently; demo mode should still work in-memory
            pass

    def set_mode(self, mode: Mode) -> Mode:
        self._mode = "live" if str(mode).lower() == "live" else "demo"
        self._ensure_persisted()
        return self._mode

    # ------------------------- Accessors --------------------------
    def get_mode(self) -> Mode:
        return self._mode

    @property
    def is_demo(self) -> bool:
        return self._mode == "demo"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mode": self._mode,
            "demo": self.is_demo,
        }

    # ------------------------- Flask glue -------------------------
    def init_app(self, app):
        from flask import g

        @app.before_request
        def _set_demo_flag():
            g.demo_mode = self.is_demo

        @app.after_request
        def _add_demo_header(resp):
            try:
                resp.headers["X-Demo-Mode"] = "1" if self.is_demo else "0"
            except Exception:
                pass
            return resp

        # Expose helpers to Jinja templates
        @app.context_processor
        def _inject_demo_vars():
            return {
                "is_demo_mode": self.is_demo,
                "demo_banner": self.banner_html(),
            }

        # Routes for toggling mode
        self.add_routes(app)

    def add_routes(self, app):
        from flask import request, jsonify, render_template_string, redirect, url_for

        @app.route("/api/mode", methods=["GET", "POST"])
        def api_mode():
            if request.method == "POST":
                body = request.get_json(silent=True) or {}
                new_mode = str(body.get("mode", "")).lower()
                if new_mode not in ("demo", "live"):
                    return jsonify({"error": "mode must be 'demo' or 'live'"}), 400
                mode = self.set_mode(new_mode)  # persist
                return jsonify({"success": True, "mode": mode})
            return jsonify(self.as_dict())

        @app.route("/admin/mode", methods=["GET", "POST"])
        def admin_mode():
            if request.method == "POST":
                new_mode = request.form.get("mode", "demo").lower()
                # If switching to live mode, check if we have credentials
                if new_mode == "live":
                    try:
                        from setup_wizard import get_configured_credentials
                        credentials = get_configured_credentials()
                        has_xero = bool(credentials.get('XERO_CLIENT_ID') and credentials.get('XERO_CLIENT_SECRET'))
                        has_stripe = bool(credentials.get('STRIPE_API_KEY'))
                        
                        # If we don't have credentials, redirect to setup page
                        if not (has_xero or has_stripe):
                            return redirect(url_for("setup_wizard"))
                    except:
                        # If there's an error checking credentials, redirect to setup
                        return redirect(url_for("setup_wizard"))
                
                self.set_mode("live" if new_mode == "live" else "demo")
                return redirect(url_for("admin_mode"))

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mode Settings - Financial Command Center</title>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; background:#f5f7fa; margin:0; padding:30px; }}
                    .card {{ background:white; max-width: 720px; margin: 0 auto; padding: 30px; border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }}
                    .badge {{ display:inline-block; padding:6px 12px; border-radius: 9999px; font-weight:600; margin-left: 10px; }}
                    .badge-demo {{ background:#fff3cd; color:#856404; }}
                    .badge-live {{ background:#d4edda; color:#155724; }}
                    .btn {{ background:#667eea; color:white; padding:10px 18px; border:none; border-radius:6px; cursor:pointer; margin-right:10px; }}
                    .btn.secondary {{ background:#6c757d; }}
                    .muted {{ color:#6c757d; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Application Mode
                        {'<span class="badge badge-demo">Demo</span>' if self.is_demo else '<span class="badge badge-live">Live</span>'}
                    </h1>
                    <p class="muted">Switch between sample data (no API keys required) and real integrations.</p>

                    <form method="POST" style="margin-top: 20px;">
                        <button class="btn" name="mode" value="demo" type="submit">Use Demo Data</button>
                        <button class="btn secondary" name="mode" value="live" type="submit">Use Real Data</button>
                    </form>

                    <div style="margin-top: 24px;">
                        <a href="/admin/dashboard">Back to Dashboard</a>
                    </div>
                </div>
            </body>
            </html>
            """
            return render_template_string(html)

    # ------------------------- UI helpers -------------------------
    def banner_html(self) -> str:
        if not self.is_demo:
            return ""
        return (
            "<div style=\"position:sticky;top:0;z-index:9999;background:#fff3cd;"
            "color:#856404;padding:10px 16px;border-bottom:1px solid #ffe8a1;"
            "font-family:Segoe UI,Arial,sans-serif;display:flex;justify-content:space-between;"
            "align-items:center;\">"
            "<div><strong>Demo Mode:</strong> You are viewing sample data. "
            "<span style=\"opacity:.85\">Connect your accounts to use real data.</span></div>"
            "<a href=\"/admin/mode\" style=\"background:#856404;color:white;padding:8px 12px;"
            "border-radius:6px;text-decoration:none;\">Upgrade to Real Data</a>"
            "</div>"
        )


# ---------------------------- Mock data ----------------------------

def make_fake_id(prefix: str) -> str:
    import secrets
    import string
    rand = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(14))
    return f"{prefix}_{rand}"


def mock_stripe_payment(amount: float, currency: str, description: Optional[str] = None) -> Dict[str, Any]:
    """Create a fake, successful Stripe-like PaymentIntent structure."""
    pid = make_fake_id("pi_demo")
    client_secret = make_fake_id("cs_demo")
    return {
        "success": True,
        "payment_intent_id": pid,
        "client_secret": client_secret,
        "amount": float(amount),
        "currency": (currency or "usd").lower(),
        "status": "succeeded",
        "description": description or "Demo payment",
        "charges": [{
            "id": make_fake_id("ch_demo"),
            "amount": int(round(float(amount) * 100)),
            "currency": (currency or "usd").lower(),
            "status": "succeeded",
            "paid": True,
            "created": int(datetime.utcnow().timestamp())
        }],
        "created": int(datetime.utcnow().timestamp())
    }


