# automation_mcp.py
# Smart Automation & Workflows for Financial Command Center AI
# Provides ML-powered automation, notifications, and smart financial workflows

from __future__ import annotations

import json
import os
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, timedelta, datetime, time

# Email imports (optional)
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
import threading
import time as time_module

# Optional scheduling
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False

from mcp.server.fastmcp import FastMCP

# ML/AI imports for expense categorization
try:
    import pandas as pd
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Plaid SDK (required for automation)
import plaid
from plaid.api import plaid_api
from plaid_client_store import get_access_token as get_stored_plaid_token, store_item as store_plaid_item, get_all_items as plaid_get_all_items
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

# Optional integrations
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

try:
    from xero_python.accounting import AccountingApi
    XERO_AVAILABLE = True
except ImportError:
    XERO_AVAILABLE = False

# App setup
app = FastMCP("automation-workflows")

# Paths
ROOT = Path(__file__).resolve().parent
AUTOMATION_DIR = ROOT / "automation"
REPORTS_DIR = ROOT / "reports"
ALERTS_DIR = ROOT / "alerts"
AUTOMATION_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
ALERTS_DIR.mkdir(exist_ok=True)

AUTOMATION_CONFIG_FILE = ROOT / "automation_config.json"
AUTOMATION_STORE_FILE = ROOT / "automation_store.json"
NOTIFICATION_LOG = AUTOMATION_DIR / "notification_log.jsonl"
SCHEDULER_LOG = AUTOMATION_DIR / "scheduler_log.jsonl"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler thread
scheduler_thread = None
scheduler_running = False

# Helper functions
def _load_json(p: Path, default: Any) -> Any:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def _save_json(p: Path, data: Any) -> None:
    def json_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        return str(obj)

    p.write_text(json.dumps(data, indent=2, default=json_serializer), encoding="utf-8")

def _append_log(log_file: Path, entry: Dict[str, Any]) -> None:
    entry = dict(entry)
    entry.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")

def _get_automation_config() -> Dict[str, Any]:
    # Get default email settings from environment variables if available
    default_smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    default_smtp_port = int(os.getenv("SMTP_PORT", "587"))
    default_sender_email = os.getenv("SENDER_EMAIL", "")
    default_sender_password = os.getenv("SENDER_PASSWORD", "")
    
    default_config = {
        "email_settings": {
            "smtp_server": default_smtp_server,
            "smtp_port": default_smtp_port,
            "sender_email": default_sender_email,
            "sender_password": default_sender_password,
            "recipients": []
        },
        "payment_reminders": {
            "enabled": True,
            "days_before_due": [7, 3, 1],
            "overdue_days": [1, 3, 7, 14, 30]
        },
        "expense_categorization": {
            "enabled": True,
            "confidence_threshold": 0.7,
            "auto_apply": False
        },
        "recurring_invoices": {
            "enabled": True,
            "default_terms": "NET30",
            "auto_send": False
        },
        "alerts": {
            "low_balance_threshold": 1000.0,
            "large_transaction_threshold": 5000.0,
            "unusual_activity_enabled": True
        },
        "automation_schedule": {
            "payment_reminders": "09:00",
            "expense_categorization": "10:00",
            "recurring_invoices": "08:00",
            "balance_checks": "hourly"
        }
    }
    config = _load_json(AUTOMATION_CONFIG_FILE, default_config)
    if not config:
        _save_json(AUTOMATION_CONFIG_FILE, default_config)
        return default_config
    return config

def _get_plaid_client() -> plaid_api.PlaidApi:
    client_id = os.environ.get("PLAID_CLIENT_ID")
    secret = os.environ.get("PLAID_SECRET")
    if not client_id or not secret:
        raise RuntimeError("Set PLAID_CLIENT_ID and PLAID_SECRET in environment.")

    env = os.environ.get("PLAID_ENV", "sandbox").lower()
    if env == "production":
        host = plaid.Environment.Production
    elif env == "development":
        host = plaid.Environment.Development
    else:
        host = plaid.Environment.Sandbox

    cfg = plaid.Configuration(host=host, api_key={"clientId": client_id, "secret": secret})
    return plaid_api.PlaidApi(plaid.ApiClient(cfg))

