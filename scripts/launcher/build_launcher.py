#!/usr/bin/env python3

"""

Build Script for Financial Command Center AI Launcher

====================================================



This script packages the Financial Command Center AI launcher with PyInstaller

and prepares a redistributable bundle that includes helper scripts, assets, and

sanitised configuration files.



Usage:

    python scripts/launcher/build_launcher.py

"""



import json

import os

import shutil

import subprocess

import sys

from datetime import datetime, timezone

from pathlib import Path

from typing import List, Optional



REPO_ROOT = Path(__file__).resolve().parents[2]

os.chdir(REPO_ROOT)



# Ensure UTF-8 stdout on Windows consoles to avoid UnicodeEncodeError

try:

    if hasattr(sys.stdout, "reconfigure"):

        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

except Exception:

    pass



# Build configuration

BUILD_DIR = Path("build")

DIST_DIR = Path("dist")

SPEC_FILE = Path("financial_launcher.spec")

MAIN_SCRIPT = Path("financial_launcher.py")

ICON_FILE = Path("assets/application.ico")

LAUNCHER_NAME = "Financial-Command-Center-Launcher"

PACKAGE_DIR_NAME = "FCC"

PACKAGE_DIR = Path(PACKAGE_DIR_NAME)

RELEASE_DIR = Path("release")

UPLOAD_SPLIT_LIMIT_MB = 49

INCLUDE_EXECUTABLE_IN_PACKAGE = False



# Version info for Windows executable

VERSION_INFO = """

# UTF-8

#

VSVersionInfo(

  ffi=FixedFileInfo(

filevers=(1, 0, 0, 0),

prodvers=(1, 0, 0, 0),

mask=0x3f,

flags=0x0,

OS=0x40004,

fileType=0x1,

subtype=0x0,

date=(0, 0)

),

  kids=[

StringFileInfo(

  [

  StringTable(

    u'040904B0',

    [StringStruct(u'CompanyName', u'Financial Command Center'),

    StringStruct(u'FileDescription', u'Financial Command Center AI Launcher'),

    StringStruct(u'FileVersion', u'1.0.0.0'),

    StringStruct(u'InternalName', u'financial_launcher'),

    StringStruct(u'LegalCopyright', u'Copyright (c) 2024 Financial Command Center'),

    StringStruct(u'OriginalFilename', u'Financial-Command-Center-Launcher.exe'),

    StringStruct(u'ProductName', u'Financial Command Center AI'),

    StringStruct(u'ProductVersion', u'1.0.0.0')])

  ]),

VarFileInfo([VarStruct(u'Translation', [1033, 1200])])

  ]

)

"""



# Shortcut script replacement blocks (all ASCII for cross-platform safety)

CREATE_SHORTCUT_ICON_OLD = (

    'if exist "%CURRENT_DIR%\\assets\\favicon.ico" set "ICON_PATH=%CURRENT_DIR%\\assets\\favicon.ico"\n'

    'if not defined ICON_PATH if exist "%CURRENT_DIR%\\assets\\application.ico" set "ICON_PATH=%CURRENT_DIR%\\assets\\application.ico"\n'

    'if not defined ICON_PATH if exist "%CURRENT_DIR%\\installer_package\\assets\\application.ico" set "ICON_PATH=%CURRENT_DIR%\\installer_package\\assets\\application.ico"\n'

    'if not defined ICON_PATH if exist "%CURRENT_DIR%\\installer_package\\assets\\credit-card.ico" set "ICON_PATH=%CURRENT_DIR%\\installer_package\\assets\\credit-card.ico"\n'

)

CREATE_SHORTCUT_ICON_NEW = (

    'set "ICON_PATH=%CURRENT_DIR%\\assets\\application.ico"\n'

    f'if not exist "%ICON_PATH%" set "ICON_PATH=%CURRENT_DIR%\\{PACKAGE_DIR_NAME}\\assets\\application.ico"\n'

    'if not exist "%ICON_PATH%" set "ICON_PATH="\n'

)

