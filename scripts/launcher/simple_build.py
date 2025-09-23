#!/usr/bin/env python3
"""
Simple Build Script for Financial Command Center AI Launcher
===========================================================

This script builds the executable without Unicode characters for Windows compatibility.
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

def install_dependencies():
    """Install PyInstaller and required dependencies"""
    print("Installing build dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", 
                              "pyinstaller", "pillow", "pystray", "requests", "psutil"])
        print("Build dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False

def clean_build():
    """Clean previous build artifacts"""
    print("Cleaning build directories...")
    dirs_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = ["financial_launcher.spec"]
    
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Removed {dir_name}")
    
    for file_name in files_to_clean:
        file_path = Path(file_name)
        if file_path.exists():
            file_path.unlink()
            print(f"Removed {file_name}")
    return True

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")
    
    # Basic PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "Financial-Command-Center-Launcher",
        "financial_launcher.py"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            exe_path = Path("dist") / "Financial-Command-Center-Launcher.exe"
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"Executable built successfully: {exe_path}")
                print(f"Size: {size_mb:.1f} MB")
                return True
            else:
                print("Executable not found after build")
                return False
        else:
            print("Build failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
    except Exception as e:
        print(f"Build failed with exception: {e}")
        return False

def create_package():
    """Create installer package"""
    print("Creating installer package...")
    
    package_dir = Path("launcher_package")
    package_dir.mkdir(exist_ok=True)
    
    # Copy executable
    exe_source = Path("dist") / "Financial-Command-Center-Launcher.exe"
    if exe_source.exists():
        shutil.copy2(exe_source, package_dir / "Financial-Command-Center-Launcher.exe")
    
    # Copy documentation
    docs = ["README.md", "LAUNCHER_README.md", "requirements.txt"]
    for doc in docs:
        if Path(doc).exists():
            shutil.copy2(doc, package_dir / doc)
    
    # Create simple instructions
    instructions = """Financial Command Center AI Launcher

Quick Start:
1. Run Financial-Command-Center-Launcher.exe
2. Follow the setup wizard
3. Application will start automatically

For support, check LAUNCHER_README.md or visit the GitHub repository.
"""
    
    with open(package_dir / "INSTRUCTIONS.txt", "w") as f:
        f.write(instructions)
    
    print(f"Package created in: {package_dir}")
    return True

def main():
    """Main build process"""
    print("Building Financial Command Center AI Launcher")
    print("=" * 50)
    
    if not Path("financial_launcher.py").exists():
        print("Error: financial_launcher.py not found")
        return 1
    
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Cleaning build", clean_build),
        ("Building executable", build_executable),
        ("Creating package", create_package)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"Failed: {step_name}")
            return 1
    
    print("\nBuild completed successfully!")
    print("Executable: dist/Financial-Command-Center-Launcher.exe")
    print("Package: launcher_package/")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
