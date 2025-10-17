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
import json
import os
import secrets
from json import JSONDecodeError
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from .emailer import EmailConfigError, build_license_email_content, send_license_email

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env", override=False)

app = Flask(__name__)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "FCC-78C6-DB1B-E742-68FD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "sayeem@daywinlabs.com").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "boombitch@69Bitch")
HOST = os.getenv("LICENSE_SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("LICENSE_SERVER_PORT", "8443"))
MAX_ACTIVATIONS = max(1, int(os.getenv("LICENSE_MAX_ACTIVATIONS", "3")))
LICENSE_TERM_DAYS = max(30, int(os.getenv("LICENSE_TERM_DAYS", "365")))
ADMIN_UI_DIST = BASE_DIR / "admin_ui" / "dist"
LICENSE_STORE_PATH = BASE_DIR / "license_store.json"
INSTALLER_DOWNLOAD_URL = os.getenv("INSTALLER_DOWNLOAD_URL")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", ADMIN_EMAIL)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "fcc-installers")
INSTALLER_FILE = os.getenv("INSTALLER_FILE", "FCC.zip")
SIGNED_URL_EXPIRY = int(os.getenv("SIGNED_URL_EXPIRY", "86400"))

# NOTE: Bootstrap phase uses primarily JSON-backed storage.
_licenses: Dict[str, Dict[str, object]] = {}


def _load_store() -> None:
    """Load persisted licenses from the JSON store, if present."""
    if not LICENSE_STORE_PATH.exists():
        return

    try:
        raw = LICENSE_STORE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[license-server] Unable to read store file: {exc}")
        return

    if not raw.strip():
        return

    try:
        payload = json.loads(raw)
    except JSONDecodeError as exc:
        print(f"[license-server] Invalid JSON in store file: {exc}")
        return

    activation_map: Dict[str, List[Dict[str, object]]] = {}
    for entry in payload.get("activations", []):
        key = str(entry.get("license_key") or "")
        fingerprint = str(entry.get("machine_fingerprint") or "")
        if not key or not fingerprint:
            continue
        activation_map.setdefault(key, []).append(
            {
                "machine_fingerprint": fingerprint,
                "first_seen_at": entry.get("first_activated_at")
                or entry.get("first_seen_at")
                or _now_iso(),
                "last_seen_at": entry.get("last_activated_at")
                or entry.get("last_seen_at")
                or _now_iso(),
                "activation_metadata": entry.get("activation_metadata") or {},
            }
        )

    for license_key, record in payload.get("licenses", {}).items():
        created_at = (
            record.get("issued_at")
            or record.get("created_at")
            or _now_iso()
        )
        _licenses[license_key] = {
            "license_key": license_key,
            "email": (record.get("email") or "").strip().lower(),
            "tier": record.get("tier") or "pilot",
            "client_name": record.get("client_name") or "",
            "created_at": created_at,
            "max_activations": int(record.get("max_activations") or MAX_ACTIVATIONS),
            "activations": activation_map.get(license_key, []),
            "is_revoked": bool(record.get("is_revoked", False)),
            "revoked_at": record.get("revoked_at"),
            "last_email_sent_at": record.get("last_email_sent_at"),
            "last_download_url": record.get("last_download_url"),
        }


def _save_store() -> None:
    """Persist the in-memory license store to disk."""
    LICENSE_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    snapshot: Dict[str, object] = {"licenses": {}, "activations": []}

    for license_key, record in _licenses.items():
        created_raw = str(record.get("created_at") or _now_iso())
        try:
            created_at = dt.datetime.fromisoformat(created_raw)
        except ValueError:
            created_at = dt.datetime.now(dt.timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=dt.timezone.utc)

        expires_at = created_at + dt.timedelta(days=LICENSE_TERM_DAYS)
        activations: List[Dict[str, object]] = list(record.get("activations") or [])
        activations.sort(
            key=lambda entry: str(entry.get("last_seen_at") or entry.get("first_seen_at") or ""),
        )
        activation_count = len(activations)
        last_activation = activations[-1] if activations else {}

        snapshot["licenses"][license_key] = {
            "license_key": license_key,
            "email": record.get("email"),
            "client_name": record.get("client_name"),
            "tier": record.get("tier") or "pilot",
            "issued_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "is_revoked": bool(record.get("is_revoked", False)),
            "revoked_at": record.get("revoked_at"),
            "max_activations": int(record.get("max_activations") or MAX_ACTIVATIONS),
            "activation_count": activation_count,
            "last_activation_at": last_activation.get("last_seen_at"),
            "last_activated_machine": last_activation.get("machine_fingerprint"),
            "last_email_sent_at": record.get("last_email_sent_at"),
            "last_download_url": record.get("last_download_url"),
        }

        for activation in activations:
            snapshot["activations"].append(
                {
                    "license_key": license_key,
                    "machine_fingerprint": activation.get("machine_fingerprint"),
                    "first_activated_at": activation.get("first_seen_at"),
                    "last_activated_at": activation.get("last_seen_at"),
                    "activation_metadata": activation.get("activation_metadata"),
                }
            )

    try:
        LICENSE_STORE_PATH.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[license-server] Failed to write store file: {exc}")


_load_store()


def _create_signed_supabase_url(object_name: str) -> Optional[str]:
    """
    Generate a time-limited download URL from Supabase storage.

    Returns None when Supabase credentials are not configured.
    """

    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    endpoint = f"{SUPABASE_URL}/storage/v1/object/sign/{SUPABASE_BUCKET}/{object_name}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    payload = {"expiresIn": SIGNED_URL_EXPIRY}
    response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text.strip()
        raise requests.HTTPError(
            f"Supabase signed URL request failed ({response.status_code}): {detail}",
            response=response,
        )

    data = response.json()
    signed_path = data.get("signedURL")
    if not signed_path:
        raise requests.HTTPError(
            f"Supabase response missing signedURL: {data}", response=response
        )

    if not signed_path.startswith("/"):
        signed_path = f"/{signed_path}"
    return f"{SUPABASE_URL}/storage/v1{signed_path}"


def _generate_download_link() -> Optional[str]:
    """
    Build a signed download URL for the installer when possible.
    Falls back to the default object on failure.
    """

    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        return _create_signed_supabase_url(INSTALLER_FILE)
    except requests.HTTPError as exc:
        print(f"[supabase] Failed to sign {INSTALLER_FILE}: {exc}")
        legacy_object = "installer_package.zip"
        if INSTALLER_FILE != legacy_object:
            try:
                signed = _create_signed_supabase_url(legacy_object)
                print(f"[supabase] Fallback succeeded using {legacy_object}")
                return signed
            except requests.HTTPError as fallback_exc:
                print(f"[supabase] Fallback failed: {fallback_exc}")
    except requests.RequestException as exc:
        print(f"[supabase] Request error while signing installer: {exc}")

    return None


def _compose_email_preview(
    record: Dict[str, object],
    download_url: Optional[str],
    *,
    subject: Optional[str] = None,
    html: Optional[str] = None,
    text: Optional[str] = None,
) -> Dict[str, str]:
    preview = build_license_email_content(
        client_name=record.get("client_name") or record.get("email") or "",
        license_key=str(record.get("license_key") or ""),
        download_url=download_url,
        support_email=SUPPORT_EMAIL,
        recipient_email=record.get("email") or "",
        subject=subject,
    )
    final_subject = subject or preview["subject"]
    final_html = html or preview["html"]
    final_text = text or preview["text"]
    return {"subject": final_subject, "html": final_html, "text": final_text}


def _send_email_for_record(
    record: Dict[str, object],
    download_url: Optional[str],
    email_preview: Dict[str, str],
) -> tuple[bool, Optional[str]]:
    recipient = (record.get("email") or "").strip()
    if not recipient:
        message = "License record missing recipient email."
        print(f"[email] {message}")
        return False, "missing_recipient"
    try:
        sent = send_license_email(
            recipient_email=recipient,
            client_name=record.get("client_name") or recipient,
            license_key=str(record.get("license_key") or ""),
            download_url=download_url,
            support_email=SUPPORT_EMAIL,
            subject=email_preview["subject"],
            html_body=email_preview["html"],
            text_body=email_preview["text"],
        )
    except EmailConfigError as exc:
        print(f"[email] Skipping onboarding email: {exc}")
        return False, str(exc)

    if sent:
        print(f"[email] Sent onboarding email to {recipient}")
        record["last_email_sent_at"] = _now_iso()
        record["last_download_url"] = download_url
        return True, None

    print(f"[email] Failed to send onboarding email to {recipient}. See logs for details.")
    return False, "delivery_failed"


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
    return f"{compact[:6]}.{compact[-4:]}"


def _get_bearer_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", maxsplit=1)[1].strip()
    return ""


def _require_admin_token() -> bool:
    return _get_bearer_token() == ADMIN_TOKEN


def _lookup_license(license_key: str) -> Optional[Dict[str, object]]:
    return _licenses.get(license_key)


def _activation_summary(record: Dict[str, object]) -> Tuple[int, int]:
    activations = record.get("activations") or []
    return len(activations), int(record.get("max_activations", MAX_ACTIVATIONS))


def _license_summary(record: Dict[str, object]) -> Dict[str, object]:
    license_key = str(record.get("license_key") or "")
    created_raw = str(record.get("created_at") or _now_iso())
    try:
        created_at = dt.datetime.fromisoformat(created_raw)
    except ValueError:
        created_at = dt.datetime.now(dt.timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=dt.timezone.utc)
    expires_at = created_at + dt.timedelta(days=LICENSE_TERM_DAYS)
    activations: List[Dict[str, object]] = list(record.get("activations") or [])
    if record.get("is_revoked"):
        status: str = "expired"
    elif expires_at < dt.datetime.now(dt.timezone.utc):
        status = "expired"
    else:
        status = "active" if activations else "pending"
    issued_to = (record.get("client_name") or "").strip() or (record.get("email") or "").strip() or "Unassigned"
    seats = int(record.get("max_activations") or MAX_ACTIVATIONS)
    download_url = record.get("last_download_url") or INSTALLER_DOWNLOAD_URL
    return {
        "id": license_key,
        "issuedTo": issued_to,
        "seats": seats,
        "status": status,
        "issuedAt": created_at.isoformat(),
        "expiresAt": expires_at.isoformat(),
        "tier": record.get("tier") or "pilot",
        "activationCount": len(activations),
        "tokenPreview": _mask_key(license_key),
        "downloadUrl": download_url,
        "isRevoked": bool(record.get("is_revoked", False)),
        "revokedAt": record.get("revoked_at"),
        "lastEmailSentAt": record.get("last_email_sent_at"),
    }


@app.post("/api/login")
def login() -> tuple[Dict[str, object], int]:
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    token_candidate = (data.get("token") or "").strip()

    is_valid = False
    if token_candidate and token_candidate == ADMIN_TOKEN:
        is_valid = True
    elif email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        is_valid = True

    if not is_valid:
        return jsonify({"ok": False, "error": "invalid_credentials"}), 401

    return jsonify({"ok": True, "token": ADMIN_TOKEN, "email": ADMIN_EMAIL}), 200


@app.post("/api/admin/create_license")
def create_license() -> tuple[Dict[str, object], int]:
    if not _require_admin_token():
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    tier = (data.get("tier") or "pilot").strip() or "pilot"
    client_name = (data.get("client_name") or "").strip()
    max_activations = int(data.get("max_activations") or MAX_ACTIVATIONS)
    max_activations = max(1, max_activations)
    send_email_flag = bool(data.get("send_email", True))
    custom_subject = data.get("email_subject") or data.get("subject")
    custom_html = data.get("email_html") or data.get("html")
    custom_text = data.get("email_text") or data.get("text")
    if not email:
        return jsonify({"ok": False, "error": "missing_email"}), 400

    license_key = _normalize_key("FCC-" + "-".join(secrets.token_hex(2).upper() for _ in range(4)))
    record = {
        "license_key": license_key,
        "email": email,
        "tier": tier,
        "client_name": client_name,
        "created_at": _now_iso(),
        "max_activations": max_activations,
        "activations": [],
        "is_revoked": False,
        "revoked_at": None,
        "last_email_sent_at": None,
        "last_download_url": None,
    }
    _licenses[license_key] = record

    signed_download = _generate_download_link()
    download_url = signed_download or INSTALLER_DOWNLOAD_URL or record.get("last_download_url")
    record["last_download_url"] = download_url

    email_preview = _compose_email_preview(
        record,
        download_url,
        subject=custom_subject,
        html=custom_html,
        text=custom_text,
    )
    email_sent = False
    email_error: Optional[str] = None
    if send_email_flag:
        email_sent, email_error = _send_email_for_record(record, download_url, email_preview)

    _save_store()
    summary = _license_summary(record)
    summary["downloadUrl"] = record.get("last_download_url") or download_url
    response_payload: Dict[str, object] = {
        "ok": True,
        "license_key": license_key,
        "license": summary,
        "email_sent": email_sent,
        "email_preview": email_preview,
        "download_url": summary.get("downloadUrl"),
    }
    if email_error:
        response_payload["email_error"] = email_error
    print(f"Issued license for {email}: {license_key}")
    return jsonify(response_payload), 200


@app.post("/api/admin/licenses/<license_key>/send_email")
def send_existing_license_email(license_key: str) -> tuple[Dict[str, object], int]:
    if not _require_admin_token():
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    record = _lookup_license(_normalize_key(license_key))
    if record is None:
        return jsonify({"ok": False, "error": "license_not_found"}), 404
    if record.get("is_revoked"):
        return jsonify({"ok": False, "error": "license_revoked"}), 400

    data = request.get_json(force=True) or {}
    custom_subject = data.get("email_subject") or data.get("subject")
    custom_html = data.get("email_html") or data.get("html")
    custom_text = data.get("email_text") or data.get("text")
    download_override = data.get("download_url")

    download_url = (
        download_override
        or _generate_download_link()
        or record.get("last_download_url")
        or INSTALLER_DOWNLOAD_URL
    )
    email_preview = _compose_email_preview(
        record,
        download_url,
        subject=custom_subject,
        html=custom_html,
        text=custom_text,
    )
    email_sent, email_error = _send_email_for_record(record, download_url, email_preview)
    _save_store()

    summary = _license_summary(record)
    response_payload: Dict[str, object] = {
        "ok": email_sent,
        "license": summary,
        "email_sent": email_sent,
        "email_preview": email_preview,
        "download_url": summary.get("downloadUrl"),
    }
    if email_error:
        response_payload["email_error"] = email_error
    return jsonify(response_payload), 200


@app.post("/api/admin/licenses/<license_key>/resend")
def resend_license_email(license_key: str) -> tuple[Dict[str, object], int]:
    if not _require_admin_token():
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    record = _lookup_license(_normalize_key(license_key))
    if record is None:
        return jsonify({"ok": False, "error": "license_not_found"}), 404
    if record.get("is_revoked"):
        return jsonify({"ok": False, "error": "license_revoked"}), 400

    download_url = _generate_download_link() or record.get("last_download_url") or INSTALLER_DOWNLOAD_URL
    email_preview = _compose_email_preview(record, download_url)
    email_sent, email_error = _send_email_for_record(record, download_url, email_preview)
    _save_store()

    summary = _license_summary(record)
    response_payload: Dict[str, object] = {
        "ok": email_sent,
        "license": summary,
        "email_sent": email_sent,
        "email_preview": email_preview,
        "download_url": summary.get("downloadUrl"),
    }
    if email_error:
        response_payload["email_error"] = email_error
    return jsonify(response_payload), 200


@app.post("/api/admin/licenses/<license_key>/revoke")
def revoke_license(license_key: str) -> tuple[Dict[str, object], int]:
    if not _require_admin_token():
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    record = _lookup_license(_normalize_key(license_key))
    if record is None:
        return jsonify({"ok": False, "error": "license_not_found"}), 404

    if not record.get("is_revoked"):
        record["is_revoked"] = True
        record["revoked_at"] = _now_iso()
        _save_store()

    summary = _license_summary(record)
    return jsonify({"ok": True, "license": summary}), 200


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

    _save_store()
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


@app.get("/api/licenses")
def list_dashboard_licenses() -> tuple[Dict[str, object], int]:
    if not _require_admin_token():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    dashboard_payload = [_license_summary(record) for record in _licenses.values()]
    return jsonify({"ok": True, "licenses": dashboard_payload}), 200


@app.get("/api/admin/licenses")
def list_licenses() -> tuple[Dict[str, object], int]:
    if not _require_admin_token():
        return jsonify({"ok": False, "error": "unauthorized"}), 403
    return jsonify({"ok": True, "licenses": list(_licenses.values())}), 200


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def serve_admin_ui(path: str) -> object:
    """
    Serve the compiled admin UI bundle. Falls back to returning index.html for
    client-side routing when the requested asset is not found.
    """

    if not ADMIN_UI_DIST.exists():
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "admin_ui_not_built",
                    "message": "Build the admin UI with `npm run build` in fcc_bootstrap/admin_ui`.",
                }
            ),
            503,
        )

    dist_root = ADMIN_UI_DIST.resolve()
    if path in ("", ".", "/"):
        return send_from_directory(dist_root, "index.html", max_age=0)

    try:
        asset_path = (dist_root / path).resolve()
        if asset_path.is_file() and dist_root in asset_path.parents:
            relative_path = asset_path.relative_to(dist_root).as_posix()
            return send_from_directory(dist_root, relative_path, max_age=0)
    except (OSError, ValueError):
        # Fall through to SPA response on path traversal attempts.
        pass

    return send_from_directory(dist_root, "index.html", max_age=0)


def main() -> None:
    print(f"FCC License Server running on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT)


if __name__ == "__main__":
    main()
