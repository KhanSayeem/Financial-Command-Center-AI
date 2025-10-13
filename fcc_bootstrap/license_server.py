#!/usr/bin/env python3
"""
FCC License Server - Bootstrap Edition
Provides minimal REST endpoints for local or production use.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from flask import Flask, jsonify, request

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

app = Flask(__name__)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "mydevsecret123")

# NOTE: Bootstrap phase uses in-memory storage; replace with persistent store later.
licenses: List[Dict[str, str]] = []


@app.post("/api/admin/create_license")
def create_license():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or auth_header.split(" ", maxsplit=1)[1] != ADMIN_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    data = request.get_json(force=True)
    email = (data or {}).get("email")
    tier = (data or {}).get("tier", "pilot")
    if not email:
        return jsonify({"ok": False, "error": "missing email"}), 400

    # Generate a secure license key with FCC prefix to simplify support lookups.
    license_key = "FCC-" + "-".join(secrets.token_hex(2).upper() for _ in range(4))
    licenses.append({"email": email, "license_key": license_key, "tier": tier})
    print(f"Issued license for {email}: {license_key}")
    return jsonify({"ok": True, "license_key": license_key})


@app.get("/api/admin/licenses")
def list_licenses():
    return jsonify({"ok": True, "licenses": licenses})


if __name__ == "__main__":
    print("FCC License Server running on http://localhost:8443")
    app.run(host="0.0.0.0", port=8443)
