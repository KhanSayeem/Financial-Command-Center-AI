#!/usr/bin/env python3
"""
Email delivery helpers for the FCC license server.

Currently supports Brevo transactional emails using the v3 API.
"""

from __future__ import annotations

import os
from textwrap import dedent
from typing import Dict, Optional

import requests

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
DEFAULT_EMAIL_SUBJECT = "Your Financial Command Center License"


class EmailConfigError(RuntimeError):
    """Raised when the email configuration is missing required values."""


def _load_config() -> Dict[str, str]:
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL")
    sender_name = os.getenv("BREVO_SENDER_NAME", "Financial Command Center")

    if not api_key or not sender_email:
        raise EmailConfigError(
            "Missing Brevo configuration. Ensure BREVO_API_KEY and "
            "BREVO_SENDER_EMAIL are set in your environment."
        )

    return {
        "api_key": api_key,
        "sender_email": sender_email,
        "sender_name": sender_name,
    }


def build_license_email_content(
    *,
    client_name: str,
    license_key: str,
    download_url: Optional[str],
    support_email: Optional[str],
    subject: Optional[str] = None,
    product_name: str = "Financial Command Center AI",
    plan_label: str = "Pilot Program",
) -> Dict[str, str]:
    """Return subject, text, and HTML bodies for the onboarding email."""

    fallback_download = download_url or "Download link will be shared separately."
    support_line = (
        f"For assistance reply to {support_email}."
        if support_email
        else "For assistance just reply to this email."
    )

    text_body = dedent(
        f"""
        Hi {client_name or 'there'},

        Welcome to the {product_name} ({plan_label})!

        Your license key:
        {license_key}

        Download the installer:
        {fallback_download}

        Setup checklist:
        1. Unzip the archive on your admin machine.
        2. Run `ultimate_cert_fix.cmd` to install the local certificates.
        3. Launch the installer and enter the license key above.
        4. Complete the setup wizard to connect Plaid/Stripe/Xero.

        {support_line}

        Thank you for choosing Daywin Labs.
        """
    ).strip()

    html_body = dedent(
        f"""
        <p>Hi {client_name or 'there'},</p>
        <p>Welcome to the <strong>{product_name}</strong> ({plan_label})!</p>
        <p><strong>Your license key</strong><br/>
        <code style="font-size:1.1rem;">{license_key}</code></p>
        <p><strong>Download the installer</strong><br/>
        <a href="{fallback_download}">{fallback_download}</a></p>
        <p><strong>Setup checklist</strong></p>
        <ol>
          <li>Unzip the archive on your admin machine.</li>
          <li>Run <code>ultimate_cert_fix.cmd</code> to install the local certificates.</li>
          <li>Launch the installer and enter the license key above.</li>
          <li>Complete the setup wizard to connect Plaid, Stripe, and Xero.</li>
        </ol>
        <p>{support_line}</p>
        <p>Thank you for choosing Daywin Labs.</p>
        """
    ).strip()

    email_subject = subject or f"Your {product_name} License"

    return {"subject": email_subject, "text": text_body, "html": html_body}


def send_license_email(
    *,
    recipient_email: str,
    client_name: str,
    license_key: str,
    download_url: Optional[str] = None,
    support_email: Optional[str] = None,
    subject: Optional[str] = None,
    html_body: Optional[str] = None,
    text_body: Optional[str] = None,
) -> bool:
    """
    Send a license onboarding email via Brevo.

    Returns True when Brevo accepts the message. Raises EmailConfigError when
    the configuration is missing. Returns False on request errors.
    """

    config = _load_config()
    if subject is None or html_body is None or text_body is None:
        preview = build_license_email_content(
            client_name=client_name,
            license_key=license_key,
            download_url=download_url,
            support_email=support_email,
            subject=subject or DEFAULT_EMAIL_SUBJECT,
        )
        subject = preview["subject"]
        html_body = html_body or preview["html"]
        text_body = text_body or preview["text"]

    payload = {
        "sender": {
            "email": config["sender_email"],
            "name": config["sender_name"],
        },
        "to": [{"email": recipient_email, "name": client_name or recipient_email}],
        "subject": subject or DEFAULT_EMAIL_SUBJECT,
        "htmlContent": html_body,
        "textContent": text_body,
    }

    headers = {
        "api-key": config["api_key"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[email] Failed to send onboarding email: {exc}")
        return False

    return True