ULTIMATE_SHORTCUT_ICON_OLD = (

    '    set "SHORTCUT_ICON="\n'

    '    if exist "%SCRIPT_DIR%\\assets\\application.ico" set "SHORTCUT_ICON=%SCRIPT_DIR%\\assets\\application.ico"\n'

    '    if not defined SHORTCUT_ICON if exist "%SCRIPT_DIR%\\installer_package\\assets\\application.ico" set "SHORTCUT_ICON=%SCRIPT_DIR%\\installer_package\\assets\\application.ico"\n'

    '    if not defined SHORTCUT_ICON if exist "%SCRIPT_DIR%\\assets\\favicon.ico" set "SHORTCUT_ICON=%SCRIPT_DIR%\\assets\\favicon.ico"\n'

    '    if defined SHORTCUT_ICON (\n'

)

ULTIMATE_SHORTCUT_ICON_NEW = (

    '    set "SHORTCUT_ICON=%SCRIPT_DIR%\\assets\\application.ico"\n'

    f'    if not exist "!SHORTCUT_ICON!" set "SHORTCUT_ICON=%SCRIPT_DIR%\\{PACKAGE_DIR_NAME}\\assets\\application.ico"\n'

    '    if exist "!SHORTCUT_ICON!" (\n'

)



def build_admin_ui_bundle() -> bool:

    """Ensure the React admin UI is built before packaging."""

    admin_ui_dir = REPO_ROOT / "fcc_bootstrap" / "admin_ui"

    if not admin_ui_dir.exists():

        print("?? Admin UI directory not found; skipping bundle step.")

        return True



    npm_executable = shutil.which("npm")

    if npm_executable is None:

        print("?? npm is not available on PATH. Install Node.js to build the admin UI bundle.")

        return False



    node_modules_dir = admin_ui_dir / "node_modules"

    if not node_modules_dir.exists():

        print("   Installing admin UI dependencies (npm install)...")

        install_result = subprocess.run(

            [npm_executable, "install"],

            cwd=admin_ui_dir,

            check=False,

        )

        if install_result.returncode != 0:

            print("?? Failed to install admin UI dependencies.")

            return False



    print("   Building admin UI bundle (npm run build)...")

    build_result = subprocess.run(

        [npm_executable, "run", "build"],

        cwd=admin_ui_dir,

        check=False,

    )

    if build_result.returncode != 0:

        print("?? Failed to build the admin UI bundle.")

        return False



    if DIST_DIR.exists():

        shutil.rmtree(DIST_DIR, ignore_errors=True)

        print("   Removed dist/ directory to avoid duplicate executables in release artefacts.")



    return True





def create_icon() -> Path | None:

    """Ensure the canonical application icon exists, creating it from fallbacks if needed."""

    icon_path = ICON_FILE

    if icon_path.exists():

        return icon_path



    fallback_candidates = [

        Path("assets/favicon.ico"),

        Path("assets/favicon.png"),

        Path("assets/logo.png"),

    ]



    for candidate in fallback_candidates:

        if not candidate.exists():

            continue

        if candidate.suffix.lower() == ".ico":

            shutil.copy2(candidate, icon_path)

            print(f"🎯 Copied fallback icon {candidate} -> {icon_path}")

            return icon_path



        try:

            from PIL import Image  # Lazy import; Pillow may not be installed



            with Image.open(candidate) as image:

                image.save(

                    icon_path,

                    format="ICO",

                    sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)],

                )

            print(f"🎯 Generated {icon_path} from {candidate}")

            return icon_path

        except ImportError:

            print("⚠️  Pillow not installed; cannot convert fallback icon.")

            break

        except Exception as exc:

            print(f"⚠️  Failed to convert {candidate} to ICO: {exc}")



    print(f"⚠️  Icon not found at {icon_path}")

    return None





def create_version_file() -> Path:

    """Create the version file consumed by PyInstaller."""

    version_file = Path("version.txt")

    version_file.write_text(VERSION_INFO, encoding="utf-8")

    return version_file





def install_build_dependencies() -> bool:

    """Install PyInstaller and other build dependencies."""

    print("📦 Installing build dependencies...")

    try:

        subprocess.check_call(

            [sys.executable, "-m", "pip", "install", "-r", "launcher_requirements.txt"]

        )

        print("✅ Build dependencies installed")

        return True

    except subprocess.CalledProcessError as exc:

        print(f"❌ Failed to install build dependencies: {exc}")

        return False





