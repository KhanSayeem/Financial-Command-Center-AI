#!/usr/bin/env python3
"""
FCC License Server - Bootstrap Edition
Provides minimal REST endpoints for local or production use.
"""
from __future__ import annotations

import datetime as dt
import os
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from dotenv import load_dotenv
from flask import Flask, jsonify, request

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

app = Flask(__name__)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "mydevsecret123")
DATABASE_URL = os.getenv("LICENSE_DATABASE_URL")
DEFAULT_MAX_ACTIVATIONS = int(os.getenv("LICENSE_DEFAULT_MAX_ACTIVATIONS", "2"))
LICENSE_DURATION_DAYS = os.getenv("LICENSE_DURATION_DAYS")

if not DATABASE_URL:
    raise RuntimeError("LICENSE_DATABASE_URL environment variable is required for the license server.")


@dataclass
class LicenseRecord:
    license_key: str
    email: str
    client_name: str
    tier: str
    issued_at: dt.datetime
    expires_at: Optional[dt.datetime]
    is_revoked: bool
    max_activations: int
    activation_count: int
    last_activation_at: Optional[dt.datetime]
    last_activated_machine: Optional[str]

    def to_json(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.issued_at:
            payload["issued_at"] = self.issued_at.isoformat()
        if self.expires_at:
            payload["expires_at"] = self.expires_at.isoformat()
        if self.last_activation_at:
            payload["last_activation_at"] = self.last_activation_at.isoformat()
        return payload


def get_connection() -> psycopg.Connection[Any]:
    return psycopg.connect(DATABASE_URL)


def init_db() -> None:
    default_max = int(DEFAULT_MAX_ACTIVATIONS)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS licenses (
                id SERIAL PRIMARY KEY,
                license_key TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                client_name TEXT NOT NULL,
                tier TEXT NOT NULL,
                issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NULL,
                is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
                max_activations INTEGER NOT NULL DEFAULT {default_max},
                activation_count INTEGER NOT NULL DEFAULT 0,
                last_activation_at TIMESTAMPTZ NULL,
                last_activated_machine TEXT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS license_activations (
                id BIGSERIAL PRIMARY KEY,
                license_key TEXT NOT NULL REFERENCES licenses(license_key) ON DELETE CASCADE,
                machine_fingerprint TEXT NOT NULL,
                first_activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                activation_metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
                UNIQUE (license_key, machine_fingerprint)
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_license_activations_license_key
            ON license_activations(license_key);
            """
        )
        conn.commit()


def _generate_license_key() -> str:
    return "FCC-" + "-".join(secrets.token_hex(2).upper() for _ in range(4))


def _issue_license(email: str, client_name: str, tier: str, max_activations: int) -> str:
    expires_at: Optional[dt.datetime] = None
    if LICENSE_DURATION_DAYS:
        try:
            duration_days = int(LICENSE_DURATION_DAYS)
            expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=duration_days)
        except ValueError:
            pass

    attempt = 0
    while True:
        attempt += 1
        license_key = _generate_license_key()
        try:
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO licenses (
                        license_key, email, client_name, tier, expires_at, max_activations
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING license_key;
                    """,
                    (license_key, email, client_name, tier, expires_at, max_activations),
                )
                conn.commit()
                return cur.fetchone()[0]
        except psycopg.errors.UniqueViolation:
            if attempt > 5:
                raise


def _fetch_license(license_key: str, for_update: bool = False) -> Optional[LicenseRecord]:
    sql = """
        SELECT license_key,
               email,
               client_name,
               tier,
               issued_at,
               expires_at,
               is_revoked,
               max_activations,
               activation_count,
               last_activation_at,
               last_activated_machine
        FROM licenses
        WHERE license_key = %s
    """
    if for_update:
        sql += " FOR UPDATE"

    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (license_key,))
        row = cur.fetchone()
        if not row:
            return None
        return LicenseRecord(**row)


def _update_license_activation_metrics(
    conn: psycopg.Connection[Any],
    license_key: str,
    activation_count: int,
    machine_fingerprint: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE licenses
            SET activation_count = %s,
                last_activation_at = NOW(),
                last_activated_machine = %s
            WHERE license_key = %s;
            """,
            (activation_count, machine_fingerprint, license_key),
        )


def _record_activation(
    license_key: str,
    machine_fingerprint: str,
    activation_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT max_activations, is_revoked, expires_at, activation_count
                FROM licenses
                WHERE license_key = %s
                FOR UPDATE;
                """,
                (license_key,),
            )
            license_row = cur.fetchone()
            if not license_row:
                return {"ok": False, "error": "invalid_license"}

            if license_row["is_revoked"]:
                return {"ok": False, "error": "license_revoked"}

            expires_at = license_row["expires_at"]
            if expires_at and expires_at < dt.datetime.now(dt.timezone.utc):
                return {"ok": False, "error": "license_expired"}

            current_count = license_row.get("activation_count") or 0

            cur.execute(
                """
                SELECT id FROM license_activations
                WHERE license_key = %s AND machine_fingerprint = %s;
                """,
                (license_key, machine_fingerprint),
            )
            activation_row = cur.fetchone()
            if activation_row:
                cur.execute(
                    """
                    UPDATE license_activations
                    SET last_activated_at = NOW(),
                        activation_metadata = %s
                    WHERE id = %s;
                    """,
                    (Jsonb(activation_metadata), activation_row["id"]),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM license_activations
                    WHERE license_key = %s;
                    """,
                    (license_key,),
                )
                current_count = cur.fetchone()["cnt"]
                if current_count >= license_row["max_activations"]:
                    return {"ok": False, "error": "activation_limit_reached"}

                cur.execute(
                    """
                    INSERT INTO license_activations (
                        license_key, machine_fingerprint, activation_metadata
                    ) VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (license_key, machine_fingerprint, Jsonb(activation_metadata)),
                )
                current_count += 1

            _update_license_activation_metrics(conn, license_key, current_count, machine_fingerprint)
        conn.commit()

    return {"ok": True}


@app.post("/api/admin/create_license")
def create_license() -> Any:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or auth_header.split(" ", maxsplit=1)[1] != ADMIN_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    client_name = (data.get("client_name") or "").strip()
    tier = (data.get("tier") or "pilot").strip()
    max_activations = int(data.get("max_activations") or DEFAULT_MAX_ACTIVATIONS)

    if not email:
        return jsonify({"ok": False, "error": "missing_email"}), 400
    if not client_name:
        return jsonify({"ok": False, "error": "missing_client_name"}), 400

    license_key = _issue_license(email, client_name, tier, max_activations)
    print(f"Issued license for {client_name} <{email}>: {license_key}")
    return jsonify({"ok": True, "license_key": license_key})


@app.get("/api/admin/licenses")
def list_licenses() -> Any:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or auth_header.split(" ", maxsplit=1)[1] != ADMIN_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT license_key,
                   email,
                   client_name,
                   tier,
                   issued_at,
                   expires_at,
                   is_revoked,
                   max_activations,
                   activation_count,
                   last_activation_at,
                   last_activated_machine
            FROM licenses
            ORDER BY issued_at DESC;
            """
        )
        records = [LicenseRecord(**row).to_json() for row in cur.fetchall()]
    return jsonify({"ok": True, "licenses": records})


@app.post("/api/license/verify")
def verify_license() -> Any:
    data = request.get_json(force=True) or {}
    license_key = (data.get("license_key") or "").strip().upper()
    machine_fingerprint = (data.get("machine_fingerprint") or "").strip()
    email = (data.get("email") or "").strip().lower()

    if not license_key:
        return jsonify({"ok": False, "error": "missing_license_key"}), 400
    if not machine_fingerprint:
        return jsonify({"ok": False, "error": "missing_machine_fingerprint"}), 400

    record = _fetch_license(license_key)
    if not record:
        return jsonify({"ok": False, "error": "invalid_license"}), 404
    if record.is_revoked:
        return jsonify({"ok": False, "error": "license_revoked"}), 403
    if record.expires_at and record.expires_at < dt.datetime.now(dt.timezone.utc):
        return jsonify({"ok": False, "error": "license_expired"}), 403
    if email and email != record.email:
        return jsonify({"ok": False, "error": "email_mismatch"}), 403

    activation_metadata = {
        "hostname": data.get("hostname"),
        "platform": data.get("platform"),
        "ip_address": data.get("ip_address"),
        "app_version": data.get("app_version"),
    }
    activation_metadata = {k: v for k, v in activation_metadata.items() if v}
    activation_result = _record_activation(license_key, machine_fingerprint, activation_metadata)
    if not activation_result.get("ok"):
        return jsonify(activation_result), 403

    refreshed = _fetch_license(license_key)
    return jsonify({"ok": True, "license": refreshed.to_json()})


@app.post("/api/admin/licenses/revoke")
def revoke_license() -> Any:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or auth_header.split(" ", maxsplit=1)[1] != ADMIN_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    data = request.get_json(force=True) or {}
    license_key = (data.get("license_key") or "").strip().upper()
    if not license_key:
        return jsonify({"ok": False, "error": "missing_license_key"}), 400

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE licenses SET is_revoked = TRUE WHERE license_key = %s RETURNING license_key;",
            (license_key,),
        )
        updated = cur.fetchone()
        conn.commit()

    if not updated:
        return jsonify({"ok": False, "error": "license_not_found"}), 404
    return jsonify({"ok": True, "license_key": license_key})


init_db()


if __name__ == "__main__":
    print("FCC License Server running on http://localhost:8443")
    app.run(host="0.0.0.0", port=8443)
