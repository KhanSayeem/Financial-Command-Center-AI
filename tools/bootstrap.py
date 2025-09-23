#!/usr/bin/env python3
"""Prepare local environment for Financial Command Center.
Creates/updates the virtual environment, installs dependencies,
and refreshes HTTPS certificates so `ultimate_cert_fix.cmd`
can launch reliably for non-technical users.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

BASE_ENV = os.environ.copy()
BASE_ENV.setdefault("PYTHONUTF8", "1")
BASE_ENV.setdefault("PYTHONIOENCODING", "utf-8")

DEFAULT_VENV = REPO_ROOT / ".venv"
DEFAULT_STATUS = REPO_ROOT / "bootstrap_status.json"
REQUIREMENTS = REPO_ROOT / "requirements.txt"


class StepError(RuntimeError):
    """Raised when a bootstrap step fails."""


def _log(message: str) -> None:
    print(message, flush=True)


def _run(cmd: list[str], *, cwd: Optional[Path] = None, capture: bool = False, env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    _log("  > " + " ".join(cmd))
    run_env = BASE_ENV.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=capture,
        env=run_env,
    )


def _venv_python(venv_path: Path) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def ensure_venv(venv_path: Path, *, force: bool = False) -> tuple[bool, Path]:
    if venv_path.exists() and not force:
        python_path = _venv_python(venv_path)
        if python_path.exists():
            _log(f"Virtual environment already in place at {venv_path}")
            return False, python_path
        _log("Existing virtual environment missing python executable; recreating.")
        force = True

    if force and venv_path.exists():
        _log(f"Recreating virtual environment at {venv_path}")
        shutil.rmtree(venv_path)
    elif not venv_path.exists():
        _log(f"Creating virtual environment at {venv_path}")

    try:
        _run([sys.executable, "-m", "venv", str(venv_path)])
    except subprocess.CalledProcessError as exc:
        raise StepError("Failed to create virtual environment") from exc

    python_path = _venv_python(venv_path)
    if not python_path.exists():
        raise StepError("Virtual environment created but python executable missing")
    return True, python_path


def ensure_dependencies(python_path: Path, *, requirements: Path, upgrade_pip: bool = True) -> bool:
    if not requirements.exists():
        _log(f"No {requirements.name} file found; skipping dependency install")
        return False

    changed = False
    if upgrade_pip:
        _log("Upgrading pip in virtual environment (best effort)")
        try:
            _run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])
        except subprocess.CalledProcessError:
            _log("  ! pip upgrade failed; proceeding anyway")
    _log(f"Installing dependencies from {requirements}")
    try:
        _run([str(python_path), "-m", "pip", "install", "-r", str(requirements)])
        changed = True
    except subprocess.CalledProcessError as exc:
        raise StepError("Dependency installation failed") from exc
    return changed


def refresh_certificates(python_path: Path, *, force: bool = False) -> dict[str, bool]:
    cert_manager = REPO_ROOT / "cert_manager.py"
    if not cert_manager.exists():
        _log("cert_manager.py not found; skipping certificate management")
        return {"mkcert": False, "generate": False, "bundle": False, "health": False}

    status = {"mkcert": False, "generate": False, "bundle": False, "health": False}

    def run_cert(args: list[str]) -> bool:
        try:
            _run([str(python_path), str(cert_manager), *args])
            return True
        except subprocess.CalledProcessError as exc:
            raise StepError(f"cert_manager failed: {' '.join(args)}") from exc

    if force:
        _log("Forcing certificate regeneration")
    _log("Ensuring mkcert root CA is installed")
    status["mkcert"] = run_cert(["--mkcert"])

    _log("Generating application certificates")
    status["generate"] = run_cert(["--generate"])

    _log("Creating client bundle")
    status["bundle"] = run_cert(["--bundle"])

    _log("Running certificate health check")
    try:
        result = _run([str(python_path), str(cert_manager), "--health"], capture=True)
        status["health"] = True
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                _log("    " + line)
    except subprocess.CalledProcessError as exc:
        raise StepError("Certificate health check failed") from exc

    return status


def write_status(status_file: Path, payload: dict) -> None:
    status_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap FCC environment")
    parser.add_argument("--venv", type=Path, default=DEFAULT_VENV, help="Virtualenv path (default: .venv)")
    parser.add_argument("--status-file", type=Path, default=DEFAULT_STATUS, help="Where to write bootstrap status JSON")
    parser.add_argument("--skip-install", action="store_true", help="Skip dependency installation")
    parser.add_argument("--skip-cert", action="store_true", help="Skip certificate management")
    parser.add_argument("--force-cert", action="store_true", help="Force certificate regeneration even if not needed")
    parser.add_argument("--force-venv", action="store_true", help="Recreate virtualenv even if it exists")
    parser.add_argument("--requirements", type=Path, default=REQUIREMENTS, help="Requirements file to install")

    args = parser.parse_args(argv)

    _log("Preparing Financial Command Center environment...")
    start_time = time.time()
    status_payload: dict[str, object] = {
        "timestamp": start_time,
        "repo_root": str(REPO_ROOT),
        "venv": str(args.venv),
        "venv_created": False,
        "dependencies_installed": False,
        "certificates": {},
    }

    try:
        venv_created, python_path = ensure_venv(args.venv, force=args.force_venv)
        status_payload["venv_created"] = venv_created
        status_payload["venv_python"] = str(python_path)

        if not args.skip_install:
            deps_changed = ensure_dependencies(python_path, requirements=args.requirements)
            status_payload["dependencies_installed"] = deps_changed
        else:
            _log("Skipping dependency installation (per flag)")

        if not args.skip_cert:
            cert_status = refresh_certificates(python_path, force=args.force_cert)
            status_payload["certificates"] = cert_status
        else:
            _log("Skipping certificate management (per flag)")

        duration = time.time() - start_time
        status_payload["duration_seconds"] = round(duration, 2)
        write_status(args.status_file, status_payload)
        _log(f"Bootstrap complete in {duration:.1f}s")
        return 0

    except StepError as exc:
        _log(f"ERROR: {exc}")
    except subprocess.CalledProcessError as exc:
        _log("ERROR: Command failed while running bootstrap")
    except Exception as exc:  # pragma: no cover
        _log(f"Unexpected error: {exc}")

    write_status(args.status_file, {"error": True, "timestamp": time.time()})
    return 1


if __name__ == "__main__":
    sys.exit(main())