def clean_build_dirs() -> bool:

    """Remove previous build artefacts for a clean run."""

    print("🧹 Cleaning build directories...")

    for dir_path in [BUILD_DIR, DIST_DIR]:

        if dir_path.exists():

            shutil.rmtree(dir_path)

            print(f"   Removed {dir_path}")



    if SPEC_FILE.exists():

        SPEC_FILE.unlink()

        print(f"   Removed {SPEC_FILE}")



    return True





def _apply_text_replacements(target: Path, replacements: list[tuple[str, str]]) -> bool:

    """Apply simple string replacements to a text file."""

    if not target.exists():

        return False



    text = target.read_text(encoding="utf-8")

    updated = False



    for old, new in replacements:

        if old in text:

            text = text.replace(old, new)

            updated = True



    if updated:

        target.write_text(text, encoding="utf-8")



    return updated





def enforce_shortcut_icon_scripts(root: Path) -> int:

    """

    Ensure helper scripts always point shortcuts to assets/application.ico.



    Returns the number of scripts updated.

    """

    updated = 0



    if _apply_text_replacements(

        root / "Create-Desktop-Shortcut.cmd",

        [(CREATE_SHORTCUT_ICON_OLD, CREATE_SHORTCUT_ICON_NEW)],

    ):

        updated += 1



    if _apply_text_replacements(

        root / "ultimate_cert_fix.cmd",

        [(ULTIMATE_SHORTCUT_ICON_OLD, ULTIMATE_SHORTCUT_ICON_NEW)],

    ):

        updated += 1



    if updated:

        rel_root = root if root == Path(".") else root.relative_to(REPO_ROOT)

        print(f"🎯 Updated {updated} shortcut script(s) in {rel_root}")



    return updated





def create_pyinstaller_spec() -> Path:

    """Create a PyInstaller spec file with pinned icon/version metadata."""

    icon_path = create_icon()

    version_file = create_version_file()



    icon_literal = "None"

    if icon_path is not None:

        try:

            icon_literal = f"'{Path(icon_path).as_posix()}'"

        except Exception:

            pass



    try:

        version_literal = f"'{Path(version_file).as_posix()}'"

    except Exception:

        version_literal = "None"



    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-



block_cipher = None



a = Analysis(

    ['{MAIN_SCRIPT}'],

    pathex=[],

    binaries=[],

    datas=[

        ('requirements.txt', '.'),

        ('launcher_requirements.txt', '.'),

        ('README.md', '.'),

    ],

    hiddenimports=[

        'PIL._tkinter_finder',

        'tkinter',

        'tkinter.ttk',

        'pystray._win32',

        'requests.packages.urllib3',

    ],

    hookspath=[],

    hooksconfig={{}},

    runtime_hooks=[],

    excludes=[],

    win_no_prefer_redirects=False,

    win_private_assemblies=False,

    cipher=block_cipher,

    noarchive=False,

)



pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)



exe = EXE(

    pyz,

    a.scripts,

    a.binaries,

    a.zipfiles,

    a.datas,

    [],

    name='{LAUNCHER_NAME}',

    debug=False,

    bootloader_ignore_signals=False,

    strip=False,

    upx=True,

    upx_exclude=[],

    runtime_tmpdir=None,

    console=False,

    disable_windowed_traceback=False,

    target_arch=None,

    codesign_identity=None,

    entitlements_file=None,

    icon={icon_literal},

    version={version_literal},

)

