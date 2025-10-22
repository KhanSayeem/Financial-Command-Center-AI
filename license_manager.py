#!/usr/bin/env python3
"""
Client-side license management for Financial Command Center.
Handles prompting the user for license information, verifying with the
license server, and persisting the activation locally.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import platform
import ssl
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import urllib.error
import urllib.request
from urllib.parse import urlparse, urlunparse

try:
    import requests  # type: ignore[import]
except ModuleNotFoundError:  # pragma: no cover - fallback when requests is unavailable
    requests = None  # type: ignore[assignment]

if requests:
    NETWORK_ERRORS: tuple[type[Exception], ...] = (requests.RequestException,)  # type: ignore[attr-defined]
else:  # pragma: no cover - exercised when requests cannot be imported
    NETWORK_ERRORS = (
        urllib.error.URLError,
        urllib.error.HTTPError,
        ssl.SSLError,
        TimeoutError,
        ConnectionError,
    )


class _SimpleResponse:
    """Minimal response wrapper used when requests is unavailable."""

    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self._text = text

    def json(self) -> Any:
        if not self._text:
            raise ValueError("Empty response body")
        return json.loads(self._text)

    @property
    def text(self) -> str:
        return self._text


def _post_json(url: str, payload: Dict[str, Any], *, timeout: int, verify: bool):
    if requests:
        return requests.post(url, json=payload, timeout=timeout, verify=verify)
    return _urllib_post_json(url, payload, timeout=timeout, verify=verify)


def _urllib_post_json(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout: int,
    verify: bool,
) -> _SimpleResponse:
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    context = None
    if url.lower().startswith("https://"):
        context = ssl.create_default_context()
        if not verify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            text = response.read().decode("utf-8", "replace")
            status = response.getcode() or 0
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", "replace")
        return _SimpleResponse(exc.code, text)
    return _SimpleResponse(status, text)

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    def load_dotenv(path: Path | str | None = None, override: bool = False) -> bool:
        env_path = Path(path or ".env")
        if not env_path.exists():
            return False
        with env_path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                if "=" not in raw or raw.strip().startswith("#"):
                    continue
                key, value = raw.split("=", 1)
                key = key.strip()
                value = value.strip().strip('\"\'')
                if override or key not in os.environ:
                    os.environ[key] = value
        return True

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

try:
    import tkinter as tk
    from tkinter import messagebox, ttk

    TK_AVAILABLE = True
except Exception:  # pragma: no cover - tkinter not always available (e.g., headless tests)
    TK_AVAILABLE = False


class NullLogger:
    """Fallback logger when none is provided."""

    def info(self, message: str) -> None:  # pragma: no cover - trivial
        print(message)

    def warning(self, message: str) -> None:  # pragma: no cover - trivial
        print(f"WARNING: {message}")

    def error(self, message: str) -> None:  # pragma: no cover - trivial
        print(f"ERROR: {message}")


def _normalize_host(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.strip("[]").lower()


def _is_localhost(host: Optional[str]) -> bool:
    normalized = _normalize_host(host)
    return normalized in {"localhost", "127.0.0.1", "::1"}


def _resolve_data_dir() -> Path:
    """Return a writable directory for storing license artifacts."""
    try:
        if os.name == "nt":
            base = os.environ.get("APPDATA")
            if not base:
                base = Path.home() / "AppData" / "Roaming"
            data_dir = Path(base) / "Financial Command Center"
        else:
            data_dir = Path.home() / ".local" / "share" / "financial-command-center"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    except Exception:
        return Path.cwd()


def compute_machine_fingerprint() -> str:
    """Generate a stable fingerprint for the current device."""
    components = [
        platform.node(),
        platform.system(),
        platform.machine(),
        platform.version(),
    ]
    try:
        mac = uuid.getnode()
        components.append(hex(mac))
    except Exception:
        components.append("mac-unknown")
    try:
        import subprocess

        if os.name == "nt":
            result = subprocess.run(
                ["wmic", "csproduct", "get", "uuid"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            system_uuid = next(
                (line.strip() for line in result.stdout.splitlines() if line.strip() and "UUID" not in line),
                "",
            )
            if system_uuid:
                components.append(system_uuid)
    except Exception:
        components.append("uuid-unknown")

    raw = "|".join(filter(None, components)).encode("utf-8", "ignore")
    return hashlib.sha256(raw).hexdigest()


class LicenseManager:
    """Handles license verification and persistence."""

    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger or NullLogger()
        server = os.getenv("LICENSE_SERVER", "https://license.daywinlabs.com").rstrip("/")
        if not server:
            server = "https://license.daywinlabs.com"
        self.license_server = server
        self.verify_ssl = os.getenv("LICENSE_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}
        self.license_path = _resolve_data_dir() / "license.json"
        self.machine_fingerprint = compute_machine_fingerprint()
        self.cache_max_hours = max(1, int(os.getenv("LICENSE_CACHE_MAX_HOURS", "72")))
        self.offline_grace_hours = max(1, int(os.getenv("LICENSE_OFFLINE_GRACE_HOURS", "12")))
        self._cipher_key = hashlib.sha256(self.machine_fingerprint.encode("utf-8")).digest()
        self._env_applied = False
        self._allow_insecure_server = os.getenv("ALLOW_INSECURE_LICENSE_SERVER", "").lower() in {"1", "true", "yes"}
        self._candidate_servers: list[str] = []
        self._disable_https_fallback = os.getenv("LICENSE_DISABLE_HTTPS_FALLBACK", "").lower() in {"1", "true", "yes"}

        parsed = urlparse(self.license_server)
        host = _normalize_host(parsed.hostname)
        if parsed.scheme not in {"http", "https"}:
            raise RuntimeError(f"Unsupported LICENSE_SERVER scheme: {parsed.scheme}")

        if parsed.scheme == "http" and not (self._allow_insecure_server or _is_localhost(host)):
            raise RuntimeError(
                "LICENSE_SERVER must use HTTPS for remote servers. "
                "Set ALLOW_INSECURE_LICENSE_SERVER=1 to permit HTTP or use localhost."
            )

        self._add_candidate(self.license_server)

        if parsed.scheme == "https" and _is_localhost(host):
            fallback = urlunparse(
                ("http", parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
            ).rstrip("/")
            self._add_candidate(fallback, priority=True)
        elif parsed.scheme == "http" and _is_localhost(host) and not self._disable_https_fallback:
            alt = urlunparse(
                ("https", parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
            ).rstrip("/")
            self._add_candidate(alt)

        if parsed.scheme == "http":
            self.verify_ssl = False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def ensure_valid_license(
        self,
        force_prompt: bool = False,
        quiet: bool = False,
        *,
        skip_cache: bool = False,
        persist_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Ensure a license is present and verified with the server."""
        cached = None if force_prompt else self._load_license(apply_env=not skip_cache)
        email = (cached or {}).get("email")
        if not persist_cache:
            self._delete_cached_license()
        license_key = None if skip_cache else (cached or {}).get("license_key")

        attempts = 0
        while attempts < 3:
            if not license_key:
                response = self._prompt_for_license(default_email=email, quiet=quiet)
                if not response:
                    if not quiet:
                        self._show_error("License verification is required to continue.")
                    return None
                license_key = response["license_key"]
                email = response["email"]

            verification = self._verify_with_server(license_key, email)
            if verification.get("ok"):
                payload = verification["license"]
                payload["license_key"] = license_key
                payload["email"] = email or payload.get("email")
                payload["machine_fingerprint"] = self.machine_fingerprint
                payload["verified_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
                payload["cache_expires_at"] = self._next_cache_expiry().isoformat()
                if persist_cache:
                    self._persist_license(payload)
                else:
                    self._delete_cached_license()
                self._apply_env(payload)

                masked = self._mask_license(license_key)
                self.logger.info(
                    f"License verified ({masked}) "
                    f"[activation {payload.get('activation_count')}/{payload.get('max_activations')}]"
                )
                return payload

            error_code = verification.get("error")
            if (
                cached
                and not skip_cache
                and cached.get("license_key") == license_key
                and cached.get("machine_fingerprint") == self.machine_fingerprint
                and not self._cache_expired(cached)
                and error_code in {"network_error", "invalid_server_response"}
            ):
                cached["offline_mode"] = True
                self._apply_env(cached)
                self.logger.warning(
                    "License server unreachable; proceeding in offline mode with cached activation."
                )
                return cached

            attempts += 1
            if not quiet:
                self._show_error(self._humanize_error(verification.get("error")))
            license_key = None  # Force re-prompt

        return None

    def load_cached_license(self) -> Optional[Dict[str, Any]]:
        """Return cached license information if present."""
        return self._load_license()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _verify_with_server(self, license_key: str, email: Optional[str]) -> Dict[str, Any]:
        payload = {
            "license_key": license_key,
            "machine_fingerprint": self.machine_fingerprint,
            "email": email,
            "hostname": platform.node(),
            "platform": platform.platform(),
            "app_version": os.getenv("APP_VERSION"),
        }
        last_error: Optional[Exception] = None
        for target in self._server_candidates():
            self.logger.info(f"Attempting license verification via {target}")
            url = f"{target}/api/license/verify"
            verify_flag = self.verify_ssl if target.startswith("https://") else False
            try:
                response = _post_json(url, payload, timeout=15, verify=verify_flag)
            except NETWORK_ERRORS as exc:  # pragma: no cover - network failures are environment-specific
                last_error = exc
                continue
            except Exception as exc:  # pragma: no cover - unexpected transport failure
                last_error = exc
                continue

            try:
                data = response.json()
            except ValueError:
                return {"ok": False, "error": "invalid_server_response"}

            if response.status_code >= 400 and "error" in data:
                return data

            if target != self.license_server:
                self._add_candidate(target, priority=True)
                self.license_server = target
            return data

        if last_error is not None:
            self.logger.error(f"Failed to reach license server: {last_error}")
        return {"ok": False, "error": "network_error"}

    def _prompt_for_license(self, default_email: Optional[str], quiet: bool) -> Optional[Dict[str, str]]:
        if TK_AVAILABLE:
            return self._prompt_with_tk(default_email)
        if quiet:
            return None
        return self._prompt_console(default_email)

    def _server_candidates(self) -> tuple[str, ...]:
        seen = set()
        ordered = []
        for candidate in self._candidate_servers:
            if candidate and candidate not in seen:
                seen.add(candidate)
                ordered.append(candidate)
        return tuple(ordered)

    def _add_candidate(self, value: Optional[str], priority: bool = False) -> None:
        if not value:
            return
        normalized = value.rstrip("/")
        if not normalized:
            return
        if normalized in self._candidate_servers:
            if priority:
                self._candidate_servers.remove(normalized)
                self._candidate_servers.insert(0, normalized)
            return
        if priority:
            self._candidate_servers.insert(0, normalized)
        else:
            self._candidate_servers.append(normalized)

    def _prompt_with_tk(self, default_email: Optional[str]) -> Optional[Dict[str, str]]:
        result: Dict[str, Any] = {"ok": False}

        root = tk.Tk()
        root.title("Financial Command Center License Required")
        root.geometry("420x260")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        key_var = tk.StringVar()
        raw_default_email = (default_email or "").strip()
        if raw_default_email and "@" not in raw_default_email:
            raw_default_email = ""
        email_var = tk.StringVar(value=raw_default_email)

        def submit() -> None:
            license_key = key_var.get().strip().upper()
            email_value = email_var.get().strip()
            if not license_key:
                messagebox.showerror("License Required", "Please enter your license key to continue.", parent=root)
                return
            result["license_key"] = license_key
            result["email"] = email_value
            result["ok"] = True
            root.destroy()

        def cancel() -> None:
            result["ok"] = False
            root.destroy()

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Enter your Financial Command Center license key").pack(anchor=tk.W)
        key_entry = ttk.Entry(frame, textvariable=key_var, width=45, show="*")
        key_entry.pack(pady=(6, 12), fill=tk.X)
        key_entry.focus_set()

        ttk.Label(frame, text="Registered email (optional, recommended)").pack(anchor=tk.W)
        ttk.Entry(frame, textvariable=email_var, width=45).pack(pady=(6, 12), fill=tk.X)

        info = (
            "Your license is tied to this device. "
            "Contact support if you need to move the installation."
        )
        ttk.Label(frame, text=info, wraplength=360).pack(pady=(0, 12), anchor=tk.W)

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Button(button_frame, text="Verify License", command=submit).pack(side=tk.RIGHT)

        root.protocol("WM_DELETE_WINDOW", cancel)
        root.mainloop()

        if result.get("ok"):
            return {"license_key": result["license_key"], "email": result["email"]}
        return None

    def _prompt_console(self, default_email: Optional[str]) -> Optional[Dict[str, str]]:
        print("\n=== Financial Command Center License Verification ===")
        try:
            license_key = input("License key: ").strip().upper()
            if not license_key:
                return None
            email = input(f"Registered email [{default_email or 'optional'}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        return {"license_key": license_key, "email": email or default_email or ""}

    def _load_license(self, apply_env: bool = True) -> Optional[Dict[str, Any]]:
        if not self.license_path.exists():
            return None
        try:
            raw_text = self.license_path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
            if isinstance(data, dict) and data.get("_format") == "fcc-license-cache":
                decrypted = self._decrypt_payload(data.get("data"))
                payload = json.loads(decrypted)
            else:
                # Backwards compatibility with plaintext caches
                payload = data if isinstance(data, dict) else None
            if not isinstance(payload, dict):
                return None
            if payload.get("machine_fingerprint") != self.machine_fingerprint:
                return None
            if self._cache_expired(payload):
                self.logger.info("Cached license expired; re-verification required.")
                return None
            if apply_env:
                self._apply_env(payload)
            return payload
        except Exception:
            self.logger.warning("Existing license cache is invalid and will be ignored.")
            return None

    def _persist_license(self, payload: Dict[str, Any]) -> None:
        try:
            self.license_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.license_path.with_suffix(".tmp")
            serialized = json.dumps(payload, indent=2)
            envelope = {
                "_format": "fcc-license-cache",
                "version": 2,
                "encrypted": True,
                "data": self._encrypt_payload(serialized),
            }
            tmp_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
            os.replace(tmp_path, self.license_path)
            try:
                os.chmod(self.license_path, 0o600)
            except Exception:
                pass
        except Exception as exc:
            self.logger.warning(f"Failed to persist license cache: {exc}")

    def _delete_cached_license(self) -> None:
        try:
            if self.license_path.exists():
                self.license_path.unlink()
        except Exception as exc:
            self.logger.warning(f"Failed to delete cached license: {exc}")

    def _show_error(self, message: str) -> None:
        if TK_AVAILABLE:
            messagebox.showerror("License Verification Failed", message)
        else:
            print(f"ERROR: {message}")

    def _humanize_error(self, code: Optional[str]) -> str:
        mapping = {
            "invalid_license": "The license key you entered is not recognized. Please verify and try again.",
            "license_revoked": "This license has been revoked. Contact support for assistance.",
            "license_expired": "Your license has expired. Contact support to renew your access.",
            "email_mismatch": "The license key does not match the provided email address.",
            "activation_limit_reached": (
                "This license has reached the maximum number of activations. Contact support to reset it."
            ),
            "network_error": "Could not reach the license server. Check your internet connection and try again.",
            "invalid_server_response": "Received an unexpected response from the license server. Try again later.",
            "missing_license_key": "License key missing from request.",
            "missing_machine_fingerprint": "Machine fingerprint missing from request.",
        }
        return mapping.get(code or "", "Unable to verify your license. Please try again or contact support.")

    @staticmethod
    def _mask_license(license_key: Optional[str]) -> str:
        if not license_key:
            return "unknown"
        key = license_key.replace("-", "")
        if len(key) <= 8:
            return key
        return f"{key[:6]}…{key[-4:]}"

    def _next_cache_expiry(self) -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=self.cache_max_hours)

    def _cache_expired(self, payload: Dict[str, Any]) -> bool:
        expiry = payload.get("cache_expires_at")
        if not expiry:
            return True
        try:
            expiry_dt = dt.datetime.fromisoformat(expiry)
        except ValueError:
            return True
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=dt.timezone.utc)
        return dt.datetime.now(dt.timezone.utc) >= expiry_dt

    def _xor_cipher(self, data: bytes) -> bytes:
        key = self._cipher_key
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def _encrypt_payload(self, plaintext: str) -> Dict[str, str]:
        raw = plaintext.encode("utf-8")
        cipher = self._xor_cipher(raw)
        token = base64.urlsafe_b64encode(cipher).decode("ascii")
        signature = hashlib.sha256(raw + self._cipher_key).hexdigest()
        return {"cipher": token, "sig": signature, "algo": "xor-sha256"}

    def _decrypt_payload(self, envelope: Optional[Dict[str, str]]) -> str:
        if not envelope:
            raise ValueError("Missing license payload")
        cipher_b64 = envelope.get("cipher")
        signature = envelope.get("sig")
        if not cipher_b64 or not signature:
            raise ValueError("Incomplete license payload")
        cipher = base64.urlsafe_b64decode(cipher_b64.encode("ascii"))
        raw = self._xor_cipher(cipher)
        expected_sig = hashlib.sha256(raw + self._cipher_key).hexdigest()
        if expected_sig != signature:
            raise ValueError("License payload integrity check failed")
        return raw.decode("utf-8")

    def _apply_env(self, payload: Optional[Dict[str, Any]]) -> None:
        if self._env_applied or not payload:
            return
        license_key = payload.get("license_key", "")
        email = payload.get("email", "")
        client_name = payload.get("client_name", "")
        os.environ.setdefault("FCC_LICENSE_KEY", license_key)
        if email:
            os.environ.setdefault("FCC_LICENSE_EMAIL", email)
        if client_name:
            os.environ.setdefault("FCC_LICENSE_CLIENT", client_name)
        watermark = f"{client_name or 'unknown'}::{self._mask_license(license_key)}"
        os.environ.setdefault("FCC_LICENSE_TAG", watermark)
        signature_source = f"{license_key}|{self.machine_fingerprint}|{client_name}"
        os.environ.setdefault("FCC_LICENSE_SIGNATURE", hashlib.sha256(signature_source.encode("utf-8")).hexdigest())
        self._env_applied = True


