#!/usr/bin/env python3
"""
Build Script for Financial Command Center AI Launcher
====================================================

This script creates a standalone executable for the Financial Command Center AI
launcher using PyInstaller.

Usage:
    python build_launcher.py
"""

from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Ensure UTF-8 stdout on Windows consoles to avoid UnicodeEncodeError when printing emojis
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Build configuration
BUILD_DIR = Path("build")
DIST_DIR = Path("dist")
SPEC_FILE = Path("financial_launcher.spec")
MAIN_SCRIPT = Path("financial_launcher.py")
ICON_FILE = Path("assets/launcher_icon.ico")  # We'll create this
LAUNCHER_NAME = "Financial-Command-Center-Launcher"

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

def create_icon():
    """Create a simple launcher icon if it doesn't exist"""
    icon_dir = Path("assets")
    icon_dir.mkdir(exist_ok=True)
    
    if not ICON_FILE.exists():
        print("📎 Creating launcher icon...")
        try:
            from PIL import Image, ImageDraw
            
            # Create a 256x256 icon
            size = 256
            image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Draw a financial symbol background
            margin = 20
            draw.ellipse([margin, margin, size-margin, size-margin], 
                        fill=(102, 126, 234, 255), outline=(90, 111, 216, 255), width=4)
            
            # Draw dollar sign
            center_x, center_y = size // 2, size // 2
            font_size = size // 4
            
            # Simple dollar sign representation
            draw.text((center_x - font_size//3, center_y - font_size//2), 
                     '$', fill='white', anchor='mm')
            
            # Save as ICO
            image.save(ICON_FILE, 'ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
            print(f"✅ Icon created: {ICON_FILE}")
            
        except ImportError:
            print("⚠️  Pillow not available, skipping icon creation")
            return None
        except Exception as e:
            print(f"⚠️  Failed to create icon: {e}")
            return None
    
    return ICON_FILE if ICON_FILE.exists() else None

def create_version_file():
    """Create version file for Windows executable"""
    version_file = Path("version.txt")
    with open(version_file, 'w') as f:
        f.write(VERSION_INFO)
    return version_file

def install_build_dependencies():
    """Install PyInstaller and other build dependencies"""
    print("📦 Installing build dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "launcher_requirements.txt"])
        print("✅ Build dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install build dependencies: {e}")
        return False

def clean_build_dirs():
    """Clean previous build artifacts"""
    print("🧹 Cleaning build directories...")
    for dir_path in [BUILD_DIR, DIST_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"   Removed {dir_path}")
    
    if SPEC_FILE.exists():
        SPEC_FILE.unlink()
        print(f"   Removed {SPEC_FILE}")

    return True

def create_pyinstaller_spec():
    """Create PyInstaller spec file for better control"""
    icon_path = create_icon()
    version_file = create_version_file()

    # Embed literal values in the spec (avoid undefined names in spec runtime)
    try:
        icon_literal = f"'{Path(icon_path).as_posix()}'" if icon_path else "None"
    except Exception:
        icon_literal = "None"
    try:
        # Only used on Windows; but safe to embed absolute/relative path
        version_literal = f"'{Path(version_file).as_posix()}'"
    except Exception:
        version_literal = "None"
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

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
    console=False,  # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={icon_literal},
    version={version_literal},
)
'''
    
    with open(SPEC_FILE, 'w') as f:
        f.write(spec_content)
    
    print(f"✅ PyInstaller spec file created: {SPEC_FILE}")
    return SPEC_FILE

def build_executable():
    """Build the executable using PyInstaller"""
    if not MAIN_SCRIPT.exists():
        print(f"❌ Main script not found: {MAIN_SCRIPT}")
        return False
    
    spec_file = create_pyinstaller_spec()
    
    print("🔨 Building executable with PyInstaller...")
    print("This may take several minutes...")
    
    try:
        # Run PyInstaller with the spec file
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            exe_path = DIST_DIR / f"{LAUNCHER_NAME}.exe"
            if exe_path.exists():
                print(f"✅ Executable built successfully: {exe_path}")
                print(f"📦 Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
                return True
            else:
                print("❌ Executable file not found after build")
                return False
        else:
            print("❌ PyInstaller build failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Build failed: {e}")
        return False

def create_installer_package():
    """Create a complete installer package"""
    print("📦 Creating installer package...")
    
    package_dir = Path("installer_package")
    package_dir.mkdir(exist_ok=True)
    
    exe_path = DIST_DIR / f"{LAUNCHER_NAME}.exe"
    if not exe_path.exists():
        print("❌ Executable not found, cannot create package")
        return False
    
    # Copy executable
    shutil.copy2(exe_path, package_dir / f"{LAUNCHER_NAME}.exe")
    
    # Create installer files
    files_to_include = [
        "README.md",
        "requirements.txt",
        "launcher_requirements.txt",
    ]
    
    for file_name in files_to_include:
        if Path(file_name).exists():
            shutil.copy2(file_name, package_dir / file_name)
    
    # Create install instructions
    install_instructions = f"""
# Financial Command Center AI - Installation Instructions

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

## Support
- Documentation: https://github.com/YourOrg/Financial-Command-Center-AI
- Issues: https://github.com/YourOrg/Financial-Command-Center-AI/issues
- Email: support@financial-command-center.com

## Uninstalling
1. Right-click the system tray icon and select "Exit"
2. Delete the installation folder
3. Remove the Python virtual environment (`.venv` folder)
"""
    
    with open(package_dir / "INSTALL.md", 'w') as f:
        f.write(install_instructions)
    
    # Create Windows batch launcher (optional)
    if sys.platform == "win32":
        batch_content = f'''@echo off
echo Starting Financial Command Center AI...
"{LAUNCHER_NAME}.exe"
if errorlevel 1 pause
'''
        with open(package_dir / "Launch.bat", 'w') as f:
            f.write(batch_content)
    
    print(f"✅ Installer package created in: {package_dir}")
    print("\nPackage contents:")
    for item in package_dir.iterdir():
        size = item.stat().st_size / 1024 if item.is_file() else 0
        print(f"  📄 {item.name} ({size:.1f} KB)")
    
    return True

def create_installer_package_full():
    """Create installer package that includes the runnable app sources.
    This ensures the launcher can find app.py/app_with_setup_wizard.py after install.
    """
    print("Creating full installer package (with app sources)...")

    package_dir = Path("installer_package")
    package_dir.mkdir(exist_ok=True)

    exe_path = DIST_DIR / f"{LAUNCHER_NAME}.exe"
    if not exe_path.exists():
        print("Executable not found, cannot create package")
        return False

    # Copy executable
    shutil.copy2(exe_path, package_dir / f"{LAUNCHER_NAME}.exe")

    # Helpers
    def _copy_tree(src: Path, dst: Path):
        if not src.exists():
            return
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    # Top-level modules the app imports
    app_files = [
        "app.py",
        "app_with_setup_wizard.py",
        "setup_wizard.py",
        "demo_mode.py",
        "cert_manager.py",
        "server_modes.py",
        "utils.py",
        "config.py",
        "xero_client.py",
        "xero_oauth.py",
        "xero_api_calls.py",
        "xero_demo_data.py",
        "plaid_demo_data.py",
        "plaid_mcp.py",
        "stripe_mcp.py",
        "webhook_server.py",
    ]
    for f in app_files:
        p = Path(f)
        if p.exists():
            shutil.copy2(p, package_dir / p.name)

    # Required folders
    for d in ["auth", "templates", "assets", "secure_config"]:
        src = Path(d)
        if src.exists():
            _copy_tree(src, package_dir / d)

    # Carry over helpful files
    for fname in [
        "README.md",
        "requirements.txt",
        "launcher_requirements.txt",
        "LAUNCHER_README.md",
        "QUICK_START.txt",
        "ultimate_cert_fix.cmd",
    ]:
        fp = Path(fname)
        if fp.exists():
            shutil.copy2(fp, package_dir / fp.name)

    # Ensure no virtualenv is bundled (keep package lean)
    venv_in_pkg = package_dir / ".venv"
    if venv_in_pkg.exists():
        import shutil as _sh
        _sh.rmtree(venv_in_pkg, ignore_errors=True)

    print(f"Full installer package created at: {package_dir}")
    return True

def main():
    """Main build process"""
    print("Building Financial Command Center AI Launcher")
    print("=" * 60)
    
    # Check if main script exists
    if not MAIN_SCRIPT.exists():
        print(f"❌ Main script not found: {MAIN_SCRIPT}")
        print("Please run this script from the project root directory.")
        return 1
    
    # Build process
    build_steps = [
        ("Installing build dependencies", install_build_dependencies),
        ("Cleaning build directories", clean_build_dirs),
        ("Building executable", build_executable),
        ("Creating installer package", create_installer_package_full),
    ]
    
    for step_name, step_func in build_steps:
        print(f"\n🔄 {step_name}...")
        if not step_func():
            print(f"❌ Failed: {step_name}")
            return 1
    
    print("\n🎉 Build completed successfully!")
    print(f"📦 Executable: dist/{LAUNCHER_NAME}.exe")
    print("📁 Installer package: installer_package/")
    print("\n🚀 Ready for distribution!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