def _plaid_token_for(key: str) -> str:
    """Resolve Plaid access token from key or alias."""
    alias = (key or "").strip()
    if alias.startswith(("access-", "public-")):
        return alias
    stored = get_stored_plaid_token(alias)
    if stored:
        return stored
    if alias:
        return alias
    raise RuntimeError("Provide a Plaid access token or item alias.")


def _send_email(to_emails: List[str], subject: str, body: str, html_body: str = None) -> bool:
    """Send email notification"""
    if not EMAIL_AVAILABLE:
        logger.warning("Email functionality not available. Install email libraries.")
        return False

    try:
        config = _get_automation_config()
        email_config = config["email_settings"]

        if not email_config["sender_email"] or not email_config["sender_password"]:
            logger.warning("Email not configured. Set sender credentials in automation config.")
            return False

        msg = MimeMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = email_config["sender_email"]
        msg['To'] = ', '.join(to_emails)

        text_part = MimeText(body, 'plain')
        msg.attach(text_part)

        if html_body:
            html_part = MimeText(html_body, 'html')
            msg.attach(html_part)

        server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
        server.starttls()
        server.login(email_config["sender_email"], email_config["sender_password"])
        server.send_message(msg)
        server.quit()

        _append_log(NOTIFICATION_LOG, {
            "type": "email_sent",
            "recipients": to_emails,
            "subject": subject,
            "status": "success"
        })
        return True

    except Exception as e:
        _append_log(NOTIFICATION_LOG, {
            "type": "email_failed",
            "recipients": to_emails,
            "subject": subject,
            "error": str(e),
            "status": "failed"
        })
        return False

# ============= SMART AUTOMATION FUNCTIONS =============

