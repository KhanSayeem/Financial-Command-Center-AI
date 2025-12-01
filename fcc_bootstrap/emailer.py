#!/usr/bin/env python3
"""
Email delivery helpers for the FCC license server.

Currently supports Brevo transactional emails using the v3 API.
"""

from __future__ import annotations

import base64
import os
import re
from pathlib import Path
from textwrap import dedent
from typing import Dict, Optional

import requests

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
DEFAULT_EMAIL_SUBJECT = "Your Financial Command Center License"
DEFAULT_EMAIL_LOGO_URL = (
    "https://jqfoqqnefabtqcjmceyu.supabase.co/storage/v1/object/sign/Branding/"
    "logo-no-background.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9iYzQ0MzBkOC05MTAyLTQ5ZjUtYmQwOS04Zjk0ZmFkNmY3MjMiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJCcmFuZGluZy9sb2dvLW5vLWJhY2tncm91bmQucG5nIiwiaWF0IjoxNzYwODI5MzI1LCJleHAiOjI0NTQ2MjEzMjV9.u-JO5pK3EgGpn8hGTl90ZKr2EGg0_TWeAqKVHtiw8u8"
)
_INLINE_COMMENT_REGEX = re.compile(r"\s+#")


def _get_logo_src() -> str:
    """
    Return a logo source URL or data URI suitable for HTML email.

    Many email clients (including Gmail) block inline data URIs, so allowing an
    externally hosted HTTPS image via the EMAIL_LOGO_URL environment variable
    keeps the logo visible while still supporting local fallbacks for testing.
    """
    remote_override = _clean_env_value(os.getenv("EMAIL_LOGO_URL"))
    if remote_override and remote_override.lower().startswith(("http://", "https://")):
        return remote_override
    if DEFAULT_EMAIL_LOGO_URL:
        return DEFAULT_EMAIL_LOGO_URL

    project_root = Path(__file__).parent.parent
    candidate_paths = [
        project_root / "logo-no-background.png",
        project_root / "assets" / "logo-no-background.png",
        project_root
        / "fcc_bootstrap"
        / "admin_ui"
        / "public"
        / "logo-no-background.png",
        project_root / "fcc_bootstrap" / "admin_ui" / "dist" / "logo-no-background.png",
    ]

    logo_path = next((path for path in candidate_paths if path.exists()), None)
    if logo_path is None:
        # No logo available; let the email fall back to text-only branding.
        return ""

    with logo_path.open("rb") as img_file:
        img_data = img_file.read()
    img_base64 = base64.b64encode(img_data).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"


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
    default_support = "support@daywinlabs.com"
    support_line = f"For assistance please reach out to {support_email or default_support}."

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
        2. Windows: run `ultimate_cert_fix.cmd` (creates the desktop shortcut, installs certs, and launches the app).
        3. macOS/Linux: run `bootstrap/bootstrap-install.sh` (approve sudo when asked) to install certificates, dependencies, and launch.

        {support_line}

        Thank you for choosing Daywin Labs.
        """
    ).strip()

    # Prepare branding blocks for the HTML email
    logo_src = _get_logo_src()
    logo_img_html = (
        f'<img src="{logo_src}" alt="Daywin Labs" '
        'style="display:block; height:30px; width:auto;">'
    ) if logo_src else ""

    if logo_img_html:
        thank_you_line = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
            'style="margin:0 0 15px 0; padding:0;">'
            '<tr>'
            f'<td style="padding:0 10px 0 0; vertical-align:middle;">{logo_img_html}</td>'
            '<td style="vertical-align:middle; font-size:16px; color:#333333;">'
            'Thank you for choosing Daywin Labs.</td>'
            '</tr>'
            '</table>'
        )
        footer_brand_html = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
            'align="center" style="margin:0 auto 10px auto; padding:0;">'
            '<tr>'
            f'<td style="padding:0 8px 0 0; vertical-align:middle;">{logo_img_html}</td>'
            '<td style="vertical-align:middle; font-size:14px; color:#666666;">Daywin Labs</td>'
            '</tr>'
            '</table>'
        )
    else:
        thank_you_line = (
            '<p style="margin:0 0 15px 0; font-size:16px; color:#333333;">'
            'Thank you for choosing Daywin Labs.'
            '</p>'
        )
        footer_brand_html = '<p style="margin:0 0 10px 0;">Daywin Labs</p>'

    if download_url:
        download_html = (
            f'<a href="{fallback_download}" style="color:#007bff; text-decoration:underline;">Download Now</a>'
        )
    else:
        download_html = fallback_download

    greeting_name = client_name or recipient_email or "there"

    html_body = f"""<!DOCTYPE html>
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
                            <p style="margin:0 0 15px 0; font-size:16px; color:#333333;">Hi {greeting_name},</p>
                            <p style="margin:0 0 15px 0; font-size:16px; color:#333333;">Welcome to the <strong>{product_name}</strong> ({plan_label})!</p>
                            <p style="margin:0 0 15px 0; font-size:16px; color:#333333;"><strong>Your license key</strong><br/>
                            <code style="font-size:1.1rem; background-color:#f9f9f9; padding:5px 8px; border-radius:4px; border:1px solid #ddd;">{license_key}</code></p>
                            <p style="margin:0 0 15px 0; font-size:16px; color:#333333;"><strong>Download the installer</strong><br/>
                            {download_html}</p>
                            <p style="margin:0 0 15px 0; font-size:16px; color:#333333;"><strong>Setup checklist</strong></p>
                            <ol style="padding-left:20px; margin:0 0 15px 0;">
                              <li style="margin:0 0 8px 0; font-size:16px; color:#333333;">Unzip the archive on your admin machine.</li>
                              <li style="margin:0 0 8px 0; font-size:16px; color:#333333;"><strong>Windows:</strong> run <code style="background-color:#f9f9f9; padding:2px 4px; border-radius:3px; border:1px solid #ddd;">ultimate_cert_fix.cmd</code> (creates the desktop shortcut, installs certificates, and launches the app).</li>
                              <li style="margin:0 0 8px 0; font-size:16px; color:#333333;"><strong>macOS/Linux:</strong> run <code style="background-color:#f9f9f9; padding:2px 4px; border-radius:3px; border:1px solid #ddd;">bootstrap/bootstrap-install.sh</code> (approve sudo when prompted) to install certificates, dependencies, and launch.</li>
                            </ol>
                            <p style="margin:0 0 15px 0; font-size:16px; color:#333333;">{support_line}</p>
                            {thank_you_line}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:20px 30px; text-align:center; background-color:#f8f9fa; border-top:1px solid #eaeaea; color:#666666; font-size:14px;">
                            {footer_brand_html}
                            <p style="margin:0;">This email was sent to {client_name or ''} - {recipient_email or ''}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

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
