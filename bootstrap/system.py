"""
System helper utilities for the FCC bootstrapper.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


LOG = logging.getLogger("fcc.bootstrap.system")


@dataclass(frozen=True)
class PythonResolution:
    """Description of a Python interpreter suitable for running FCC."""

    executable: Path
    args: tuple[str, ...] = ()
    source: str = ""

    def command(self, script: Path, extra_args: Iterable[str] | None = None) -> list[str]:
        cmd = [str(self.executable), *self.args, str(script)]
        if extra_args:
            cmd.extend(extra_args)
        return cmd


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _preferred_python_names() -> Iterable[str]:
    if _is_windows():
        return ("python.exe", "python3.exe", "python")
    return ("python3", "python")


def _iter_candidate_paths() -> Iterable[PythonResolution]:
    """Yield possible Python interpreters in priority order."""
    current = Path(sys.executable) if sys.executable else None
    if current and current.exists():
        yield PythonResolution(current, source="sys.executable")

    seen: set[Path] = set()
    for name in _preferred_python_names():
        path = shutil.which(name)
        if not path:
            continue
        resolved = Path(path).resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        yield PythonResolution(resolved, source=f"PATH:{name}")

    if _is_windows():
        launcher = shutil.which("py")
        if launcher:
            yield PythonResolution(Path(launcher), args=("-3",), source="py-launcher")

        local_programs = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python"
        if local_programs.exists():
            for child in sorted(local_programs.glob("Python3*"), reverse=True):
                candidate = child / "python.exe"
                if candidate.exists():
                    yield PythonResolution(candidate, source=f"LOCALAPPDATA:{child.name}")


def _python_supports_required_version(resolution: PythonResolution) -> bool:
    try:
        result = subprocess.run(
            [str(resolution.executable), *resolution.args, "-c", "import sys; print(sys.version_info[:2])"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:  # noqa: BLE001
        LOG.debug("Version probe failed for %s: %s", resolution.executable, exc)
        return False

    try:
        major, minor = eval(result.stdout.strip(), {"__builtins__": {}})  # noqa: S307
    except Exception as exc:  # noqa: BLE001
        LOG.debug("Unable to parse version from %s output %r: %s", resolution.executable, result.stdout, exc)
        return False

    return (major, minor) >= (3, 11)


def _download_python_windows(tmp_dir: Path) -> Path:
    url = os.environ.get(
        "FCC_PYTHON_INSTALLER_URL",
        "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe",
    )
    target = tmp_dir / "python-installer.exe"
    LOG.info("Downloading Python runtime from %s", url)
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            f"$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '{url}' -OutFile '{target}'",
        ],
        check=True,
    )
    return target


def _run_python_installer_windows(installer: Path) -> None:
    LOG.info("Running Python installer...")
    args = [
        str(installer),
        "/quiet",
        "InstallAllUsers=0",
        "Include_test=0",
        "Include_launcher=1",
        "Include_pip=1",
        "PrependPath=1",
    ]
    result = subprocess.run(args, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Python installer exited with code {result.returncode}")


def _install_python_windows() -> None:
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        installer = _download_python_windows(tmp)
        try:
            _run_python_installer_windows(installer)
        finally:
            installer.unlink(missing_ok=True)


def resolve_python(venv_python: Optional[Path], allow_install: bool = True) -> PythonResolution:
    """Locate a Python 3.11+ interpreter, installing one on Windows if permitted."""
    if venv_python and venv_python.exists():
        return PythonResolution(venv_python, source="venv")

    for candidate in _iter_candidate_paths():
        if _python_supports_required_version(candidate):
            LOG.debug("Selected python %s (%s)", candidate.executable, candidate.source)
            return candidate

    if _is_windows() and allow_install:
        LOG.warning("Python 3.11+ not found. Attempting to install automatically...")
        _install_python_windows()
        return resolve_python(venv_python, allow_install=False)

    raise RuntimeError(
        "Python 3.11 or newer is required but was not found. "
        "Install Python manually and rerun the bootstrapper."
    )


def is_windows_admin() -> bool:
    """Return True if the current process has administrative privileges."""
    if not _is_windows():
        return False
    try:
        import ctypes  # noqa: PLC0415

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
