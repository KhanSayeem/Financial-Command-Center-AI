"""
Virtual environment creation and dependency installation helpers.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .system import PythonResolution


LOG = logging.getLogger("fcc.bootstrap.env")


@dataclass(frozen=True)
class EnvironmentPaths:
    repo_root: Path
    venv_dir: Path
    requirements: Path
    setup_requirements: Path
    lite_requirements: Path


def default_paths(repo_root: Path) -> EnvironmentPaths:
    venv_dir = repo_root / ".venv"
    return EnvironmentPaths(
        repo_root=repo_root,
        venv_dir=venv_dir,
        requirements=repo_root / "requirements.txt",
        setup_requirements=repo_root / "requirements_setup_wizard.txt",
        lite_requirements=repo_root / "requirements_lite.txt",
    )


def ensure_virtualenv(paths: EnvironmentPaths, python: PythonResolution) -> Path:
    if paths.venv_dir.exists():
        LOG.info("Virtual environment already present at %s", paths.venv_dir)
        return paths.venv_dir
    LOG.info("Creating virtual environment at %s", paths.venv_dir)
    paths.venv_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(python.executable), *python.args, "-m", "venv", str(paths.venv_dir)], check=True)
    return paths.venv_dir


def venv_python(venv_dir: Path) -> Path:
    win_path = venv_dir / "Scripts" / "python.exe"
    if win_path.exists():
        return win_path
    return venv_dir / "bin" / "python"


def _run_pip(python_bin: Path, *args: str) -> subprocess.CompletedProcess[str]:
    cmd = [str(python_bin), "-m", "pip", *args]
    LOG.debug("Running pip command: %s", " ".join(cmd))
    return subprocess.run(cmd, text=True, capture_output=True)


def install_dependencies(paths: EnvironmentPaths, python_bin: Path) -> None:
    if not paths.requirements.exists():
        raise FileNotFoundError(f"requirements.txt not found at {paths.requirements}")

    LOG.info("Upgrading pip/setuptools...")
    upgrade = _run_pip(python_bin, "install", "--upgrade", "pip", "setuptools", "wheel")
    if upgrade.returncode != 0:
        LOG.warning("pip upgrade failed: %s", upgrade.stderr.strip())

    LOG.info("Installing application dependencies...")
    primary = _run_pip(
        python_bin,
        "install",
        "--disable-pip-version-check",
        "--prefer-binary",
        "-r",
        str(paths.requirements),
    )
    if primary.returncode == 0:
        LOG.info("Dependencies installed successfully.")
        return

    LOG.error("Primary dependency installation failed:\n%s", primary.stderr.strip())

    if not paths.lite_requirements.exists():
        LOG.info("Creating fallback lite requirements file at %s", paths.lite_requirements)
        paths.lite_requirements.write_text(
            "\n".join(
                [
                    "Flask==2.3.3",
                    "Werkzeug==2.3.7",
                    "Jinja2==3.1.2",
                    "itsdangerous==2.1.2",
                    "click==8.1.7",
                    "Flask-Cors==4.0.1",
                    "requests==2.31.0",
                    "urllib3==2.0.7",
                    "certifi==2023.7.22",
                    "charset-normalizer==3.3.2",
                    "idna==3.4",
                    "cryptography>=42.0.0",
                    "cffi>=1.17.1",
                    "pycparser==2.21",
                    "python-dotenv==1.0.0",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    LOG.info("Retrying with lite dependency set...")
    lite = _run_pip(
        python_bin,
        "install",
        "--disable-pip-version-check",
        "--prefer-binary",
        "-r",
        str(paths.lite_requirements),
    )
    if lite.returncode == 0:
        LOG.info("Lite dependencies installed (demo mode).")
        return

    raise RuntimeError(
        "Dependency installation failed. pip output:\n"
        f"{lite.stderr.strip() or lite.stdout.strip()}"
    )
