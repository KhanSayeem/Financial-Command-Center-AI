#!/usr/bin/env python3
"""
create_license.py - FCC Pilot License + Installer Delivery CLI
Bootstrap version: single $999 'pilot' tier.
"""

from __future__ import annotations

import csv
import datetime as dt
import os
from pathlib import Path
from typing import Tuple

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

LICENSE_SERVER = os.getenv("LICENSE_SERVER", "http://localhost:8443")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET = os.getenv("SUPABASE_BUCKET", "fcc-installers")
INSTALLER_FILE = os.getenv("INSTALLER_FILE", "installer_package.zip")
SIGNED_URL_EXPIRY = int(os.getenv("SIGNED_URL_EXPIRY", "86400"))
LOG_FILE = BASE_DIR / "issued_pilot_licenses.csv"
PILOT_TIER = "pilot"


def ensure_env() -> None:
    missing = [k for k, v in {
        "ADMIN_TOKEN": ADMIN_TOKEN,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_SERVICE_KEY": SUPABASE_KEY,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def create_license(email: str) -> str:
    url = f"{LICENSE_SERVER}/api/admin/create_license"
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    data = {"email": email, "tier": PILOT_TIER}
    response = requests.post(url, headers=headers, json=data, timeout=10)
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
    response.raise_for_status()
    payload = response.json()
    if "signedURL" not in payload:
        raise RuntimeError(f"Signed URL generation failed: {payload}")
    signed_path = payload["signedURL"]
    if not signed_path.startswith("/"):
        signed_path = f"/{signed_path}"
    return f"{SUPABASE_URL}/storage/v1{signed_path}"


def log_delivery(email: str, license_key: str, signed_url: str) -> None:
    new_file = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as fh:
        writer = csv.writer(fh)
        if new_file:
            writer.writerow(["timestamp", "email", "license_key", "download_link"])
        writer.writerow([dt.datetime.now(dt.timezone.utc).isoformat(), email, license_key, signed_url])


def run_flow() -> Tuple[str, str]:
    print("FCC Pilot License Delivery\n")
    client_email = input("Client email: ").strip()
    if not client_email:
        raise ValueError("Email is required.")

    print("\nCreating license key...")
    license_key = create_license(client_email)
    print("License key created:", license_key)

    print("\nGenerating 24-hour signed download link...")
    signed_url = create_signed_supabase_url(INSTALLER_FILE)
    print("Signed Supabase URL generated.\n")

    print("----------------------------------------------")
    print(f"Message to send to {client_email}:\n")
    print(
        f"""
Hi {client_email},

Thank you for joining the FCC AI CFO Pilot Program ($999/month).

Your license key: {license_key}

Download (valid for 24 hours):
{signed_url}

Setup Instructions:
1. Unzip installer_package.zip
2. Run financial_launcher.py (or FCCLauncher.exe)
3. Enter your license key when prompted.
4. Complete setup wizard to link your Plaid/Stripe/Xero accounts.

Support: sayeem@daywinlabs.com
- Daywin Labs | FCC AI CFO
"""
    )
    print("----------------------------------------------")

    log_delivery(client_email, license_key, signed_url)
    print(f"Logged in {LOG_FILE}\nDone.")
    return license_key, signed_url


if __name__ == "__main__":
    ensure_env()
    run_flow()