"""



    SPEC_FILE.write_text(spec_content, encoding="utf-8")

    print(f"✅ PyInstaller spec file created: {SPEC_FILE}")

    return SPEC_FILE





def build_executable() -> bool:

    """Build the launcher executable with PyInstaller."""

    if not MAIN_SCRIPT.exists():

        print(f"❌ Main script not found: {MAIN_SCRIPT}")

        return False



    spec_file = create_pyinstaller_spec()



    print("🔨 Building executable with PyInstaller...")

    print("    This may take several minutes...")



    try:

        cmd = [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)]

        result = subprocess.run(cmd, capture_output=True, text=True)



        if result.returncode != 0:

            print("❌ PyInstaller build failed")

            print("STDOUT:", result.stdout)

            print("STDERR:", result.stderr)

            return False



        exe_path = DIST_DIR / f"{LAUNCHER_NAME}.exe"

        if exe_path.exists():

            size_mb = exe_path.stat().st_size / (1024 * 1024)

            print(f"✅ Executable built successfully: {exe_path} ({size_mb:.1f} MB)")

            return True



        print("❌ Executable file not found after build")

        return False

    except Exception as exc:

        print(f"❌ Build failed: {exc}")

        return False





def create_installer_package() -> bool:

    """Create a lightweight installer package."""

    print("📦 Creating installer package...")



    package_dir = PACKAGE_DIR

    package_dir.mkdir(exist_ok=True)



    exe_path = DIST_DIR / f"{LAUNCHER_NAME}.exe"

    if INCLUDE_EXECUTABLE_IN_PACKAGE:

        if not exe_path.exists():

            print("❌ Executable not found, cannot create package")

            return False

        shutil.copy2(exe_path, package_dir / exe_path.name)

    else:

        if exe_path.exists():

            print("   Skipping executable copy; package will rely on ultimate_cert_fix.cmd entry point.")



    icon_path = create_icon()

    assets_dir = package_dir / "assets"

    assets_dir.mkdir(parents=True, exist_ok=True)

    if icon_path and icon_path.exists():

        shutil.copy2(icon_path, assets_dir / icon_path.name)



    for file_name in ["README.md", "requirements.txt", "launcher_requirements.txt"]:

        src = Path(file_name)

        if src.exists():

            shutil.copy2(src, package_dir / src.name)



    enforce_shortcut_icon_scripts(package_dir)



    install_instructions = f"""# Financial Command Center AI - Installation Instructions



## Quick Start

1. Run `{LAUNCHER_NAME}.exe`

2. Follow the setup wizard

3. The application will automatically:

   - Install Python dependencies

   - Configure SSL certificates

   - Launch the web interface

   - Add system tray integration



## System Requirements

- Windows 10/11, macOS 10.14+, or Linux

- 200 MB free disk space

- Internet connection for dependency installation



## Troubleshooting

- If the launcher fails to start, check `launcher.log`

- For permission errors, try running as administrator

- For network issues, check your firewall settings



## Uninstalling

1. Right-click the system tray icon and select "Exit"

2. Delete the installation folder

3. Remove the Python virtual environment (`.venv` folder)