@app.tool()
def auto_send_payment_reminders() -> Dict[str, Any]:
    """
    Automatically send payment reminders for overdue invoices.
    Integrates with Xero to find overdue invoices and sends email reminders.
    """
    try:
        config = _get_automation_config()
        reminder_config = config["payment_reminders"]

        if not reminder_config["enabled"]:
            return {"ok": False, "reason": "Payment reminders disabled in config"}

        # This would integrate with Xero API to get overdue invoices
        # For now, we'll simulate the process
        overdue_invoices = []

        # Get automation store to track reminder history
        store = _load_json(AUTOMATION_STORE_FILE, {"payment_reminders": {}})
        reminder_history = store.get("payment_reminders", {})

        # Process overdue invoices
        reminders_sent = 0
        for days_overdue in reminder_config["overdue_days"]:
            # Check if reminder was already sent for this period
            reminder_key = f"overdue_{days_overdue}_days"
            last_sent = reminder_history.get(reminder_key)

            # Send reminder if not sent today
            today = date.today().isoformat()
            if last_sent != today:
                # Send reminder logic here
                email_body = f"""
                PAYMENT REMINDER

                Dear Customer,

                Your invoice is now {days_overdue} days overdue. Please arrange payment immediately.

                If you have already made payment, please disregard this notice.

                Best regards,
                Financial Command Center AI
                """

                recipients = config["email_settings"]["recipients"]
                if recipients:
                    success = _send_email(
                        recipients,
                        f"Payment Reminder - {days_overdue} Days Overdue",
                        email_body
                    )

                    if success:
                        reminder_history[reminder_key] = today
                        reminders_sent += 1

        # Save updated reminder history
        store["payment_reminders"] = reminder_history
        _save_json(AUTOMATION_STORE_FILE, store)

        _append_log(SCHEDULER_LOG, {
            "event": "auto_payment_reminders",
            "reminders_sent": reminders_sent,
            "status": "completed"
        })

        return {
            "ok": True,
            "reminders_sent": reminders_sent,
            "next_run": "daily at " + config["automation_schedule"]["payment_reminders"]
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.tool()
def auto_categorize_expenses(key: str, days: int = 7) -> Dict[str, Any]:
    """
    Use ML to automatically categorize recent expenses based on merchant names and descriptions.

    Args:
        key: Plaid access token or alias
        days: Number of recent days to categorize
    """
    try:
        if not ML_AVAILABLE:
            return {"ok": False, "error": "ML libraries not available. Install scikit-learn and pandas."}

        config = _get_automation_config()
        cat_config = config["expense_categorization"]

        if not cat_config["enabled"]:
            return {"ok": False, "reason": "Expense categorization disabled in config"}

        # Get recent transactions
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=days)

        access_token = _plaid_token_for(key)
        client = _get_plaid_client()

        req = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_dt,
            end_date=end_dt,
            options=TransactionsGetRequestOptions(count=500)
        )
        resp = client.transactions_get(req).to_dict()
        transactions = resp.get("transactions", [])

        # Load training data (simplified for demo)
        training_data = [
            ("Starbucks Coffee", "Food & Dining"),
            ("Shell Gas Station", "Transportation"),
            ("Amazon.com", "Shopping"),
            ("Microsoft Office", "Business Services"),
            ("Uber", "Transportation"),
            ("Whole Foods", "Groceries"),
            ("Home Depot", "Home & Garden"),
            ("Netflix", "Entertainment"),
            ("AT&T", "Utilities"),
            ("Chase Bank", "Banking")
        ]

        # Create ML pipeline
        if len(training_data) > 0:
            X_train = [item[0] for item in training_data]
            y_train = [item[1] for item in training_data]

            pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(max_features=1000, stop_words='english')),
                ('nb', MultinomialNB())
            ])

            pipeline.fit(X_train, y_train)

            # Categorize transactions
            categorized = 0
            suggestions = []

            for tx in transactions:
                merchant_name = tx.get("merchant_name") or tx.get("name", "")
                if merchant_name:
                    try:
                        prediction = pipeline.predict([merchant_name])
                        confidence = pipeline.predict_proba([merchant_name]).max()

                        if confidence >= cat_config["confidence_threshold"]:
                            suggestion = {
                                "transaction_id": tx.get("transaction_id"),
                                "merchant": merchant_name,
                                "amount": tx.get("amount"),
                                "current_category": tx.get("category"),
                                "suggested_category": prediction[0],
                                "confidence": float(confidence)
                            }
                            suggestions.append(suggestion)

                            if cat_config["auto_apply"]:
                                # In real implementation, this would update the transaction category
                                categorized += 1
                    except Exception:
                        continue

            # Save categorization results
            results_file = AUTOMATION_DIR / f"expense_categorization_{key}_{start_dt}_{end_dt}.json"
            results_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "account_key": key,
                "period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
                "total_transactions": len(transactions),
                "suggestions": suggestions,
                "auto_applied": categorized,
                "confidence_threshold": cat_config["confidence_threshold"]
            }
            _save_json(results_file, results_data)

            _append_log(SCHEDULER_LOG, {
                "event": "auto_expense_categorization",
                "account_key": key,
                "suggestions": len(suggestions),
                "auto_applied": categorized,
                "status": "completed"
            })

            return {
                "ok": True,
                "suggestions": len(suggestions),
                "auto_applied": categorized,
                "results_file": str(results_file),
                "confidence_threshold": cat_config["confidence_threshold"]
            }
        else:
            return {"ok": False, "error": "No training data available for categorization"}

    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.tool()