_GLOBAL_LICENSE_PAYLOAD: Optional[Dict[str, Any]] = None


def ensure_cli_license(
    force_prompt: bool = False,
    quiet: bool = False,
    *,
    skip_cache: bool = False,
    persist_cache: bool = True,
) -> Dict[str, Any]:
    """
    Convenience helper for CLI entrypoints.
    Ensures a valid license is present or exits the process.
    """
    global _GLOBAL_LICENSE_PAYLOAD
    if _GLOBAL_LICENSE_PAYLOAD and not skip_cache:
        return _GLOBAL_LICENSE_PAYLOAD

    manager = LicenseManager()
    payload = manager.ensure_valid_license(
        force_prompt=force_prompt,
        quiet=quiet,
        skip_cache=skip_cache,
        persist_cache=persist_cache,
    )
    if not payload:
        raise SystemExit(2)
    _GLOBAL_LICENSE_PAYLOAD = payload
    return payload


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Financial Command Center License Manager")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify license interactively (default action when no args provided).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-prompting for a license even if a cached activation exists.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Run without showing GUI/console prompts (non-zero exit when verification required).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Skip using cached activations and always prompt/verify online.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Do not write a verified license to the local cache.",
    )
    parser.add_argument(
        "--stateless",
        action="store_true",
        help="Shortcut for --no-cache --no-persist to force fresh online verification without caching.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:  # pragma: no cover - CLI wrapper
    args = _parse_args(argv)
    manager = LicenseManager()

    if not args.verify and not argv:
        args.verify = True

    if args.stateless:
        args.no_cache = True
        args.no_persist = True

    skip_cache = args.no_cache
    persist_cache = not args.no_persist
    force_prompt = args.force or skip_cache

    if args.verify:
        license_payload = manager.ensure_valid_license(
            force_prompt=force_prompt,
            quiet=args.quiet,
            skip_cache=skip_cache,
            persist_cache=persist_cache,
        )
        return 0 if license_payload else 1

    print("No action requested. Use --verify to trigger license verification.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI execution
    sys.exit(main())
