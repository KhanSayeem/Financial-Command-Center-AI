#!/usr/bin/env python3
"""
Email delivery helpers for the FCC license server.

Currently supports Brevo transactional emails using the v3 API.
"""

from __future__ import annotations

import os
import re
from textwrap import dedent
from typing import Dict, Optional

import requests

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
DEFAULT_EMAIL_SUBJECT = "Your Financial Command Center License"
_INLINE_COMMENT_REGEX = re.compile(r"\s+#")


class EmailConfigError(RuntimeError):
    """Raised when the email configuration is missing required values."""


def _clean_env_value(raw: Optional[str]) -> Optional[str]:
    """Return env values without trailing inline comments or extra whitespace."""
    if raw is None:
        return None
    candidate = raw.strip()
    if not candidate:
        return ""
    parts = _INLINE_COMMENT_REGEX.split(candidate, 1)
    return parts[0].strip()


def _load_config() -> Dict[str, str]:
    api_key = _clean_env_value(os.getenv("BREVO_API_KEY"))
    sender_email = _clean_env_value(os.getenv("BREVO_SENDER_EMAIL"))
    sender_name = _clean_env_value(os.getenv("BREVO_SENDER_NAME")) or "Financial Command Center"

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
    recipient_email: Optional[str] = None,
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
        <!DOCTYPE html>
        <html>
        <head>
            <title>Your {product_name} License</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body style="margin:0; padding:20px; font-family:Arial, sans-serif; background-color:#f5f5f5;">
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color:#f5f5f5;">
                <tr>
                    <td style="padding:20px 0;">
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" align="center" style="background-color:#ffffff; border-radius:8px; overflow:hidden;">
                            <tr>
                                <td style="padding:30px 30px 20px 30px; text-align:center; border-bottom:1px solid #eaeaea;">
                                    <h1 style="margin:0; font-size:24px; color:#333333;">{product_name}</h1>
                                    <p style="margin:10px 0 0 0; font-size:16px; color:#666666;">{plan_label}</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding:30px 30px 20px 30px;">
                                    <p style="margin:0 0 15px 0; font-size:16px; color:#333333;">Hi {client_name or 'there'},</p>
                                    <p style="margin:0 0 15px 0; font-size:16px; color:#333333;">Welcome to the <strong>{product_name}</strong> ({plan_label})!</p>
                                    <p style="margin:0 0 15px 0; font-size:16px; color:#333333;"><strong>Your license key</strong><br/>
                                    <code style="font-size:1.1rem; background-color:#f9f9f9; padding:5px 8px; border-radius:4px; border:1px solid #ddd;">{license_key}</code></p>
                                    <p style="margin:0 0 15px 0; font-size:16px; color:#333333;"><strong>Download the installer</strong><br/>
                                    <a href="{fallback_download}" style="color:#007bff; text-decoration:underline;">Download Now</a></p>
                                    <p style="margin:0 0 15px 0; font-size:16px; color:#333333;"><strong>Setup checklist</strong></p>
                                    <ol style="padding-left:20px; margin:0 0 15px 0;">
                                      <li style="margin:0 0 8px 0; font-size:16px; color:#333333;">Unzip the archive on your admin machine.</li>
                                      <li style="margin:0 0 8px 0; font-size:16px; color:#333333;">Run <code style="background-color:#f9f9f9; padding:2px 4px; border-radius:3px; border:1px solid #ddd;">ultimate_cert_fix.cmd</code> to install the local certificates.</li>
                                      <li style="margin:0 0 8px 0; font-size:16px; color:#333333;">Launch the installer and enter the license key above.</li>
                                      <li style="margin:0 0 8px 0; font-size:16px; color:#333333;">Complete the setup wizard to connect Plaid, Stripe, and Xero.</li>
                                    </ol>
                                    <p style="margin:0 0 15px 0; font-size:16px; color:#333333;">{support_line}</p>
                                    <p style="margin:0 0 0 0; font-size:16px; color:#333333;">Thank you for choosing Daywin Labs.</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding:20px 30px; text-align:center; background-color:#f8f9fa; border-top:1px solid #eaeaea; color:#666666; font-size:14px;">
                                    <p style="margin:0 0 10px 0;">Daywin Labs</p>
                                    <p style="margin:0;">This email was sent to {client_name or ''} - {recipient_email or ''}</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
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
            recipient_email=recipient_email,
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
