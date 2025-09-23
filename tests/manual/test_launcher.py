#!/usr/bin/env python3
"""
Test Script for Financial Command Center AI Launcher
===================================================

This script tests various components of the launcher to ensure
everything works correctly before building the executable.

Usage:
    python test_launcher.py
"""

import sys
import subprocess
import importlib
import unittest
from pathlib import Path

class LauncherTests(unittest.TestCase):
    """Test cases for the launcher components"""
    
    def test_python_version(self):
        """Test if Python version is compatible"""
        version = sys.version_info
        self.assertGreaterEqual(version.major, 3, "Python 3.x required")
        self.assertGreaterEqual(version.minor, 8, "Python 3.8+ required")
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    
    def test_main_script_exists(self):
        """Test if main launcher script exists"""
        script_path = Path("financial_launcher.py")
        self.assertTrue(script_path.exists(), "financial_launcher.py not found")
        print("✅ Main launcher script exists")
    
    def test_requirements_files_exist(self):
        """Test if requirements files exist"""
        files = ["requirements.txt", "launcher_requirements.txt"]
        for file_name in files:
            file_path = Path(file_name)
            self.assertTrue(file_path.exists(), f"{file_name} not found")
        print("✅ Requirements files exist")
    
    def test_core_imports(self):
        """Test if core Python modules can be imported"""
        core_modules = [
            "tkinter",
            "threading", 
            "subprocess",
            "webbrowser",
            "pathlib",
            "json",
            "logging"
        ]
        
        for module_name in core_modules:
            try:
                importlib.import_module(module_name)
                print(f"✅ {module_name} import successful")
            except ImportError as e:
                self.fail(f"Failed to import {module_name}: {e}")
    
    def test_optional_imports(self):
        """Test optional imports with graceful fallback"""
        optional_modules = {
            "pystray": "System tray functionality",
            "PIL": "Icon generation",
            "requests": "HTTP requests",
        }
        
        for module_name, description in optional_modules.items():
            try:
                importlib.import_module(module_name)
                print(f"✅ {module_name} available ({description})")
            except ImportError:
                print(f"⚠️  {module_name} not available ({description}) - will fallback gracefully")
    
    def test_launcher_syntax(self):
        """Test if launcher script has valid syntax"""
        try:
            with open("financial_launcher.py", 'r') as f:
                code = f.read()
            compile(code, "financial_launcher.py", "exec")
            print("✅ Launcher script syntax is valid")
        except SyntaxError as e:
            self.fail(f"Syntax error in launcher script: {e}")
    
    def test_build_script_exists(self):
        """Test if build script exists"""
        build_script = Path("scripts/launcher/build_launcher.py")
        self.assertTrue(build_script.exists(), "scripts/launcher/build_launcher.py not found")
        print("✅ Build script exists")

def test_system_compatibility():
    """Test system compatibility"""
    print("\n🔍 System Compatibility Check")
    print("-" * 40)
    
    # Test platform
    import platform
    system = platform.system()
    print(f"Platform: {system} {platform.release()}")
    
    # Test available disk space
    import shutil
    free_space = shutil.disk_usage(".").free / (1024**3)  # GB
    print(f"Available disk space: {free_space:.1f} GB")
    
    if free_space < 1.0:
        print("⚠️  Low disk space - may affect build process")
    else:
        print("✅ Sufficient disk space")
    
    # Test network connectivity (optional)
    try:
        import urllib.request
        urllib.request.urlopen('https://pypi.org', timeout=5)
        print("✅ Network connectivity available")
    except:
        print("⚠️  Network connectivity issues - may affect dependency installation")

def test_launcher_functionality():
    """Test basic launcher functionality without GUI"""
    print("\n🧪 Launcher Functionality Test")
    print("-" * 40)
    
    try:
        # Import launcher classes without running GUI
        sys.path.insert(0, ".")
        
        # Test importing main classes
        from financial_launcher import (
            LauncherLogger, 
            DependencyManager,
            ServerManager,
            ErrorHandler
        )
        
        print("✅ Main classes import successfully")
        
        # Test logger
        logger = LauncherLogger()
        logger.info("Test log message")
        print("✅ Logger functionality works")
        
        # Test dependency manager
        dep_manager = DependencyManager(logger)
        has_python = dep_manager.check_python_version()
        print(f"✅ Dependency manager works (Python check: {has_python})")
        
        print("✅ Basic launcher functionality test passed")
        
    except Exception as e:
        print(f"❌ Launcher functionality test failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Financial Command Center AI Launcher - Test Suite")
    print("=" * 60)
    
    # Run unit tests
    print("\n📋 Unit Tests")
    print("-" * 40)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(LauncherTests)
    runner = unittest.TextTestRunner(verbosity=0, stream=open('/dev/null', 'w') if hasattr(sys, 'platform') and sys.platform != 'win32' else open('nul', 'w'))
    result = runner.run(suite)
    
    # Manual verbose output
    test_cases = [
        LauncherTests().test_python_version,
        LauncherTests().test_main_script_exists,
        LauncherTests().test_requirements_files_exist,
        LauncherTests().test_core_imports,
        LauncherTests().test_optional_imports,
        LauncherTests().test_launcher_syntax,
        LauncherTests().test_build_script_exists,
    ]
    
    failed_tests = []
    for test_case in test_cases:
        try:
            test_case()
        except Exception as e:
            failed_tests.append((test_case.__name__, str(e)))
    
    # Run additional tests
    test_system_compatibility()
    
    functionality_ok = test_launcher_functionality()
    
    # Summary
    print(f"\n📊 Test Summary")
    print("-" * 40)
    
    if failed_tests:
        print(f"❌ {len(failed_tests)} unit tests failed:")
        for test_name, error in failed_tests:
            print(f"   • {test_name}: {error}")
    else:
        print("✅ All unit tests passed")
    
    if functionality_ok:
        print("✅ Functionality tests passed")
    else:
        print("❌ Functionality tests failed")
    
    overall_success = len(failed_tests) == 0 and functionality_ok
    
    if overall_success:
        print("\n🎉 All tests passed! Ready to build executable.")
        print("Run: python scripts/launcher/build_launcher.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before building.")
        return 1

if __name__ == "__main__":
    sys.exit(main())