"""

    (package_dir / "INSTALL.md").write_text(install_instructions, encoding="utf-8")



    print(f"✅ Installer package created in: {package_dir}")

    return True





def create_installer_package_full() -> bool:

    """Create an installer package that includes runtime sources and assets."""

    print("📦 Creating full installer package (with app sources)...")



    enforce_shortcut_icon_scripts(REPO_ROOT)



    package_dir = PACKAGE_DIR

    if package_dir.exists():

        shutil.rmtree(package_dir)

    package_dir.mkdir(parents=True, exist_ok=True)



    exe_path = DIST_DIR / f"{LAUNCHER_NAME}.exe"

    if INCLUDE_EXECUTABLE_IN_PACKAGE:

        if not exe_path.exists():

            print("❌ Executable not found, cannot create package")

            return False

        shutil.copy2(exe_path, package_dir / exe_path.name)

    else:

        if exe_path.exists():

            print("   Skipping executable copy; package will rely on ultimate_cert_fix.cmd entry point.")



    icon_path = create_icon()

    assets_dir = package_dir / "assets"

    assets_dir.mkdir(parents=True, exist_ok=True)

    if icon_path and icon_path.exists():

        shutil.copy2(icon_path, assets_dir / icon_path.name)

    favicon = Path("assets/favicon.ico")

    if favicon.exists():

        shutil.copy2(favicon, assets_dir / favicon.name)



    default_ignores = [

        "__pycache__",

        "*.pyc",

        "*.pyo",

        "*.pyd",

        "*.log",

        "*.tmp",

        "*.bak",

        ".DS_Store",

        "Thumbs.db",

        "issued_pilot_licenses.csv",

    ]

    missing_assets: list[str] = []



    def _copy_file(src: Path, dst: Path) -> None:

        if not src.exists():

            missing_assets.append(str(src))

            return

        dst.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(src, dst)
        if dst.suffix in {".sh", ".command", ".desktop"}:
            try:
                dst.chmod(dst.stat().st_mode | 0o111)
            except Exception:
                pass



    def _copy_tree(src: Path, dst: Path, extra_ignores: Optional[List[str]] = None) -> None:

        if not src.exists():

            missing_assets.append(str(src))

            return

        if dst.exists():

            shutil.rmtree(dst)

        patterns = list(default_ignores)

        if extra_ignores:

            patterns.extend(extra_ignores)

        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*patterns))



    runtime_files = [

        "app.py",

        "app_with_setup_wizard.py",

        "automation_config_manager.py",

        "automation_mcp.py",

        "automation_mcp_warp.py",

        "cert_manager.py",

        "chatgpt_integration.py",

        "claude_integration.py",

        "compliance_mcp.py",

        "compliance_mcp_warp.py",

        "config.py",

        "custom_fcc_assistant.py",

        "demo_mode.py",

        "fcc_assistant_core.py",

        "fcc_assistant_integration.py",

        "fcc_llama32_integration.py",

        "financial_export.py",

        "financial_launcher.py",

        "mcp_endpoints.py",

        "mcp_server.py",

        "mcp_server_warp.py",

        "plaid_client_store.py",

        "plaid_demo_data.py",

        "plaid_mcp.py",

        "plaid_mcp_warp.py",

        "server_modes.py",

        "session_config.py",

        "setup_api_routes.py",

        "setup_wizard.py",

        "stripe_mcp.py",

        "stripe_mcp_warp.py",

        "license_manager.py",

        "utils.py",

        "warp_integration.py",

        "webhook_server.py",

        "xero_api_calls.py",

        "xero_client.py",

        "xero_demo_data.py",

        "xero_mcp.py",

        "xero_mcp_warp.py",

        "xero_oauth.py",

        "xero_token_exchange.py",

        "automation_config.json",

        "compliance_config.json",

        "compliance_rules.json",

        "plaid_store_warp.json",

        "requirements.txt",

        "requirements_setup_wizard.txt",

        "launcher_requirements.txt",

    ]

    for file_name in runtime_files:

        _copy_file(Path(file_name), package_dir / Path(file_name).name)



    folder_manifest = [

        ("auth", ["api_keys.json", "rate_limits.json", "encryption.key"]),

        ("templates", []),

        ("static", []),

        ("ui", []),

        ("tools", []),

        ("MCPServers", ["test_*"]),

        ("fcc-openai-adapter", ["tests", "demos", "*.ipynb"]),

        ("fcc-local-llm-adapter", ["tests", "*.ipynb"]),

        ("bootstrap", []),

    ]

    for folder_name, ignore_patterns in folder_manifest:

        _copy_tree(Path(folder_name), package_dir / folder_name, ignore_patterns)



    for runtime_dir in [

        "automation",

        "alerts",

        "audit",

        "audit_warp",

        "exports",

        "exports_warp",

        "reports",

        "reports_warp",

        "certs",

        "secure_config",

        "tokens",

    ]:

        (package_dir / runtime_dir).mkdir(parents=True, exist_ok=True)



    doc_sources = {

        Path("README.md"): package_dir / "README.md",

        Path("docs/LAUNCHER_README.md"): package_dir / "LAUNCHER_README.md",

    }

    for src, dest in doc_sources.items():

        _copy_file(src, dest)



    for helper in [

        "mkcert.exe",

        "Create-Desktop-Shortcut.cmd",

        "create_shortcut.ps1",

        "create-quick-start-shortcut.ps1",

        "ultimate_cert_fix.cmd",

        "bootstrap/run_windows.cmd",

        "bootstrap/run_unix.sh",

        "bootstrap/bootstrap-install.cmd",

        "bootstrap/bootstrap-install.ps1",

        "bootstrap/bootstrap-install.sh",
        "bootstrap/mac-launch.command",
        "bootstrap/financial-command-center.desktop",

    ]:

        _copy_file(Path(helper), package_dir / Path(helper).name)



    enforce_shortcut_icon_scripts(package_dir)



    install_instructions = """# Financial Command Center AI - Installation Guide



