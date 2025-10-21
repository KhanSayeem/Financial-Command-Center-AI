"""
Server launch helpers for the bootstrap CLI.
"""

from __future__ import annotations

import logging
import os
import socket
import ssl
import subprocess
import time
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen


LOG = logging.getLogger("fcc.bootstrap.server")


def _pick_port(preferred: int = 8000, attempts: int = 10) -> int:
    tried = []
    for offset in range(attempts):
        port = preferred + offset
        tried.append(port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"Unable to find a free port (tried {tried})")


def start_server(
    python_bin: Path,
    repo_root: Path,
    *,
    env_overrides: Optional[dict[str, str]] = None,
    preferred_port: int = 8000,
    capture_output: bool = True,
) -> tuple[subprocess.Popen[bytes], int, str]:
    entry = repo_root / "app_with_setup_wizard.py"
    if not entry.exists():
        raise FileNotFoundError(f"Application entry not found at {entry}")

    port = _pick_port(preferred_port)
    server_url = f"https://127.0.0.1:{port}"

    env = os.environ.copy()
    env.update(
        {
            "FLASK_ENV": "production",
            "FORCE_HTTPS": "true",
            "ALLOW_HTTP": "false",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "FCC_PORT": str(port),
            "APP_MODE": env.get("APP_MODE", "demo"),
        }
    )
    if env_overrides:
        env.update(env_overrides)

    stdout = subprocess.PIPE if capture_output else None
    stderr = subprocess.PIPE if capture_output else None

    LOG.info("Starting Financial Command Center server on %s", server_url)
    process = subprocess.Popen(
        [str(python_bin), str(entry)],
        cwd=str(repo_root),
        env=env,
        stdout=stdout,
        stderr=stderr,
    )
    return process, port, server_url


def wait_for_health(server_url: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    health_url = f"{server_url}/health"
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    while time.time() < deadline:
        try:
            req = Request(health_url, method="GET")
            with urlopen(req, context=context, timeout=5) as resp:
                if resp.status < 500:
                    LOG.info("Server responded at %s", health_url)
                    return True
        except URLError:
            time.sleep(2)
        except Exception as exc:  # noqa: BLE001
            LOG.debug("Health probe error: %s", exc)
            time.sleep(2)
    return False


def stop_server(process: subprocess.Popen[bytes], wait: bool = True) -> None:
    if process.poll() is not None:
        return
    LOG.info("Stopping server...")
    process.terminate()
    if wait:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            LOG.warning("Forcing server shutdown.")
            process.kill()
