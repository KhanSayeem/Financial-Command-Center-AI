#!/usr/bin/env python3
"""
create_license.py - FCC Pilot License + Installer Delivery CLI

This streamlined version defaults to the local HTTP license server and adds
options to skip signed download generation for offline testing.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse

import requests
from dotenv import load_dotenv

from emailer import EmailConfigError, send_license_email

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env", override=False)

DEFAULT_LICENSE_SERVER = "https://license.daywinlabs.com"
LICENSE_SERVER = os.getenv("LICENSE_SERVER", DEFAULT_LICENSE_SERVER).rstrip("/")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET = os.getenv("SUPABASE_BUCKET", "fcc-installers")
DEFAULT_INSTALLER_FILE = "FCC.zip"
INSTALLER_FILE = os.getenv("INSTALLER_FILE", DEFAULT_INSTALLER_FILE)
SIGNED_URL_EXPIRY = int(os.getenv("SIGNED_URL_EXPIRY", "86400"))
VERIFY_LICENSE_SSL = os.getenv("LICENSE_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}
STATIC_INSTALLER_URL = os.getenv("INSTALLER_DOWNLOAD_URL")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", os.getenv("ADMIN_EMAIL", "sayeem@daywinlabs.com"))

parsed_license_server = urlparse(LICENSE_SERVER or DEFAULT_LICENSE_SERVER)
if parsed_license_server.scheme == "http":
    VERIFY_LICENSE_SSL = False
elif (
    parsed_license_server.scheme == "https"
    and parsed_license_server.hostname in {"localhost", "127.0.0.1"}
    and not VERIFY_LICENSE_SSL
):
    LICENSE_SERVER = urlunparse(
        ("http", parsed_license_server.netloc, parsed_license_server.path, parsed_license_server.params,
         parsed_license_server.query, parsed_license_server.fragment)
    ).rstrip("/")

LOG_FILE = BASE_DIR / "issued_pilot_licenses.csv"
PILOT_TIER = "pilot"


def ensure_env(require_supabase: bool = True) -> None:
    requirements = {"ADMIN_TOKEN": ADMIN_TOKEN}
    if require_supabase:
        requirements.update(
            {
                "SUPABASE_URL": SUPABASE_URL,
                "SUPABASE_SERVICE_KEY": SUPABASE_KEY,
            }
        )
    missing = [key for key, value in requirements.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def create_license(email: str, client_name: str = "") -> str:
    url = f"{LICENSE_SERVER}/api/admin/create_license"
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    data = {"email": email, "tier": PILOT_TIER, "client_name": client_name}
    response = requests.post(url, headers=headers, json=data, timeout=10, verify=VERIFY_LICENSE_SSL)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"License creation failed: {payload}")
    return payload["license_key"]


def create_signed_supabase_url(file_path: str) -> str:
    url = f"{SUPABASE_URL}/storage/v1/object/sign/{BUCKET}/{file_path}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    data = {"expiresIn": SIGNED_URL_EXPIRY}
    response = requests.post(url, headers=headers, json=data, timeout=10)
    if response.status_code >= 400:
        detail = ""
        try:
            detail_json = response.json()
            detail = f" Details: {detail_json}"
        except Exception:
            if response.text:
                detail = f" Details: {response.text.strip()}"
        raise requests.HTTPError(
            f"Failed to generate signed URL for '{file_path}' "
            f"(HTTP {response.status_code}).{detail or ''}",
            response=response,
        )
    payload = response.json()
    if "signedURL" not in payload:
        raise RuntimeError(f"Signed URL generation failed: {payload}")
    signed_path = payload["signedURL"]
    if not signed_path.startswith("/"):
        signed_path = f"/{signed_path}"
    return f"{SUPABASE_URL}/storage/v1{signed_path}"


def log_delivery(email: str, client_name: str, license_key: str, signed_url: Optional[str]) -> None:
    new_file = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as fh:
        writer = csv.writer(fh)
        if new_file:
            writer.writerow(["timestamp", "email", "client_name", "license_key", "download_link"])
        writer.writerow(
            [
                dt.datetime.now(dt.timezone.utc).isoformat(),
                email,
                client_name,
                license_key,
                signed_url or "",
            ]
        )


def run_flow(skip_download: bool = False) -> Tuple[str, Optional[str]]:
    print("FCC Pilot License Delivery\n")
    client_name = input("Client name: ").strip()
    client_email = input("Client email: ").strip()
    if not client_email:
        raise ValueError("Email is required.")
    if not client_name:
        client_name = client_email

    print("\nCreating license key...")
    license_key = create_license(client_email, client_name=client_name)
    print("License key created:", license_key)

    signed_url: Optional[str] = None
    installer_file = INSTALLER_FILE
    if skip_download:
        print("\nSkipping signed download generation (requested).")
    else:
        print("\nGenerating 24-hour signed download link...")
        print(f" - Using installer object: {installer_file}")
        try:
            signed_url = create_signed_supabase_url(installer_file)
        except requests.HTTPError:
            legacy_name = "installer_package.zip"
            if installer_file == legacy_name:
                print(f" - Could not find '{legacy_name}', retrying with '{DEFAULT_INSTALLER_FILE}'...")
                installer_file = DEFAULT_INSTALLER_FILE
                signed_url = create_signed_supabase_url(installer_file)
            else:
                raise
        print("Signed Supabase URL generated.\n")

    print("----------------------------------------------")
    print(f"Message to send to {client_email}:\n")
    download_line = signed_url or STATIC_INSTALLER_URL or "<download link not generated>"
    print(
        f"""
Hi {client_name},

Thank you for joining the FCC AI CFO Pilot Program ($999/month).

Your license key: {license_key}

Download (valid for 24 hours):
{download_line}

Setup Instructions:
1. Unzip {installer_file}
2. Double-click ultimate_cert_fix.cmd
3. Enter your license key when prompted.
4. Complete setup wizard to link your Plaid/Stripe/Xero accounts.

Support: sayeem@daywinlabs.com
- Daywin Labs | FCC AI CFO
"""
    )
    print("----------------------------------------------")

    log_delivery(client_email, client_name, license_key, signed_url)

    try:
        if send_license_email(
            recipient_email=client_email,
            client_name=client_name,
            license_key=license_key,
            download_url=signed_url or STATIC_INSTALLER_URL,
            support_email=SUPPORT_EMAIL,
        ):
            print(f"[email] Sent onboarding email to {client_email}.")
        else:
            print(f"[email] Brevo rejected the onboarding email for {client_email}.")
    except EmailConfigError as exc:
        print(f"[email] Skipping onboarding email: {exc}")

    print(f"Logged in {LOG_FILE}\nDone.")
    return license_key, signed_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FCC Pilot License creation helper")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip creating the signed download link (useful for local testing).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_env(require_supabase=not args.skip_download)
    run_flow(skip_download=args.skip_download)


if __name__ == "__main__":
    main()
