#!/usr/bin/env python3
"""
Financial Command Center AI - Launcher
Handles proper startup and cleanup for the application
"""

import os
import sys
import subprocess
import tempfile
import shutil
import atexit
from pathlib import Path

# Configuration
APP_NAME = "Financial Command Center AI"
TEMP_CLEANUP_ENABLED = True

def cleanup_temp_data():
    """Clean up temporary data on exit"""
    if not TEMP_CLEANUP_ENABLED:
        return
    
    try:
        # Clean up any temporary files created during this session
        temp_dir = Path(tempfile.gettempdir())
        app_temp_pattern = f"fcc_*"
        
        # Only clean up our own temp files
        for temp_file in temp_dir.glob(app_temp_pattern):
            try:
                if temp_file.is_file():
                    temp_file.unlink()
                elif temp_file.is_dir():
                    shutil.rmtree(temp_file)
            except (PermissionError, FileNotFoundError):
                # Ignore cleanup failures - they're not critical
                pass
                
    except Exception:
        # Silent cleanup failure - not critical
        pass

def find_main_app():
    """Find the main application file to run"""
    script_dir = Path(__file__).parent
    
    # Priority order: setup wizard, regular app
    candidates = [
        script_dir / "app_with_setup_wizard.py",
        script_dir / "app.py"
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    raise FileNotFoundError(f"No application file found in {script_dir}")

def main():
    """Main launcher function"""
    try:
        # Register cleanup function
        atexit.register(cleanup_temp_data)
        
        # Find and run the main application
        app_file = find_main_app()
        
        print(f"Starting {APP_NAME}...")
        print(f"Using: {app_file.name}")
        
        # Run the application
        sys.exit(subprocess.call([sys.executable, str(app_file)]))
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure the application files are present in the installation directory.")
        input("Press Enter to exit...")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print(f"\\n{APP_NAME} stopped by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Please check the installation and try again.")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()

