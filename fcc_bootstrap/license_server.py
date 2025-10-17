#!/usr/bin/env python3
"""
FCC License Server - Bootstrap Edition (HTTP)

Provides minimal REST endpoints backed by in-memory storage. Designed for
single-user pilot programs where the admin issues a key and delivers a signed
installer link. TLS support from earlier versions has been removed to simplify
local development. If HTTPS is required, place this service behind a reverse
proxy that terminates TLS.
"""

from __future__ import annotations

import datetime as dt
import os
import secrets
from pathlib import Path
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv
from flask import Flask, jsonify, request

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env", override=False)

app = Flask(__name__)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "mydevsecret123")
HOST = os.getenv("LICENSE_SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("LICENSE_SERVER_PORT", "8443"))
MAX_ACTIVATIONS = max(1, int(os.getenv("LICENSE_MAX_ACTIVATIONS", "3")))

# NOTE: Bootstrap phase uses in-memory storage; replace with persistent store later.
_licenses: Dict[str, Dict[str, object]] = {}


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _normalize_key(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.strip().upper()


def _mask_key(value: str) -> str:
    compact = value.replace("-", "")
    if len(compact) <= 8:
        return compact
    return f"{compact[:6]}…{compact[-4:]}"


def _lookup_license(license_key: str) -> Optional[Dict[str, object]]:
    return _licenses.get(license_key)


def _activation_summary(record: Dict[str, object]) -> Tuple[int, int]:
    activations = record.get("activations") or []
    return len(activations), int(record.get("max_activations", MAX_ACTIVATIONS))


@app.post("/api/admin/create_license")
def create_license() -> tuple[Dict[str, object], int]:
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.split(" ", maxsplit=1)[1] if auth_header.startswith("Bearer ") else ""
    if token != ADMIN_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    tier = (data.get("tier") or "pilot").strip() or "pilot"
    client_name = (data.get("client_name") or "").strip()
    if not email:
        return jsonify({"ok": False, "error": "missing_email"}), 400

    license_key = _normalize_key("FCC-" + "-".join(secrets.token_hex(2).upper() for _ in range(4)))
    record = {
        "license_key": license_key,
        "email": email,
        "tier": tier,
        "client_name": client_name,
        "created_at": _now_iso(),
        "max_activations": MAX_ACTIVATIONS,
        "activations": [],
    }
    _licenses[license_key] = record
    print(f"Issued license for {email}: {license_key}")
    return jsonify({"ok": True, "license_key": license_key}), 200


@app.post("/api/license/verify")
def verify_license() -> tuple[Dict[str, object], int]:
    data = request.get_json(force=True) or {}
    license_key = _normalize_key(data.get("license_key"))
    fingerprint = (data.get("machine_fingerprint") or "").strip()
    email = (data.get("email") or "").strip().lower()

    if not license_key:
        return jsonify({"ok": False, "error": "missing_license_key"}), 400
    if not fingerprint:
        return jsonify({"ok": False, "error": "missing_machine_fingerprint"}), 400

    record = _lookup_license(license_key)
    if record is None:
        return jsonify({"ok": False, "error": "invalid_license"}), 400

    record_email = (record.get("email") or "").strip().lower()
    if record_email and email and email != record_email:
        return jsonify({"ok": False, "error": "email_mismatch"}), 400

    activations = record.setdefault("activations", [])
    assert isinstance(activations, list)
    now = _now_iso()
    existing = next((entry for entry in activations if entry.get("machine_fingerprint") == fingerprint), None)
    if existing:
        existing["last_seen_at"] = now
    else:
        max_allowed = int(record.get("max_activations") or MAX_ACTIVATIONS)
        if len(activations) >= max_allowed:
            masked = _mask_key(license_key)
            print(f"Activation limit reached for {masked}")
            return jsonify({"ok": False, "error": "activation_limit_reached"}), 400
        activations.append(
            {
                "machine_fingerprint": fingerprint,
                "first_seen_at": now,
                "last_seen_at": now,
            }
        )

    activation_count, max_activations = _activation_summary(record)
    payload = {
        "license_key": license_key,
        "email": record.get("email"),
        "tier": record.get("tier"),
        "client_name": record.get("client_name"),
        "activation_count": activation_count,
        "max_activations": max_activations,
        "activations": activations,
        "created_at": record.get("created_at"),
    }
    return jsonify({"ok": True, "license": payload}), 200


@app.get("/api/admin/licenses")
def list_licenses() -> tuple[Dict[str, object], int]:
    return jsonify({"ok": True, "licenses": list(_licenses.values())}), 200


def main() -> None:
    print(f"FCC License Server running on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT)


if __name__ == "__main__":
    main()