## Quick Steps

1. Extract this archive and open the `FCC` folder.

2. Run `ultimate_cert_fix.cmd` (double-click on Windows).

3. Follow the prompts to verify your license, install Python/dependencies, and generate certificates.

4. When your browser opens to `https://localhost:8443/setup`, complete the setup wizard with your own API credentials.



## Requirements

- Windows 10/11, macOS 11+, or Ubuntu 20.04+

- 200 MB free disk space

- Internet access for dependency installation and license verification



## Helpful Scripts

- `ultimate_cert_fix.cmd`: primary entry point for licensing, dependency installation, and launch.

- `LAUNCH.bat`: optional helper that launches `ultimate_cert_fix.cmd`.

- `Create-Desktop-Shortcut.cmd`: optional script to pin the launcher to the desktop.



## Support

- Re-run `ultimate_cert_fix.cmd` if you need to repair the installation.

- Logs are written to `launcher.log`.

- Contact support@financial-command-center.com for assistance."""

    (package_dir / "INSTALL.md").write_text(install_instructions, encoding="utf-8")



    quick_start = """Financial Command Center AI - Quick Start

==================================================

1. Double-click `ultimate_cert_fix.cmd`.

2. Enter your license key when prompted.

3. Allow the script to install Python/dependencies and generate certificates.

4. When the browser opens, complete the setup wizard at https://localhost:8443/setup.

5. After setup, bookmark the dashboard for daily use."""

    (package_dir / "QUICK_START.txt").write_text(quick_start, encoding="utf-8")



    launch_batch = """@echo off

REM Simplified helper to start the Financial Command Center setup script

setlocal

cd /d "%~dp0"

start "" "ultimate_cert_fix.cmd"

"""

    (package_dir / "LAUNCH.bat").write_text(launch_batch, encoding="utf-8")



    sanitized_json = {

        "plaid_store.json": {"items": {}, "account_mappings": {}},

        "plaid_store_warp.json": {"items": {}, "account_mappings": {}},

        "automation_store.json": {"payment_reminders": {}, "recurring_invoices": []},

        "compliance_blacklist.json": {"merchants": []},

        "compliance_blacklist_warp.json": {"merchants": []},

        "spending_limits.json": {

            "daily_limit": None,

            "monthly_limit": None,

            "merchant_limits": {},

            "category_limits": {},

            "created_at": None,

            "last_updated": None,

        },

        "spending_limits_warp.json": {

            "daily_limit": None,

            "monthly_limit": None,

            "merchant_limits": {},

            "category_limits": {},

            "created_at": None,

            "last_updated": None,

        },

        "xero_tenant.json": {"tenant_id": ""},

        "xero_tenant_warp.json": {"tenant_id": ""},

        "auth/api_keys.json": {},

        "auth/rate_limits.json": {},

        "secure_config/mcp_harness_overrides.json": {},

        "secure_config/metadata.json": {

            "last_updated": datetime.now(timezone.utc).isoformat(),

            "services_configured": [],

            "config_version": "1.0",

        },

        "secure_config/app_mode.json": {

            "mode": "demo",

            "updated_at": datetime.now(timezone.utc).isoformat(),

        },

        "certs/cert_config.json": {

            "cert_file": "certs/server.crt",

            "key_file": "certs/server.key",

            "ca_cert": "certs/ca.crt",

            "ca_key": "certs/ca.key",

            "validity_days": 365,

            "last_generated": None,

            "hostnames": ["localhost", "127.0.0.1", "::1"],

            "organization": "Financial Command Center AI",

            "country": "US",

            "use_mkcert": True,

            "trust_installed": False,

        },

    }

    for rel_path, data in sanitized_json.items():

        target = package_dir / rel_path

        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")



    secure_readme = """Secure Configuration

====================

