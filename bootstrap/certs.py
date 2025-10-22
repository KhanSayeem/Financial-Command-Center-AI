"""
Certificate provisioning helpers for FCC bootstrapper.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import ssl
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from cert_manager import CertificateManager  # pragma: no cover - type checking only


LOG = logging.getLogger("fcc.bootstrap.certs")
_SITE_PACKAGES_INJECTED: dict[Path, bool] = {}


class CertificateError(RuntimeError):
    """Raised when certificate provisioning fails."""


def _venv_site_packages(venv_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    win_path = venv_dir / "Lib" / "site-packages"
    if win_path.exists():
        candidates.append(win_path)
    lib_dir = venv_dir / "lib"
    if lib_dir.exists():
        for candidate in sorted(lib_dir.glob("python*/site-packages"), reverse=True):
            if candidate.exists():
                candidates.append(candidate)
    return candidates


def _inject_site_packages(venv_dir: Path | None) -> None:
    if not venv_dir:
        return
    if _SITE_PACKAGES_INJECTED.get(venv_dir):
        return
    for site_path in _venv_site_packages(venv_dir):
        if str(site_path) not in sys.path:
            sys.path.insert(0, str(site_path))
    _SITE_PACKAGES_INJECTED[venv_dir] = True


def _manager_type(venv_dir: Path | None) -> Type["CertificateManager"]:
    try:
        from cert_manager import CertificateManager  # pylint: disable=import-outside-toplevel

        return CertificateManager
    except ModuleNotFoundError:
        _inject_site_packages(venv_dir)
        from cert_manager import CertificateManager  # pylint: disable=import-outside-toplevel

        return CertificateManager


def _run_command(cmd: list[str]) -> bool:
    LOG.debug("Executing: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True
    LOG.debug("Command failed (%s): %s", result.returncode, result.stderr.strip())
    return False


def _validate_cert_pair(cert_path: Path, key_path: Path) -> bool:
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
        return True
    except ssl.SSLError as exc:
        LOG.warning("Certificate/key validation failed: %s", exc)
        return False


def ensure_certificates(base_dir: Path, venv_dir: Path | None = None) -> "CertificateManager":
    manager_cls = _manager_type(venv_dir)
    manager = manager_cls(base_dir=base_dir, use_mkcert=True)
    generated = manager.ensure_certificates()

    cert_path = Path(manager.config["cert_file"])
    key_path = Path(manager.config["key_file"])

    if generated:
        LOG.info("Generated fresh certificates in %s", manager.certs_dir)
    elif cert_path.exists() and key_path.exists() and not _validate_cert_pair(cert_path, key_path):
        LOG.info("Regenerating certificates to repair mismatched key pair.")
        if manager.generate_server_certificate():
            LOG.info("Regenerated certificates in %s", manager.certs_dir)
        else:
            raise CertificateError("Failed to regenerate certificate/key pair.")
    else:
        LOG.info("Certificates in %s are valid.", manager.certs_dir)

    return manager


def _install_trust_windows(manager: "CertificateManager") -> bool:
    if manager.install_certificate_to_system_store():
        LOG.info("Windows trust store updated.")
        return True
    LOG.warning("Could not install certificate into Windows trust store automatically.")
    return False


def _install_trust_macos(ca_path: Path) -> bool:
    if not shutil.which("security"):
        LOG.warning("macOS security tool not available. Skipping automatic trust install.")
        return False
    cmd = [
        "security",
        "add-trusted-cert",
        "-d",
        "-r",
        "trustRoot",
        "-k",
        "/Library/Keychains/System.keychain",
        str(ca_path),
    ]
    if os.geteuid() != 0:
        cmd.insert(0, "sudo")
    if _run_command(cmd):
        LOG.info("macOS system trust updated.")
        return True
    LOG.warning("Automatic trust installation failed. Import %s manually via Keychain Access.", ca_path)
    return False


def _install_trust_linux(ca_path: Path) -> bool:
    dest = Path("/usr/local/share/ca-certificates") / ca_path.name
    if not dest.parent.exists():
        LOG.warning(
            "Directory %s not present; skipping automatic trust installation. Import %s manually.",
            dest.parent,
            ca_path,
        )
        return False
    if os.geteuid() != 0:
        copy_cmd = ["sudo", "cp", str(ca_path), str(dest)]
        update_cmd = ["sudo", "update-ca-certificates"]
    else:
        copy_cmd = ["cp", str(ca_path), str(dest)]
        update_cmd = ["update-ca-certificates"]
    if _run_command(copy_cmd) and _run_command(update_cmd):
        LOG.info("System trust updated via update-ca-certificates.")
        return True
    LOG.warning("Automatic Linux trust install failed; manual steps may be required.")
    return False


def install_trust(manager: "CertificateManager", *, skip: bool = False) -> bool:
    if skip:
        LOG.info("Skipping certificate trust installation.")
        return False

    ca_path = Path(manager.config["ca_cert"])
    if not ca_path.exists():
        raise CertificateError(f"CA certificate not found at {ca_path}")

    system = platform.system()
    if system == "Windows":
        return _install_trust_windows(manager)
    if system == "Darwin":
        return _install_trust_macos(ca_path)
    if system == "Linux":
        return _install_trust_linux(ca_path)

    LOG.warning("Automatic trust installation not supported on %s.", system)
    return False
