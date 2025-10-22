"""
Cross-platform bootstrap CLI entry point.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import platform
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Callable

from . import certs, env_setup, license_flow, server, system
from .system import PythonResolution, is_windows_admin


LOG = logging.getLogger("fcc.bootstrap")
REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_FLAG = REPO_ROOT / ".fcc_installed"


def _configure_logging(verbose: bool) -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.handlers[:] = [handler]


def _write_install_flag() -> None:
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    INSTALL_FLAG.write_text(f"{timestamp}\n", encoding="utf-8")


def _monitor_process(proc: subprocess.Popen[bytes]) -> None:
    threads = []
    if proc.stdout:
        threads.append(
            threading.Thread(
                target=_stream_pipe, args=(proc.stdout, logging.INFO), daemon=True
            )
        )
    if proc.stderr:
        threads.append(
            threading.Thread(
                target=_stream_pipe, args=(proc.stderr, logging.ERROR), daemon=True
            )
        )
    for t in threads:
        t.start()
    try:
        proc.wait()
    finally:
        for t in threads:
            t.join(timeout=1)


def _stream_pipe(pipe, level: int) -> None:
    for raw in iter(pipe.readline, b""):
        text = raw.decode("utf-8", "replace").rstrip()
        if text:
            LOG.log(level, "[server] %s", text)


def _resolve_python(paths: env_setup.EnvironmentPaths, allow_install: bool) -> PythonResolution:
    venv_py = env_setup.venv_python(paths.venv_dir)
    candidate = venv_py if venv_py.exists() else None
    return system.resolve_python(candidate, allow_install=allow_install)


def _ensure_environment(paths: env_setup.EnvironmentPaths, python_resolution: PythonResolution) -> Path:
    env_setup.ensure_virtualenv(paths, python_resolution)
    venv_bin = env_setup.venv_python(paths.venv_dir)
    env_setup.install_dependencies(paths, venv_bin)
    return venv_bin


def _license_check(interpreter: PythonResolution, stateless: bool, quiet: bool) -> None:
    license_flow.verify_via_interpreter(interpreter, REPO_ROOT, stateless=stateless, quiet=quiet)


def _launch_server(
    paths: env_setup.EnvironmentPaths,
    venv_bin: Path,
    *,
    open_browser: bool,
    detach: bool,
    port: int,
    timeout: int,
) -> int:
    proc, _, url = server.start_server(
        venv_bin,
        paths.repo_root,
        preferred_port=port,
        capture_output=not detach,
    )
    if not server.wait_for_health(url, timeout=timeout):
        if proc.poll() is not None:
            stdout = proc.stdout.read().decode("utf-8", "replace") if proc.stdout else ""
            stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
            LOG.error("Server exited early (code %s).", proc.returncode)
            if stdout:
                LOG.error("stdout:\n%s", stdout)
            if stderr:
                LOG.error("stderr:\n%s", stderr)
            return proc.returncode or 1
        LOG.warning("Server health check timed out.")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Unable to open browser automatically: %s", exc)

    if detach:
        LOG.info("Server running at %s (PID %s).", url, proc.pid)
        return 0

    try:
        _monitor_process(proc)
        return proc.returncode or 0
    except KeyboardInterrupt:
        LOG.info("Stopping server...")
        server.stop_server(proc, wait=True)
        return 0


def _command_install(args: argparse.Namespace) -> int:
    paths = env_setup.default_paths(REPO_ROOT)
    python_resolution = _resolve_python(paths, allow_install=not args.no_auto_python_install)
    venv_bin = _ensure_environment(paths, python_resolution)
    venv_resolution = PythonResolution(venv_bin, source="venv")

    _license_check(venv_resolution, stateless=args.stateless_license, quiet=args.quiet_license)

    manager = certs.ensure_certificates(REPO_ROOT, paths.venv_dir)

    trust_warning = False
    if platform.system() == "Windows" and not args.skip_trust and not is_windows_admin():
        LOG.warning(
            "Administrator privileges are required to install the certificate into the Windows trust store automatically."
        )
        trust_warning = True

    trust_installed = certs.install_trust(manager, skip=args.skip_trust)
    if not trust_installed:
        if platform.system() == "Windows":
            LOG.warning(
                "Install certificate manually with:\n  certutil -user -addstore Root \"%s\"",
                Path(manager.config["ca_cert"]),
            )
        trust_warning = True

    _write_install_flag()
    LOG.info("Installation steps complete.")

    if not args.launch:
        if trust_warning:
            LOG.info("Restart the browser after trusting the certificate to clear cached warnings.")
        return 0

    status = _launch_server(
        paths,
        venv_bin,
        open_browser=args.open_browser,
        detach=args.detach,
        port=args.port,
        timeout=args.timeout,
    )
    if trust_warning:
        LOG.info("Restart the browser after trusting the certificate to clear cached warnings.")
    return status


def _ensure_ready_for_launch(paths: env_setup.EnvironmentPaths) -> Path:
    if not paths.venv_dir.exists():
        raise RuntimeError("Virtual environment not found. Run `fcc-bootstrap install` first.")
    venv_bin = env_setup.venv_python(paths.venv_dir)
    if not venv_bin.exists():
        raise RuntimeError(f"Virtual environment Python missing at {venv_bin}. Re-run install.")
    return venv_bin


def _command_launch(args: argparse.Namespace) -> int:
    paths = env_setup.default_paths(REPO_ROOT)
    venv_bin = _ensure_ready_for_launch(paths)
    venv_resolution = PythonResolution(venv_bin, source="venv")
    if not args.skip_license:
        _license_check(venv_resolution, stateless=args.stateless_license, quiet=True)
    return _launch_server(
        paths,
        venv_bin,
        open_browser=args.open_browser,
        detach=args.detach,
        port=args.port,
        timeout=args.timeout,
    )


def _command_repair(args: argparse.Namespace) -> int:
    paths = env_setup.default_paths(REPO_ROOT)
    python_resolution = _resolve_python(paths, allow_install=not args.no_auto_python_install)
    venv_bin = _ensure_environment(paths, python_resolution)
    venv_resolution = PythonResolution(venv_bin, source="venv")

    if not args.skip_license:
        _license_check(venv_resolution, stateless=args.stateless_license, quiet=args.quiet_license)

    manager = certs.ensure_certificates(REPO_ROOT, paths.venv_dir)

    trust_warning = False
    if platform.system() == "Windows" and not args.skip_trust and not is_windows_admin():
        LOG.warning(
            "Administrator privileges are required to install the certificate into the Windows trust store automatically."
        )
        trust_warning = True

    if not args.skip_trust:
        trust_installed = certs.install_trust(manager, skip=False)
        if not trust_installed:
            if platform.system() == "Windows":
                LOG.warning(
                    "Install certificate manually with:\n  certutil -user -addstore Root \"%s\"",
                    Path(manager.config["ca_cert"]),
                )
            trust_warning = True

    _write_install_flag()
    LOG.info("Repair complete.")

    if not args.launch:
        if trust_warning:
            LOG.info("Restart the browser after trusting the certificate to clear cached warnings.")
        return 0

    status = _launch_server(
        paths,
        venv_bin,
        open_browser=args.open_browser,
        detach=args.detach,
        port=args.port,
        timeout=args.timeout,
    )
    if trust_warning:
        LOG.info("Restart the browser after trusting the certificate to clear cached warnings.")
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fcc-bootstrap",
        description="Financial Command Center cross-platform bootstrapper",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install", help="Perform first-time installation tasks.")
    install.set_defaults(
        handler=_command_install,
        launch=True,
        open_browser=True,
        detach=False,
    )
    install.add_argument("--stateless-license", action="store_true", help="Force online licence verification.")
    install.add_argument("--quiet-license", action="store_true", help="Suppress licence prompts when possible.")
    install.add_argument("--skip-trust", action="store_true", help="Skip installing certificates into OS trust store.")
    install.add_argument("--no-launch", dest="launch", action="store_false", help="Do not launch the server after install.")
    install.add_argument("--no-browser", dest="open_browser", action="store_false", help="Do not open the browser automatically.")
    install.add_argument("--detach", action="store_true", help="Detach after launch and leave the server running.")
    install.add_argument("--port", type=int, default=8000, help="Preferred HTTPS port (default: 8000).")
    install.add_argument("--timeout", type=int, default=60, help="Seconds to wait for health check (default: 60).")
    install.add_argument("--no-auto-python-install", action="store_true", help="Prevent automatic Python installation on Windows.")

    launch = subparsers.add_parser("launch", help="Start the application server using existing installation.")
    launch.set_defaults(
        handler=_command_launch,
        open_browser=True,
        detach=False,
    )
    launch.add_argument("--skip-license", action="store_true", help="Skip licence verification (use cached activation).")
    launch.add_argument("--stateless-license", action="store_true", help="Force fresh licence check before launch.")
    launch.add_argument("--no-browser", dest="open_browser", action="store_false")
    launch.add_argument("--detach", action="store_true")
    launch.add_argument("--port", type=int, default=8000)
    launch.add_argument("--timeout", type=int, default=60)

    repair = subparsers.add_parser("repair", help="Re-run installation checks without clearing data.")
    repair.set_defaults(
        handler=_command_repair,
        launch=False,
        open_browser=True,
        detach=False,
    )
    repair.add_argument("--skip-license", action="store_true")
    repair.add_argument("--stateless-license", action="store_true")
    repair.add_argument("--quiet-license", action="store_true")
    repair.add_argument("--skip-trust", action="store_true")
    repair.add_argument("--launch", action="store_true", help="Launch the server after repair completes.")
    repair.add_argument("--no-browser", dest="open_browser", action="store_false")
    repair.add_argument("--detach", action="store_true")
    repair.add_argument("--port", type=int, default=8000)
    repair.add_argument("--timeout", type=int, default=60)
    repair.add_argument("--no-auto-python-install", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    handler: Callable[[argparse.Namespace], int] = getattr(args, "handler")
    try:
        return handler(args)
    except RuntimeError as exc:
        LOG.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        LOG.warning("Cancelled by user.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