This directory is created during installation to store encrypted credentials.

- `app_mode.json` starts in demo mode; the setup wizard updates it after activation.

- `metadata.json` is regenerated when services are connected.

- `config.enc` and `master.key` will be created automatically by the setup wizard.

Never commit or redistribute the contents of this folder once real credentials exist.

"""

    (package_dir / "secure_config" / "README.md").write_text(secure_readme, encoding="utf-8")



    certs_readme = """TLS Certificates

================

Run `ultimate_cert_fix.cmd` (Windows) or `python cert_manager.py --generate` to create trusted certificates.

The installer ships without private keys; new keys are generated locally for each client."""

    (package_dir / "certs" / "README.md").write_text(certs_readme, encoding="utf-8")



    venv_in_pkg = package_dir / ".venv"

    if venv_in_pkg.exists():

        shutil.rmtree(venv_in_pkg, ignore_errors=True)



    for artifact in [".fcc_installed", "launcher.log"]:

        path = package_dir / artifact

        if path.exists():

            path.unlink(missing_ok=True)



    if missing_assets:

        print("⚠️  The following expected assets were not found and were skipped:")

        for asset in sorted(set(missing_assets)):

            print(f"   - {asset}")



    print(f"✅ Full installer package created at: {package_dir}")

    return True





def create_release_archives(package_dir: Path) -> bool:

    """Create distributable archives respecting the 50 MB Supabase limit."""

    release_dir = RELEASE_DIR

    release_dir.mkdir(parents=True, exist_ok=True)



    archive_base = release_dir / PACKAGE_DIR_NAME

    archive_path_str = shutil.make_archive(str(archive_base), "zip", root_dir=package_dir)

    archive_path = Path(archive_path_str)

    size_bytes = archive_path.stat().st_size

    size_mb = size_bytes / (1024 * 1024)

    rel_archive = archive_path.relative_to(REPO_ROOT)

    print(f"\u2705 Release archive created: {rel_archive} ({size_mb:.1f} MB)")



    limit_bytes = UPLOAD_SPLIT_LIMIT_MB * 1024 * 1024

    if size_bytes <= limit_bytes:

        return True



    print(f"\u26a0\uFE0F Archive exceeds {UPLOAD_SPLIT_LIMIT_MB} MB; splitting into {UPLOAD_SPLIT_LIMIT_MB} MB parts...")

    with archive_path.open("rb") as source:

        part = 1

        while True:

            chunk = source.read(limit_bytes)

            if not chunk:

                break

            part_path = archive_path.with_suffix(archive_path.suffix + f".part{part:02d}")

            with part_path.open("wb") as dest:

                dest.write(chunk)

            part_mb = len(chunk) / (1024 * 1024)

            print(f"   -> {part_path.relative_to(REPO_ROOT)} ({part_mb:.1f} MB)")

            part += 1



    return True





def main() -> int:

    """Main build process."""

    print("Building Financial Command Center AI Launcher")

    print("=" * 60)



    if not MAIN_SCRIPT.exists():

        print(f"❌ Main script not found: {MAIN_SCRIPT}")

        print("Please run this script from the project root directory.")

        return 1



    create_icon()  # Ensure icon exists before starting

    enforce_shortcut_icon_scripts(REPO_ROOT)



    build_steps = [

        ("Building admin UI bundle", build_admin_ui_bundle),

        ("Installing build dependencies", install_build_dependencies),

        ("Cleaning build directories", clean_build_dirs),

        ("Building executable", build_executable),

        ("Creating installer package", create_installer_package_full),

        ("Building release archives", lambda: create_release_archives(PACKAGE_DIR)),

    ]



    for step_name, step_func in build_steps:

        print(f"\n🔄 {step_name}...")

        if not step_func():

            print(f"❌ Failed: {step_name}")

            return 1



    print("\n🎉 Build completed successfully!")

    print(f"📦 Executable: dist/{LAUNCHER_NAME}.exe")

    print(f"📁 Installer package: {PACKAGE_DIR_NAME}/")

    print("\n🚀 Ready for distribution!")



    return 0





if __name__ == "__main__":

    sys.exit(main())