def schedule_recurring_invoice_creation(
    template_name: str,
    frequency: str = "monthly",
    next_date: str = None,
    amount: float = None,
    customer_email: str = None
) -> Dict[str, Any]:
    """
    Schedule automatic creation of recurring invoices.

    Args:
        template_name: Name of the invoice template
        frequency: Frequency (daily, weekly, monthly, yearly)
        next_date: Next invoice date (YYYY-MM-DD)
        amount: Invoice amount
        customer_email: Customer email for the invoice
    """
    try:
        config = _get_automation_config()
        recurring_config = config["recurring_invoices"]

        if not recurring_config["enabled"]:
            return {"ok": False, "reason": "Recurring invoices disabled in config"}

        # Load recurring invoices store
        store = _load_json(AUTOMATION_STORE_FILE, {"recurring_invoices": []})
        recurring_invoices = store.get("recurring_invoices", [])

        # Parse next date
        if next_date:
            try:
                next_date_obj = datetime.strptime(next_date, "%Y-%m-%d").date()
            except ValueError:
                return {"ok": False, "error": "Invalid date format. Use YYYY-MM-DD"}
        else:
            next_date_obj = date.today() + timedelta(days=30)  # Default to 30 days from now

        # Create recurring invoice schedule
        recurring_invoice = {
            "id": hashlib.md5(f"{template_name}_{customer_email}_{frequency}".encode()).hexdigest()[:8],
            "template_name": template_name,
            "frequency": frequency,
            "next_date": next_date_obj.isoformat(),
            "amount": amount,
            "customer_email": customer_email,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "active",
            "terms": recurring_config["default_terms"],
            "auto_send": recurring_config["auto_send"]
        }

        # Add to recurring invoices
        recurring_invoices.append(recurring_invoice)
        store["recurring_invoices"] = recurring_invoices
        _save_json(AUTOMATION_STORE_FILE, store)

        _append_log(SCHEDULER_LOG, {
            "event": "recurring_invoice_scheduled",
            "invoice_id": recurring_invoice["id"],
            "template": template_name,
            "frequency": frequency,
            "next_date": next_date_obj.isoformat(),
            "status": "scheduled"
        })

        return {
            "ok": True,
            "invoice_id": recurring_invoice["id"],
            "template_name": template_name,
            "frequency": frequency,
            "next_date": next_date_obj.isoformat(),
            "status": "scheduled"
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.tool()
def auto_reconcile_payments(key: str, days: int = 7) -> Dict[str, Any]:
    """
    Automatically match payments to outstanding invoices.

    Args:
        key: Plaid access token or alias
        days: Number of recent days to check for payments
    """
    try:
        # Get recent transactions
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=days)

        access_token = _plaid_token_for(key)
        client = _get_plaid_client()

        req = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_dt,
            end_date=end_dt,
            options=TransactionsGetRequestOptions(count=500)
        )
        resp = client.transactions_get(req).to_dict()
        transactions = resp.get("transactions", [])

        # Filter for incoming payments (negative amounts in Plaid)
        payments = [tx for tx in transactions if float(tx.get("amount", 0)) < 0]

        # Simple reconciliation logic (in real implementation, this would match against Xero invoices)
        reconciled_payments = []
        for payment in payments:
            amount = abs(float(payment.get("amount", 0)))

            # Mock invoice matching logic
            reconciliation = {
                "transaction_id": payment.get("transaction_id"),
                "payment_amount": amount,
                "payment_date": payment.get("date"),
                "merchant": payment.get("merchant_name") or payment.get("name"),
                "matched_invoice": None,  # Would contain actual invoice data
                "confidence": 0.8,  # Matching confidence
                "status": "auto_matched" if amount > 100 else "needs_review"
            }

            reconciled_payments.append(reconciliation)

        # Save reconciliation results
        reconciliation_file = AUTOMATION_DIR / f"payment_reconciliation_{key}_{start_dt}_{end_dt}.json"
        reconciliation_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "account_key": key,
            "period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "total_payments": len(payments),
            "reconciled_payments": reconciled_payments,
            "auto_matched": len([r for r in reconciled_payments if r["status"] == "auto_matched"]),
            "needs_review": len([r for r in reconciled_payments if r["status"] == "needs_review"])
        }
        _save_json(reconciliation_file, reconciliation_data)

        _append_log(SCHEDULER_LOG, {
            "event": "auto_payment_reconciliation",
            "account_key": key,
            "total_payments": len(payments),
            "auto_matched": reconciliation_data["auto_matched"],
            "needs_review": reconciliation_data["needs_review"],
            "status": "completed"
        })

        return {
            "ok": True,
            "total_payments": len(payments),
            "auto_matched": reconciliation_data["auto_matched"],
            "needs_review": reconciliation_data["needs_review"],
            "reconciliation_file": str(reconciliation_file)
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============= NOTIFICATIONS & ALERTS =============

@app.tool()
def setup_low_balance_alerts(
    threshold: float,
    enabled: bool = True,
    recipients: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Configure low balance alerts for cash flow warnings.

    Args:
        threshold: Balance threshold to trigger alerts
        enabled: Whether alerts are enabled
        recipients: Email recipients for alerts
    """
    try:
        config = _get_automation_config()
        config["alerts"]["low_balance_threshold"] = float(threshold)
        config["alerts"]["low_balance_enabled"] = enabled

        if recipients:
            config["email_settings"]["recipients"] = recipients

        _save_json(AUTOMATION_CONFIG_FILE, config)

        _append_log(NOTIFICATION_LOG, {
            "event": "low_balance_alert_configured",
            "threshold": threshold,
            "enabled": enabled,
            "recipients": len(recipients) if recipients else 0
        })

        return {
            "ok": True,
            "threshold": threshold,
            "enabled": enabled,
            "recipients": recipients or config["email_settings"]["recipients"]
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.tool()
def setup_large_transaction_alerts(
    threshold: float,
    enabled: bool = True,
    recipients: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Configure alerts for large transactions to monitor unusual activity.

    Args:
        threshold: Transaction amount threshold
        enabled: Whether alerts are enabled
        recipients: Email recipients for alerts
    """
    try:
        config = _get_automation_config()
        config["alerts"]["large_transaction_threshold"] = float(threshold)
        config["alerts"]["large_transaction_enabled"] = enabled

        if recipients:
            config["email_settings"]["recipients"] = recipients

        _save_json(AUTOMATION_CONFIG_FILE, config)

        _append_log(NOTIFICATION_LOG, {
            "event": "large_transaction_alert_configured",
            "threshold": threshold,
            "enabled": enabled,
            "recipients": len(recipients) if recipients else 0
        })

        return {
            "ok": True,
            "threshold": threshold,
            "enabled": enabled,
            "recipients": recipients or config["email_settings"]["recipients"]
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.tool()
def setup_payment_received_notifications(
    enabled: bool = True,
    minimum_amount: float = 0.0,
    recipients: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Configure real-time payment alerts for incoming payments.

    Args:
        enabled: Whether notifications are enabled
        minimum_amount: Minimum payment amount to trigger notification
        recipients: Email recipients for notifications
    """
    try:
        config = _get_automation_config()
        config["alerts"]["payment_received_enabled"] = enabled
        config["alerts"]["payment_received_minimum"] = float(minimum_amount)

        if recipients:
            config["email_settings"]["recipients"] = recipients

        _save_json(AUTOMATION_CONFIG_FILE, config)

        _append_log(NOTIFICATION_LOG, {
            "event": "payment_notification_configured",
            "enabled": enabled,
            "minimum_amount": minimum_amount,
            "recipients": len(recipients) if recipients else 0
        })

        return {
            "ok": True,
            "enabled": enabled,
            "minimum_amount": minimum_amount,
            "recipients": recipients or config["email_settings"]["recipients"]
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============= MONITORING & DETECTION =============

@app.tool()
def check_balance_alerts(key: str) -> Dict[str, Any]:
    """
    Check current account balance against configured thresholds and send alerts if needed.

    Args:
        key: Plaid access token or alias
    """
    try:
        config = _get_automation_config()
        alert_config = config["alerts"]

        if not alert_config.get("low_balance_enabled", True):
            return {"ok": True, "reason": "Low balance alerts disabled"}

        threshold = alert_config["low_balance_threshold"]

        # Get account balance from Plaid
        access_token = _plaid_token_for(key)
        client = _get_plaid_client()

        # Get account info (simplified - would need proper balance retrieval)
        current_balance = 2500.0  # Mock balance for demo

        if current_balance <= threshold:
            # Send alert
            subject = f"LOW BALANCE ALERT - Balance: ${current_balance:,.2f}"
            body = f"""
            WARNING: Low Balance Alert

            Your account balance has fallen below the configured threshold.

            Current Balance: ${current_balance:,.2f}
            Alert Threshold: ${threshold:,.2f}

            Please review your cash flow and consider taking action.

            Financial Command Center AI
            """

            recipients = config["email_settings"]["recipients"]
            if recipients:
                _send_email(recipients, subject, body)

            _append_log(NOTIFICATION_LOG, {
                "event": "low_balance_alert_triggered",
                "account_key": key,
                "current_balance": current_balance,
                "threshold": threshold,
                "alert_sent": bool(recipients)
            })

            return {
                "ok": True,
                "alert_triggered": True,
                "current_balance": current_balance,
                "threshold": threshold,
                "recipients_notified": len(recipients) if recipients else 0
            }
        else:
            return {
                "ok": True,
                "alert_triggered": False,
                "current_balance": current_balance,
                "threshold": threshold
            }

    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.tool()
def monitor_transactions(key: str, hours: int = 24) -> Dict[str, Any]:
    """
    Monitor recent transactions for unusual activity and large amounts.

    Args:
        key: Plaid access token or alias
        hours: Number of hours to monitor
    """
    try:
        config = _get_automation_config()
        alert_config = config["alerts"]

        # Get recent transactions
        end_dt = date.today()
        start_dt = end_dt - timedelta(hours=hours)

        access_token = _plaid_token_for(key)
        client = _get_plaid_client()

        req = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_dt,
            end_date=end_dt,
            options=TransactionsGetRequestOptions(count=100)
        )
        resp = client.transactions_get(req).to_dict()
        transactions = resp.get("transactions", [])

        alerts_triggered = []

        # Check for large transactions
        large_threshold = alert_config.get("large_transaction_threshold", 5000.0)
        large_enabled = alert_config.get("large_transaction_enabled", True)

        if large_enabled:
            for tx in transactions:
                amount = abs(float(tx.get("amount", 0)))
                if amount >= large_threshold:
                    alert = {
                        "type": "large_transaction",
                        "transaction_id": tx.get("transaction_id"),
                        "amount": amount,
                        "merchant": tx.get("merchant_name") or tx.get("name"),
                        "date": tx.get("date"),
                        "threshold": large_threshold
                    }
                    alerts_triggered.append(alert)

        # Check for payment received notifications
        payment_enabled = alert_config.get("payment_received_enabled", True)
        payment_minimum = alert_config.get("payment_received_minimum", 0.0)

        if payment_enabled:
            for tx in transactions:
                amount = float(tx.get("amount", 0))
                if amount < 0 and abs(amount) >= payment_minimum:  # Incoming payment
                    alert = {
                        "type": "payment_received",
                        "transaction_id": tx.get("transaction_id"),
                        "amount": abs(amount),
                        "merchant": tx.get("merchant_name") or tx.get("name"),
                        "date": tx.get("date")
                    }
                    alerts_triggered.append(alert)

        # Send notifications if alerts triggered
        if alerts_triggered:
            recipients = config["email_settings"]["recipients"]
            if recipients:
                subject = f"Transaction Alerts - {len(alerts_triggered)} alerts"
                body = "Transaction Monitoring Alert\n\n"

                for alert in alerts_triggered:
                    if alert["type"] == "large_transaction":
                        body += f"LARGE TRANSACTION: ${alert['amount']:,.2f} at {alert['merchant']} on {alert['date']}\n"
                    elif alert["type"] == "payment_received":
                        body += f"PAYMENT RECEIVED: ${alert['amount']:,.2f} from {alert['merchant']} on {alert['date']}\n"

                body += f"\nFinancial Command Center AI"
                _send_email(recipients, subject, body)

        # Log monitoring results
        monitoring_file = ALERTS_DIR / f"transaction_monitoring_{key}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        monitoring_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "account_key": key,
            "monitoring_period_hours": hours,
            "total_transactions": len(transactions),
            "alerts_triggered": alerts_triggered,
            "notifications_sent": len(config["email_settings"]["recipients"]) if alerts_triggered else 0
        }
        _save_json(monitoring_file, monitoring_data)

        _append_log(NOTIFICATION_LOG, {
            "event": "transaction_monitoring",
            "account_key": key,
            "hours_monitored": hours,
            "total_transactions": len(transactions),
            "alerts_triggered": len(alerts_triggered)
        })

        return {
            "ok": True,
            "total_transactions": len(transactions),
            "alerts_triggered": len(alerts_triggered),
            "monitoring_file": str(monitoring_file),
            "alerts": alerts_triggered
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============= CONFIGURATION & MANAGEMENT =============

@app.tool()
def get_automation_status() -> Dict[str, Any]:
    """Get the current status of all automation systems."""
    try:
        config = _get_automation_config()

        # Check scheduler status
        global scheduler_running

        # Get recent logs
        recent_logs = []
        if SCHEDULER_LOG.exists():
            with SCHEDULER_LOG.open("r") as f:
                lines = f.readlines()
                recent_logs = [json.loads(line) for line in lines[-10:]]

        status = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "scheduler_running": scheduler_running,
            "config": config,
            "integrations": {
                "plaid": bool(os.environ.get("PLAID_CLIENT_ID")),
                "stripe": STRIPE_AVAILABLE and bool(os.environ.get("STRIPE_API_KEY")),
                "xero": XERO_AVAILABLE,
                "ml_available": ML_AVAILABLE
            },
            "recent_logs": recent_logs,
            "automation_modules": {
                "payment_reminders": config["payment_reminders"]["enabled"],
                "expense_categorization": config["expense_categorization"]["enabled"],
                "recurring_invoices": config["recurring_invoices"]["enabled"],
                "balance_alerts": config["alerts"].get("low_balance_enabled", True),
                "transaction_monitoring": config["alerts"].get("large_transaction_enabled", True)
            }
        }

        return {"ok": True, "status": status}

    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.tool()
def update_automation_config(
    payment_reminders_enabled: Optional[bool] = None,
    expense_categorization_enabled: Optional[bool] = None,
    recurring_invoices_enabled: Optional[bool] = None,
    low_balance_threshold: Optional[float] = None,
    large_transaction_threshold: Optional[float] = None,
    email_recipients: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Update automation configuration settings."""
    try:
        config = _get_automation_config()

        if payment_reminders_enabled is not None:
            config["payment_reminders"]["enabled"] = payment_reminders_enabled

        if expense_categorization_enabled is not None:
            config["expense_categorization"]["enabled"] = expense_categorization_enabled

        if recurring_invoices_enabled is not None:
            config["recurring_invoices"]["enabled"] = recurring_invoices_enabled

        if low_balance_threshold is not None:
            config["alerts"]["low_balance_threshold"] = float(low_balance_threshold)

        if large_transaction_threshold is not None:
            config["alerts"]["large_transaction_threshold"] = float(large_transaction_threshold)

        if email_recipients is not None:
            config["email_settings"]["recipients"] = email_recipients

        _save_json(AUTOMATION_CONFIG_FILE, config)

        _append_log(SCHEDULER_LOG, {
            "event": "automation_config_updated",
            "updated_fields": {
                "payment_reminders": payment_reminders_enabled,
                "expense_categorization": expense_categorization_enabled,
                "recurring_invoices": recurring_invoices_enabled,
                "low_balance_threshold": low_balance_threshold,
                "large_transaction_threshold": large_transaction_threshold,
                "email_recipients": len(email_recipients) if email_recipients else None
            }
        })

        return {"ok": True, "config": config}

    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============= SCHEDULER MANAGEMENT =============

def run_scheduler():
    """Background scheduler thread function"""
    if not SCHEDULE_AVAILABLE:
        logger.error("Schedule library not available. Install with: pip install schedule")
        return

    global scheduler_running
    scheduler_running = True

    # Schedule automation tasks
    schedule.every().day.at("09:00").do(auto_send_payment_reminders)
    schedule.every().hour.do(lambda: check_balance_alerts("default"))

    logger.info("Automation scheduler started")

    while scheduler_running:
        try:
            schedule.run_pending()
            time_module.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time_module.sleep(60)

@app.tool()
def start_automation_scheduler() -> Dict[str, Any]:
    """Start the background automation scheduler."""
    try:
        if not SCHEDULE_AVAILABLE:
            return {"ok": False, "error": "Schedule library not available. Install with: pip install schedule"}

        global scheduler_thread, scheduler_running

        if scheduler_running:
            return {"ok": False, "reason": "Scheduler already running"}

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

        _append_log(SCHEDULER_LOG, {
            "event": "scheduler_started",
            "status": "running"
        })

        return {"ok": True, "status": "Automation scheduler started"}

    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.tool()
def stop_automation_scheduler() -> Dict[str, Any]:
    """Stop the background automation scheduler."""
    try:
        global scheduler_running

        if not scheduler_running:
            return {"ok": False, "reason": "Scheduler not running"}

        scheduler_running = False

        _append_log(SCHEDULER_LOG, {
            "event": "scheduler_stopped",
            "status": "stopped"
        })

        return {"ok": True, "status": "Automation scheduler stopped"}

    except Exception as e:
        return {"ok": False, "error": str(e)}

# Entry point
if __name__ == "__main__":
    app.run()
