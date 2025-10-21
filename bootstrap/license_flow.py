"""
Thin wrapper around license_manager so we can reuse its CLI via Python.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from .system import PythonResolution


LOG = logging.getLogger("fcc.bootstrap.license")


class LicenseError(RuntimeError):
    """Raised when licence verification fails."""


def verify_via_interpreter(
    interpreter: PythonResolution,
    repo_root: Path,
    *,
    stateless: bool = False,
    quiet: bool = False,
) -> None:
    script = repo_root / "license_manager.py"
    if not script.exists():
        raise FileNotFoundError(f"license_manager.py not found at {script}")

    cmd = interpreter.command(
        script,
        extra_args=[
            "--verify",
            *(["--stateless"] if stateless else []),
            *(["--quiet"] if quiet else []),
        ],
    )
    LOG.info("Verifying license...")
    result = subprocess.run(cmd, cwd=str(repo_root))
    if result.returncode != 0:
        raise LicenseError("License verification failed.")

