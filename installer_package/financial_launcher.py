#!/usr/bin/env python3
"""
Financial Command Center AI - One-Click Launcher
=================================================

Single executable that handles:
- Automatic dependency installation
- Web browser auto-launch to setup wizard
- System tray integration for easy access
- Client-friendly error handling and support instructions
- Branded installer experience

Usage:
    python financial_launcher.py
    or create executable: pyinstaller --onefile financial_launcher.py
"""

import os
import sys
import subprocess
import webbrowser
import threading
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tkinter as tk
from tkinter import messagebox, ttk
import logging

# System tray imports (fallback gracefully)
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    SYSTEM_TRAY_AVAILABLE = True
except ImportError:
    SYSTEM_TRAY_AVAILABLE = False

# Version and branding
LAUNCHER_VERSION = "1.0.1"
APP_NAME = "Financial Command Center AI"
COMPANY_NAME = "Financial Command Center"
SUPPORT_EMAIL = "khansayeem03@gmail.com"
SUPPORT_URL = "https://github.com/KhanSayeem/Financial-Command-Center-AI"

class LauncherLogger:
    """Centralized logging for the launcher"""
    
    def __init__(self):
        # Choose a user-writable log directory (avoid Program Files)
        def _log_dir() -> Path:
            try:
                if sys.platform == 'win32':
                    base = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA') or os.path.expanduser('~')
                    p = Path(base) / 'Financial Command Center' / 'Logs'
                else:
                    p = Path.home() / '.local' / 'share' / 'financial-command-center' / 'logs'
                p.mkdir(parents=True, exist_ok=True)
                return p
            except Exception:
                return Path.cwd()

        self.log_file = _log_dir() / 'launcher.log'

        # Ensure stdout can handle unicode; fall back gracefully
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

        handlers = [logging.StreamHandler(sys.stdout)]
        try:
            handlers.insert(0, logging.FileHandler(self.log_file, encoding='utf-8'))
        except Exception:
            # If file handler fails (permissions), continue with stdout only
            pass

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers,
        )
        self.logger = logging.getLogger(__name__)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)

class DependencyManager:
    """Handles automatic dependency installation"""
    
    def __init__(self, logger: LauncherLogger):
        self.logger = logger
        self.requirements_file = Path("requirements.txt")
        # Create venv in a user‑writable location (avoids Program Files permission issues)
        def _venv_dir() -> Path:
            try:
                if sys.platform == 'win32':
                    base = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA') or os.path.expanduser('~')
                    p = Path(base) / 'Financial Command Center' / 'Python' / '.venv'
                else:
                    p = Path.home() / '.local' / 'share' / 'financial-command-center' / 'venv'
                p.parent.mkdir(parents=True, exist_ok=True)
                return p
            except Exception:
                return Path.cwd() / '.venv'
        self.venv_path = _venv_dir()
        self.python_executable = self._find_python()
    
    def _find_python(self) -> str:
        """Find the best Python executable"""
        candidates = ["python", "python3", "py"]
        for candidate in candidates:
            try:
                result = subprocess.run([candidate, "--version"], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and "Python 3" in result.stdout:
                    return candidate
            except FileNotFoundError:
                continue
        raise RuntimeError("Python 3.x not found in PATH")
    
    def check_python_version(self) -> bool:
        """Check if Python version is compatible"""
        try:
            result = subprocess.run([self.python_executable, "-c", 
                                   "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                major, minor = map(int, version.split('.'))
                if major >= 3 and minor >= 8:
                    self.logger.info(f"Python {version} is compatible")
                    return True
                else:
                    self.logger.error(f"Python {version} is too old (need 3.8+)")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to check Python version: {e}")
            return False
    
    def create_virtual_environment(self) -> bool:
        """Create virtual environment if it doesn't exist"""
        if self.venv_path.exists():
            self.logger.info("Virtual environment already exists")
            return True
        
        try:
            self.logger.info("Creating virtual environment...")
            subprocess.run([self.python_executable, "-m", "venv", str(self.venv_path)], 
                          check=True)
            self.logger.info("Virtual environment created")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create virtual environment: {e}")
            return False
    
    def get_venv_python(self) -> str:
        """Get Python executable from virtual environment"""
        if sys.platform == "win32":
            return str(self.venv_path / "Scripts" / "python.exe")
        else:
            return str(self.venv_path / "bin" / "python")
    
    def install_dependencies(self) -> bool:
        """Install all required dependencies with resilience and clear logs."""
        if not self.requirements_file.exists():
            self.logger.error(f"Requirements file not found: {self.requirements_file}")
            return False

        venv_python = self.get_venv_python()
        self.logger.info("Installing dependencies...")

        def run(cmd):
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                return True, result.stdout
            except subprocess.CalledProcessError as e:
                out = (e.stdout or "") + "\n" + (e.stderr or "")
                return False, out

        # Always keep pip tooling up to date
        ok, out = run([venv_python, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
        if not ok:
            self.logger.warning("pip upgrade failed; continuing anyway")
            self.logger.warning(out)

        base_cmd = [venv_python, "-m", "pip", "install", "--disable-pip-version-check", "--prefer-binary", "-r", str(self.requirements_file)]
        ok, out = run(base_cmd)
        if ok:
            self.logger.info("Dependencies installed successfully")
            return True

        # Log detailed failure and retry with a lighter set
        self.logger.error("Primary dependency install failed. Details follow:")
        for line in out.splitlines()[-80:]:
            self.logger.error(line)

        # Fallback to lite requirements for demo-only mode
        lite_reqs = Path("requirements_lite.txt")
        if not lite_reqs.exists():
            try:
                lite_reqs.write_text("\n".join([
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
                    # Security/certs
                    "cryptography>=42.0.0",
                    "cffi>=1.17.1",
                    "pycparser==2.21",
                    "python-dotenv==1.0.0",
                ]), encoding="utf-8")
            except Exception as e:
                self.logger.warning(f"Failed to write lite requirements: {e}")

        self.logger.info("Retrying with minimal dependencies (demo mode capable)...")
        ok, out2 = run([venv_python, "-m", "pip", "install", "--disable-pip-version-check", "--prefer-binary", "-r", str(lite_reqs)])
        if ok:
            self.logger.info("Lite dependencies installed. The app will run in demo mode; optional integrations may be unavailable until full requirements install succeeds.")
            return True

        self.logger.error("Lite dependency install also failed. Details:")
        for line in out2.splitlines()[-80:]:
            self.logger.error(line)
        return False
    
    def setup_environment(self) -> bool:
        """Complete environment setup"""
        steps = [
            ("Checking Python version", self.check_python_version),
            ("Creating virtual environment", self.create_virtual_environment),
            ("Installing dependencies", self.install_dependencies)
        ]
        
        for step_name, step_func in steps:
            self.logger.info(f"{step_name}...")
            if not step_func():
                return False
        
        return True

class ServerManager:
    """Manages the Flask application server"""
    
    def __init__(self, logger: LauncherLogger, dependency_manager: DependencyManager):
        self.logger = logger
        self.dep_manager = dependency_manager
        self.server_process = None
        self.server_url = "https://127.0.0.1:8000"
        self.is_running = False
        # Cache the resolved app working directory
        self._app_workdir = None
        self.cert_manager = None

    def _candidate_roots(self):
        """Return plausible roots to look for the Flask app files."""
        roots = []
        try:
            roots.append(Path.cwd())
        except Exception:
            pass
        try:
            roots.append(Path(__file__).resolve().parent)
        except Exception:
            pass
        try:
            roots.append(Path(sys.executable).resolve().parent)
        except Exception:
            pass
        # PyInstaller temp extraction dir when frozen
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            try:
                roots.append(Path(meipass))
            except Exception:
                pass
        # Previously persisted install location (if any)
        try:
            state_file = Path.home() / "AppData" / "Local" / "Financial Command Center" / "install_state.json"
            if state_file.exists():
                import json as _json
                data = _json.loads(state_file.read_text(encoding="utf-8"))
                p = data.get("app_dir")
                if p:
                    roots.append(Path(p))
        except Exception:
            pass
        # Unique paths only
        uniq = []
        seen = set()
        for r in roots:
            try:
                rp = str(r.resolve())
            except Exception:
                rp = str(r)
            if rp not in seen:
                seen.add(rp)
                uniq.append(r)
        return uniq

    def _resolve_app_entry(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Find the best app entry file and its working directory.
        Returns (app_path, workdir) or (None, None).
        """
        candidates = ["app_with_setup_wizard.py", "app.py"]
        for root in self._candidate_roots():
            for name in candidates:
                path = root / name
                if path.exists():
                    try:
                        return path.resolve(), path.parent.resolve()
                    except Exception:
                        return path, root
        # As a last resort, scan a few levels up from current working directory
        try:
            here = Path.cwd()
            for up in [here.parent, here.parent.parent]:
                if not up:
                    continue
                for name in candidates:
                    p = up / name
                    if p.exists():
                        return p.resolve(), p.parent.resolve()
        except Exception:
            pass
        return None, None
    
    def _setup_ssl_certificates(self) -> bool:
        """Setup SSL certificates using the cert_manager"""
        try:
            # Import cert_manager locally to avoid circular imports
            from cert_manager import CertificateManager
            
            # Find app working directory to place certificates there
            app_path, workdir = self._resolve_app_entry()
            if workdir:
                self.cert_manager = CertificateManager(base_dir=workdir, use_mkcert=True)
            else:
                self.cert_manager = CertificateManager(use_mkcert=True)
            
            self.logger.info("Setting up SSL certificates...")
            
            # Use enhanced certificate generation that prefers mkcert
            cert_generated = self.cert_manager.ensure_certificates()
            
            if cert_generated:
                if self.cert_manager.config.get("use_mkcert", False) and self.cert_manager.config.get("trust_installed", False):
                    self.logger.info("Browser-trusted certificates ready with mkcert!")
                else:
                    self.logger.info("SSL certificates generated successfully")
            else:
                self.logger.info("SSL certificates are already valid")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup SSL certificates: {e}")
            return False
    
    def start_server(self) -> bool:
        """Start the Flask application server"""
        try:
            # Setup SSL certificates first
            if not self._setup_ssl_certificates():
                self.logger.warning("SSL certificate setup failed, continuing without SSL")
            
            venv_python = self.dep_manager.get_venv_python()
            # Resolve app entry and working directory robustly
            app_path, workdir = self._resolve_app_entry()
            if app_path is None or workdir is None:
                # Provide detailed diagnostics
                search_paths = [str(p) for p in self._candidate_roots()]
                self.logger.error("Application entry file not found. Looked for app_with_setup_wizard.py or app.py in:")
                for p in search_paths:
                    self.logger.error(f"  - {p}")
                return False

            self._app_workdir = workdir
            self.logger.info(f"Using app entry: {app_path}")
            self.logger.info(f"App working directory: {workdir}")
            
            # Pick port (env override, then default 8000). If busy, try 8001-8010.
            def _pick_port():
                import socket
                preferred = os.environ.get('FCC_PORT') or os.environ.get('PORT') or '8000'
                try_order = [int(preferred)] + [p for p in range(8001, 8011)]
                for p in try_order:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        try:
                            s.bind(('127.0.0.1', p))
                            return p
                        except OSError:
                            continue
                return int(preferred)

            port = _pick_port()
            self.server_url = f"https://127.0.0.1:{port}"
            self.logger.info(f"Starting Financial Command Center server on port {port}...")
            
            # Set environment variables for proper SSL operation
            env = os.environ.copy()
            env.update({
                "FLASK_ENV": "production",
                "FORCE_HTTPS": "true",
                "ALLOW_HTTP": "false",
                # Force UTF-8 output and input so Unicode/emoji doesn't crash
                # when stdout/stderr are attached to a non-UTF console
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
                # Default to demo mode unless explicitly set by user
                "APP_MODE": env.get("APP_MODE", "demo"),
                # Communicate chosen port to the app
                "FCC_PORT": str(port),
            })
            
            self.server_process = subprocess.Popen(
                [venv_python, str(app_path)],
                env=env,
                cwd=str(workdir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            # Give server time to start
            time.sleep(3)
            
            if self.server_process.poll() is None:
                self.is_running = True
                self.logger.info("Server started successfully")
                return True
            else:
                self.logger.error("Server failed to start")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the Flask application server"""
        if self.server_process:
            self.logger.info("Stopping server...")
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            self.is_running = False
            self.logger.info("Server stopped")
    
    def is_server_healthy(self) -> bool:
        """Check if server is responding"""
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.get(f"{self.server_url}/health", 
                                  verify=False, timeout=5)
            return response.status_code == 200
        except:
            return False

class SystemTrayManager:
    """Manages system tray integration"""
    
    def __init__(self, logger: LauncherLogger, server_manager: ServerManager):
        self.logger = logger
        self.server_manager = server_manager
        self.icon = None
        
        if not SYSTEM_TRAY_AVAILABLE:
            self.logger.warning("System tray not available (install pillow and pystray)")
    
    def create_icon_image(self):
        """Create system tray icon"""
        # Create a simple icon
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Draw a simple financial symbol (dollar sign in circle)
        draw.ellipse([8, 8, 56, 56], fill='#667eea', outline='#5a6fd8')
        draw.text((24, 20), '$', fill='white', anchor='mm')
        
        return image
    
    def setup_system_tray(self):
        """Setup system tray with menu"""
        if not SYSTEM_TRAY_AVAILABLE:
            return
        
        image = self.create_icon_image()
        menu = pystray.Menu(
            item('Open Dashboard', self._open_dashboard),
            item('Open Setup Wizard', self._open_setup),
            pystray.Menu.SEPARATOR,
            item('Server Status', self._show_status),
            item('View Logs', self._open_logs),
            pystray.Menu.SEPARATOR,
            item('Restart Server', self._restart_server),
            item('Exit', self._quit_application)
        )
        
        self.icon = pystray.Icon(APP_NAME, image, menu=menu)
        
        # Run in separate thread
        tray_thread = threading.Thread(target=self.icon.run, daemon=True)
        tray_thread.start()
        self.logger.info("System tray activated")
    
    def _open_dashboard(self, icon, item):
        webbrowser.open(f"{self.server_manager.server_url}/admin/dashboard")
    
    def _open_setup(self, icon, item):
        webbrowser.open(f"{self.server_manager.server_url}/setup")
    
    def _show_status(self, icon, item):
        status = "Running" if self.server_manager.is_running else "Stopped"
        health = "Healthy" if self.server_manager.is_server_healthy() else "Unhealthy"
        messagebox.showinfo("Server Status", f"Server: {status}\nHealth: {health}")
    
    def _open_logs(self, icon, item):
        if sys.platform == "win32":
            os.startfile("launcher.log")
        else:
            subprocess.run(["open", "launcher.log"])
    
    def _restart_server(self, icon, item):
        self.server_manager.stop_server()
        time.sleep(2)
        self.server_manager.start_server()
    
    def _quit_application(self, icon, item):
        self.server_manager.stop_server()
        if self.icon:
            self.icon.stop()
        sys.exit(0)

class ErrorHandler:
    """Client-friendly error handling and support instructions"""
    
    def __init__(self, logger: LauncherLogger):
        self.logger = logger
    
    def show_error_dialog(self, title: str, message: str, error_code: str = None):
        """Show user-friendly error dialog with support information"""
        
        support_info = f"""
Support Information:
- Error Code: {error_code or 'GENERAL_ERROR'}
- Version: {LAUNCHER_VERSION}
- Log File: launcher.log

Contact Support:
- Email: {SUPPORT_EMAIL}
- Documentation: {SUPPORT_URL}
- Troubleshooting Guide: {SUPPORT_URL}/troubleshooting
        """
        
        full_message = f"{message}\n\n{support_info}"
        
        root = tk.Tk()
        root.withdraw()  # Hide main window
        
        messagebox.showerror(title, full_message)
        root.destroy()
    
    def handle_python_error(self):
        self.show_error_dialog(
            "Python Installation Error",
            "Python 3.8+ is required but was not found.\n\n"
            "Please install Python from python.org and try again.",
            "PYTHON_NOT_FOUND"
        )
    
    def handle_dependency_error(self):
        self.show_error_dialog(
            "Dependency Installation Error",
            "Failed to install required packages.\n\n"
            "This could be due to:\n"
            "- Network connectivity issues\n"
            "- Insufficient disk space\n"
            "- Permission restrictions\n\n"
            "Try running as administrator or check your internet connection.",
            "DEPENDENCY_INSTALL_FAILED"
        )
    
    def handle_server_error(self):
        self.show_error_dialog(
            "Server Start Error",
            "Failed to start the Financial Command Center server.\n\n"
            "This could be due to:\n"
            "- Port 8000 already in use\n"
            "- SSL certificate issues\n"
            "- Missing environment variables\n\n"
            "Check the launcher.log file for detailed error information.",
            "SERVER_START_FAILED"
        )

class BrandedInstaller:
    """Creates a branded installer experience"""
    
    def __init__(self, logger: LauncherLogger):
        self.logger = logger
        self.progress_window = None
        self.progress_var = None
        self.status_var = None
    
    def show_welcome_screen(self):
        """Show branded welcome screen"""
        root = tk.Tk()
        root.title(f"{APP_NAME} - Setup")
        root.geometry("600x500")  # Increased height to show buttons
        root.resizable(False, False)
        
        # Make sure window appears on top
        root.lift()
        root.attributes('-topmost', True)
        root.after_idle(root.attributes, '-topmost', False)
        
        # Configure styling
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main frame
        main_frame = ttk.Frame(root, padding="40")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text=APP_NAME, 
                               font=('Segoe UI', 24, 'bold'))
        title_label.pack()
        
        subtitle_label = ttk.Label(header_frame, 
                                  text="Unified Financial Operations Platform",
                                  font=('Segoe UI', 12))
        subtitle_label.pack(pady=(5, 0))
        
        # Content
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        welcome_text = """
Welcome to Financial Command Center AI!

This installer will:
- Set up a Python virtual environment
- Install all required dependencies
- Configure SSL certificates
- Launch the web-based setup wizard
- Create system tray shortcuts

Click 'Start Setup' to begin the installation process.
        """
        
        text_label = ttk.Label(content_frame, text=welcome_text, 
                              font=('Segoe UI', 11), justify=tk.LEFT)
        text_label.pack(anchor=tk.W)
        
        # Buttons - with more explicit layout
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))  # Add top padding
        
        # Create buttons with specific sizes
        cancel_button = ttk.Button(button_frame, text="Cancel", width=12,
                                  command=root.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=(0, 5))
        
        start_button = ttk.Button(button_frame, text="Start Setup", width=12,
                                 command=lambda: self._start_setup(root))
        start_button.pack(side=tk.RIGHT, padx=(10, 5))
        
        # Make Start Setup button the default and focused
        start_button.focus_set()
        root.bind('<Return>', lambda event: self._start_setup(root))
        
        # Center window
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry(f"+{x}+{y}")
        
        root.mainloop()
    
    def _start_setup(self, parent_window):
        """Start the setup process"""
        parent_window.destroy()
        self.show_progress_window()
    
    def show_progress_window(self):
        """Show installation progress window"""
        self.progress_window = tk.Tk()
        self.progress_window.title(f"{APP_NAME} - Installing")
        self.progress_window.geometry("500x300")
        self.progress_window.resizable(False, False)
        
        # Main frame
        main_frame = ttk.Frame(self.progress_window, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Installing Financial Command Center AI",
                               font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var,
                                      maximum=100, length=400)
        progress_bar.pack(pady=(0, 20))
        
        # Status text
        self.status_var = tk.StringVar(value="Initializing...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                font=('Segoe UI', 10))
        status_label.pack()
        
        # Log area
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Center window
        self.progress_window.update_idletasks()
        x = (self.progress_window.winfo_screenwidth() // 2) - (self.progress_window.winfo_width() // 2)
        y = (self.progress_window.winfo_screenheight() // 2) - (self.progress_window.winfo_height() // 2)
        self.progress_window.geometry(f"+{x}+{y}")
        
        # Start installation in separate thread
        install_thread = threading.Thread(target=self._run_installation, daemon=True)
        install_thread.start()
        
        self.progress_window.mainloop()
    
    def _run_installation(self):
        """Run the complete installation process"""
        try:
            # Use the connected launcher if available
            if hasattr(self, 'launcher'):
                success = self._run_setup_with_launcher()
            else:
                # Fallback - create our own launcher instance
                logger = LauncherLogger()
                dependency_manager = DependencyManager(logger)
                server_manager = ServerManager(logger, dependency_manager)
                success = self._run_setup_standalone(dependency_manager, server_manager)
            
            if success:
                self.progress_window.after(0, lambda: self.update_status("Installation completed successfully!", 100))
                # Schedule closing progress window and showing completion dialog
                self.progress_window.after(3000, self._on_installation_complete)  # Wait 3 seconds
            else:
                self.progress_window.after(0, lambda: self.update_status("Installation failed!", 100))
            
            return success
            
        except Exception as e:
            self.progress_window.after(0, lambda e=e: self.update_status(f"Error: {e}", 100))
            return False
    
    def _run_setup_with_launcher(self):
        """Run setup using the connected launcher"""
        setup_steps = [
            ("Checking Python installation...", self.launcher._check_python, 20),
            ("Setting up virtual environment...", self.launcher._setup_environment, 60),
            ("Starting application server...", self.launcher._start_server, 90),
            ("Finalizing setup...", self.launcher._finalize_setup, 100)
        ]
        
        for step_name, step_func, progress in setup_steps:
            # Update UI on main thread
            def update_ui(name=step_name, prog=progress):
                self.update_status(name, prog)
                self.progress_window.update()
            
            self.progress_window.after(0, update_ui)
            time.sleep(1)  # Give UI time to update
            
            try:
                if not step_func():
                    self.progress_window.after(0, lambda: self.update_status("Setup step failed!", 100))
                    return False
            except Exception as e:
                self.progress_window.after(0, lambda e=e: self.update_status(f"Error in setup: {e}", 100))
                return False
        
        return True
    
    def _run_setup_standalone(self, dependency_manager, server_manager):
        """Run setup standalone"""
        setup_steps = [
            ("Checking Python installation...", self._check_python_with_progress, dependency_manager, 20),
            ("Setting up virtual environment...", self._setup_environment_with_progress, dependency_manager, 60),
            ("Starting application server...", self._start_server_with_progress, server_manager, 90),
            ("Finalizing setup...", self._finalize_setup_with_progress, server_manager, 100)
        ]
        
        for step_name, step_func, manager, progress in setup_steps:
            # Update UI on main thread
            def update_ui(name=step_name, prog=progress):
                self.update_status(name, prog)
                self.progress_window.update()
            
            self.progress_window.after(0, update_ui)
            time.sleep(1)  # Give UI time to update
            
            try:
                if not step_func(manager):
                    self.progress_window.after(0, lambda: self.update_status("Setup step failed!", 100))
                    return False
            except Exception as e:
                self.progress_window.after(0, lambda e=e: self.update_status(f"Error in setup: {e}", 100))
                return False
        
        return True
    
    def _check_python_with_progress(self, dependency_manager):
        """Check Python with progress updates"""
        try:
            result = dependency_manager.check_python_version()
            if result:
                self.progress_window.after(0, lambda: self.update_status("Python version check passed", None))
            return result
        except Exception:
            self.progress_window.after(0, lambda: self.update_status("Python version check failed", None))
            return False
    
    def _setup_environment_with_progress(self, dependency_manager):
        """Setup environment with progress updates"""
        try:
            self.progress_window.after(0, lambda: self.update_status("Creating virtual environment...", None))
            if not dependency_manager.create_virtual_environment():
                return False
            
            self.progress_window.after(0, lambda: self.update_status("Installing dependencies...", None))
            if not dependency_manager.install_dependencies():
                return False
                
                self.progress_window.after(0, lambda: self.update_status("Environment setup completed", None))
            return True
        except Exception:
            self.progress_window.after(0, lambda: self.update_status("Environment setup failed", None))
            return False
    
    def _start_server_with_progress(self, server_manager):
        """Start server with progress updates"""
        try:
            self.progress_window.after(0, lambda: self.update_status("Starting application server...", None))
            result = server_manager.start_server()
            if result:
                self.progress_window.after(0, lambda: self.update_status("Server started successfully", None))
            else:
                self.progress_window.after(0, lambda: self.update_status("Server failed to start", None))
            return result
        except Exception:
            self.progress_window.after(0, lambda: self.update_status("Server start failed", None))
            return False
    
    def _finalize_setup_with_progress(self, server_manager):
        """Finalize setup with progress updates"""
        try:
            self.progress_window.after(0, lambda: self.update_status("Checking server health...", None))
            for i in range(10):
                if server_manager.is_server_healthy():
                    self.progress_window.after(0, lambda: self.update_status("Server is healthy and ready", None))
                    return True
                time.sleep(1)
            
            self.progress_window.after(0, lambda: self.update_status("Server health check timeout", None))
            return False
        except Exception:
            self.progress_window.after(0, lambda: self.update_status("Server health check failed", None))
            return False
    
    def _on_installation_complete(self):
        """Handle successful installation completion"""
        try:
            # Close progress window
            self.progress_window.destroy()
            
            # If we have a launcher, start the post-installation process
            if hasattr(self, 'launcher'):
                # Start system tray
                self.launcher.tray_manager.setup_system_tray()
                
                # Open web browser to setup wizard
                # Open the best available start URL (prefer setup during installation)
                self.launcher._open_start_url(prefer_setup=True)
                
                # Show completion dialog
                self.show_completion_dialog(True)
                
                # Keep launcher alive in background
                threading.Thread(target=self.launcher._keep_alive, daemon=True).start()
            else:
                self.show_completion_dialog(True)
                
        except Exception as e:
            print(f"Error in completion handler: {e}")
            self.show_completion_dialog(True)  # Still show success
    
    def update_progress(self, value: float):
        """Update progress bar"""
        if self.progress_var:
            self.progress_var.set(value)
    
    def update_status(self, message: str, progress: float = None):
        """Update status message and optionally progress"""
        if self.status_var:
            self.status_var.set(message)
        if progress is not None:
            self.update_progress(progress)
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
    
    def show_completion_dialog(self, success: bool):
        """Show installation completion dialog"""
        if self.progress_window:
            self.progress_window.destroy()
        
        root = tk.Tk()
        root.withdraw()
        
        if success:
            messagebox.showinfo(
                "Installation Complete",
                f"{APP_NAME} has been successfully installed!\n\n"
                "The application is now running and available in your system tray.\n"
                "Your web browser will open to the setup wizard."
            )
        else:
            messagebox.showerror(
                "Installation Failed",
                f"Failed to install {APP_NAME}.\n\n"
                "Please check the launcher.log file for details."
            )
        
        root.destroy()

class FinancialLauncher:
    """Main launcher class that orchestrates everything"""
    
    def __init__(self):
        self.logger = LauncherLogger()
        self.dependency_manager = DependencyManager(self.logger)
        self.server_manager = ServerManager(self.logger, self.dependency_manager)
        self.error_handler = ErrorHandler(self.logger)
        self.installer = BrandedInstaller(self.logger)
        self.tray_manager = SystemTrayManager(self.logger, self.server_manager)
        # Connect installer to launcher for actual setup
        self.installer.launcher = self

    def _install_state_path(self) -> str:
        """Return path to persistent install state file."""
        try:
            base = os.environ.get('APPDATA') if sys.platform == 'win32' else os.path.expanduser('~/.local/share')
            folder = os.path.join(base, 'Financial Command Center')
            os.makedirs(folder, exist_ok=True)
            return os.path.join(folder, 'install_state.json')
        except Exception:
            # Fallback to current directory
            return os.path.join(os.getcwd(), '.install_state.json')

    def _is_installed(self) -> bool:
        """Detect if installation has previously completed."""
        try:
            p = Path(self._install_state_path())
            if not p.exists():
                # Fallback heuristic: treat as installed if virtual env exists
                try:
                    return Path('.venv').exists()
                except Exception:
                    return False
            data = json.loads(p.read_text(encoding='utf-8'))
            return bool(data.get('installed'))
        except Exception:
            return False

    def _mark_installed(self):
        """Persist installation completion state."""
        try:
            p = Path(self._install_state_path())
            state = {
                'installed': True,
                'version': LAUNCHER_VERSION,
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
            }
            p.write_text(json.dumps(state, indent=2), encoding='utf-8')
        except Exception as e:
            self.logger.warning(f"Failed to persist install state: {e}")
    
    def run(self):
        """Main launcher entry point"""
        self.logger.info(f"Starting {APP_NAME} Launcher v{LAUNCHER_VERSION}")

        force_setup = any(arg.lower() in ("--setup", "/setup") for arg in sys.argv[1:])
        packaged = bool(getattr(sys, 'frozen', False))

        # If packaged (EXE/MSI install) and not forcing setup, skip the Tk installer
        # If not packaged, also skip installer when we detect prior install
        if (packaged and not force_setup) or (not force_setup and self._is_installed()):
            self.logger.info("Detected installed environment. Skipping installer wizard.")
            if self.server_manager.start_server():
                try:
                    self._create_shortcuts_if_needed()
                except Exception as e:
                    self.logger.warning(f"Shortcut creation skipped: {e}")
                self.tray_manager.setup_system_tray()
                self._open_start_url(prefer_setup=False)  # Prefer dashboard for regular launches
                self._keep_alive()
                return
            else:
                self.logger.warning("Server failed to start; launching installer wizard.")

        # Show branded welcome screen (first run or forced)
        self.installer.show_welcome_screen()
    
    def run_setup_with_progress(self):
        """Run setup process with progress updates - called by installer"""
        if self._run_setup():
            self.logger.info("Setup completed successfully")
            # Start system tray
            self.tray_manager.setup_system_tray()
            # Open the best available start URL (prefer setup during installation)
            self._open_start_url(prefer_setup=True)
            # Create shortcuts so users can re-open without terminal
            try:
                self._create_shortcuts_if_needed()
            except Exception as e:
                self.logger.warning(f"Shortcut creation skipped: {e}")
            # Persist install completion so future launches skip the wizard
            self._mark_installed()
            # Keep launcher running for system tray
            self._keep_alive()
            return True
        else:
            self.logger.error("Setup failed")
            return False
    
    def _run_setup(self) -> bool:
        """Run the complete setup process"""
        setup_steps = [
            ("Checking Python installation", self._check_python, 15),
            ("Setting up virtual environment", self._setup_environment, 45),
            ("Generating SSL certificates", self._setup_ssl_only, 70),
            ("Starting application server", self._start_server, 90),
            ("Finalizing setup", self._finalize_setup, 100)
        ]
        
        for step_name, step_func, progress in setup_steps:
            self.logger.info(f"{step_name}...")
            if hasattr(self.installer, 'update_status'):
                self.installer.update_status(step_name, progress)
            
            if not step_func():
                return False
        
        return True
    
    def _setup_ssl_only(self) -> bool:
        """Setup SSL certificates as a separate step"""
        try:
            # Import cert_manager locally
            from cert_manager import CertificateManager
            
            # Create cert manager with mkcert enabled in current directory 
            cert_manager = CertificateManager(use_mkcert=True)
            
            self.logger.info("Setting up SSL certificates...")
            
            # Use the enhanced certificate generation that prefers mkcert
            cert_generated = cert_manager.ensure_certificates()
            
            if cert_generated:
                self.logger.info("SSL certificates generated successfully")
                if cert_manager.config.get("use_mkcert", False) and cert_manager.config.get("trust_installed", False):
                    self.logger.info("Browser-trusted certificates created with mkcert!")
                    self.logger.info("Browsers should show secure connections without warnings")
                else:
                    self.logger.info("Self-signed certificates created - may show browser warnings")
                    # Try to install CA certificate to Windows trust store for self-signed certs
                    self._install_ca_certificate(cert_manager)
            else:
                self.logger.info("SSL certificates were already valid")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup SSL certificates: {e}")
            return False
    
    def _install_ca_certificate(self, cert_manager):
        """Install CA certificate to Windows trust store"""
        try:
            import sys
            if sys.platform != "win32":
                return
            
            ca_cert_path = cert_manager.config["ca_cert"]
            if not Path(ca_cert_path).exists():
                self.logger.warning("CA certificate not found, skipping trust store installation")
                return
            
            self.logger.info("Installing CA certificate to Windows trust store...")
            
            # Use PowerShell to install certificate to trusted root store
            ps_command = f"""
                try {{
                    Import-Certificate -FilePath '{ca_cert_path}' -CertStoreLocation 'Cert:\\LocalMachine\\Root' -ErrorAction Stop
                    Write-Host 'Certificate installed successfully to trusted root store'
                }} catch {{
                    Write-Host 'Failed to install to machine store, trying current user store...'
                    try {{
                        Import-Certificate -FilePath '{ca_cert_path}' -CertStoreLocation 'Cert:\\CurrentUser\\Root' -ErrorAction Stop
                        Write-Host 'Certificate installed successfully to user store'
                    }} catch {{
                        Write-Host 'Failed to install certificate: ' + $_.Exception.Message
                        exit 1
                    }}
                }}
            """
            
            result = subprocess.run([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info("CA certificate installed to Windows trust store")
                self.logger.info("Browser should now show the site as secure")
            else:
                self.logger.warning(f"Certificate installation failed: {result.stderr}")
                self.logger.info("You may see 'Not secure' warnings in the browser")
                
        except Exception as e:
            self.logger.warning(f"Failed to install CA certificate: {e}")
            self.logger.info("You may see 'Not secure' warnings in the browser")
    
    def _check_python(self) -> bool:
        """Check Python installation"""
        try:
            if not self.dependency_manager.check_python_version():
                self.error_handler.handle_python_error()
                return False
            return True
        except Exception as e:
            self.logger.error(f"Python check failed: {e}")
            self.error_handler.handle_python_error()
            return False
    
    def _setup_environment(self) -> bool:
        """Setup Python environment and dependencies"""
        if not self.dependency_manager.setup_environment():
            self.error_handler.handle_dependency_error()
            return False
        return True
    
    def _start_server(self) -> bool:
        """Start the application server"""
        if not self.server_manager.start_server():
            self.error_handler.handle_server_error()
            return False
        return True
    
    def _finalize_setup(self) -> bool:
        """Finalize setup process"""
        # Wait for server to be fully ready
        for i in range(10):
            if self.server_manager.is_server_healthy():
                return True
            time.sleep(1)
        return False
    
    def _launch_browser(self):
        """Launch web browser to setup wizard"""
        try:
            setup_url = f"{self.server_manager.server_url}/setup"
            if not self.server_manager.is_server_healthy():
                setup_url = f"{self.server_manager.server_url}/"
            
            self.logger.info(f"Opening browser to {setup_url}")
            webbrowser.open(setup_url)
        except Exception as e:
            self.logger.error(f"Failed to launch browser: {e}")

    def _open_start_url(self, prefer_setup=False):
        """Open the start URL. Always go to root path and let Flask app handle routing."""
        try:
            base = self.server_manager.server_url
            start_url = f"{base}/"
            
            self.logger.info(f"Opening browser to {start_url}")
            webbrowser.open(start_url)
        except Exception as e:
            self.logger.error(f"Failed to open start URL: {e}")

    def _create_windows_shortcut(self, lnk_path: str, target: str, args: str, icon: str, workdir: str):
        """Create a .lnk shortcut using PowerShell WScript.Shell COM."""
        if sys.platform != "win32":
            return
        def esc(s: str) -> str:
            return s.replace("'", "''") if s else s
        ps = (
            f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{esc(lnk_path)}');"
            f"$s.TargetPath='{esc(target)}';"
            f"$s.Arguments='{esc(args)}';"
            f"$s.WorkingDirectory='{esc(workdir)}';"
            + (f"$s.IconLocation='{esc(icon)}';" if icon else "") +
            "$s.WindowStyle=7;"
            "$s.Save();"
        )
        try:
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True)
            self.logger.info(f"Created shortcut: {lnk_path}")
        except Exception as e:
            self.logger.warning(f"Failed to create shortcut {lnk_path}: {e}")

    def _create_shortcuts_if_needed(self):
        """Ensure Desktop and Start Menu shortcuts exist on Windows."""
        if sys.platform != 'win32':
            return
        try:
            from pathlib import Path
            app_name = APP_NAME
            repo_root = str(Path(__file__).resolve().parent)
            desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
            start_menu_dir = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', app_name)
            os.makedirs(start_menu_dir, exist_ok=True)

            launch_cmd = os.path.join(repo_root, 'ultimate_cert_fix.cmd')
            quick_start_cmd = os.path.join(repo_root, 'ultimate_cert_fix.cmd')
            quick_start_ps1 = os.path.join(repo_root, 'ultimate_cert_fix.cmd')

            # Determine target/args for full launcher (prefer GUI pythonw over .cmd to avoid console popups)
            if getattr(sys, 'frozen', False):
                target = sys.executable
                args = ''
            else:
                vpy = self.dependency_manager.get_venv_python()
                pyw = vpy[:-4] + 'w.exe' if vpy.lower().endswith('python.exe') else vpy
                if os.path.exists(pyw):
                    target = pyw
                    args = os.path.join(repo_root, 'financial_launcher.py')
                elif os.path.exists(launch_cmd):
                    target = launch_cmd
                    args = ''
                else:
                    target = 'pythonw.exe'
                    args = os.path.join(repo_root, 'financial_launcher.py')

            icon_path = str(Path(repo_root, 'assets', 'launcher_icon.ico'))
            icon = icon_path if Path(icon_path).exists() else ''
            
            # Quick Start targets (prefer PowerShell for better error handling)
            if os.path.exists(quick_start_ps1):
                quick_target = 'powershell.exe'
                quick_args = f'-NoProfile -ExecutionPolicy Bypass -File "{quick_start_ps1}"'
            elif os.path.exists(quick_start_cmd):
                quick_target = quick_start_cmd
                quick_args = ''
            else:
                # Fallback to direct Python call
                quick_target = self.dependency_manager.get_venv_python()
                quick_args = os.path.join(repo_root, 'app_with_setup_wizard.py')

            # Desktop shortcuts
            if desktop and os.path.isdir(desktop):
                # Full launcher shortcut
                lnk1 = os.path.join(desktop, f'{app_name}.lnk')
                self._create_windows_shortcut(lnk1, target, args, icon, repo_root)
                
                # Quick start shortcut (main one users will use)
                quick_lnk = os.path.join(desktop, f'{app_name} - Quick Start.lnk')
                self._create_windows_shortcut(quick_lnk, quick_target, quick_args, icon, repo_root)

            # Start Menu shortcuts
            # Full launcher shortcut
            lnk2 = os.path.join(start_menu_dir, f'{app_name}.lnk')
            self._create_windows_shortcut(lnk2, target, args, icon, repo_root)
            
            # Quick start shortcut in Start Menu
            quick_lnk2 = os.path.join(start_menu_dir, f'{app_name} - Quick Start.lnk')
            self._create_windows_shortcut(quick_lnk2, quick_target, quick_args, icon, repo_root)
        except Exception as e:
            self.logger.warning(f'Failed to set up shortcuts: {e}')

    def _keep_alive(self):
        """Keep launcher alive for system tray functionality"""
        if SYSTEM_TRAY_AVAILABLE:
            # System tray will keep app alive, but also monitor browser activity
            try:
                self._monitor_browser_activity()
            except KeyboardInterrupt:
                self.logger.info("Shutting down...")
                self.server_manager.stop_server()
        else:
            # No system tray, just show a simple GUI to keep alive
            self._show_control_panel()
    
    def _monitor_browser_activity(self):
        """Monitor browser activity and shut down when browser is closed"""
        import time
        
        last_ping_time = time.time()
        browser_timeout = 60  # 1 minute without ping = shutdown
        
        self.logger.info("Monitoring browser activity. Will auto-shutdown 1 minute after browser closes.")
        
        try:
            while True:
                current_time = time.time()
                
                # Check for browser ping file (created by JavaScript in the web app)
                ping_file = Path("browser_ping.tmp")
                if ping_file.exists():
                    try:
                        # Read the ping timestamp
                        ping_timestamp = float(ping_file.read_text().strip())
                        if current_time - ping_timestamp < 30:  # Ping is recent (within 30 seconds)
                            last_ping_time = current_time
                    except:
                        pass
                
                # Check if too much time has passed without a ping
                time_since_ping = current_time - last_ping_time
                if time_since_ping > browser_timeout:
                    self.logger.info("No browser ping detected for 1 minute. Shutting down...")
                    break
                
                time.sleep(5)  # Check every 5 seconds
                
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        
        # Cleanup
        ping_file = Path("browser_ping.tmp")
        if ping_file.exists():
            ping_file.unlink()
        
        self.logger.info("Shutting down launcher...")
        self.server_manager.stop_server()
        sys.exit(0)
    
    def _update_browser_processes(self, browser_set):
        """Update set of browser processes"""
        import psutil
        browser_names = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe']
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() in browser_names:
                    browser_set.add(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def _is_browser_accessing_app(self, browser_processes):
        """Check if any browser is likely accessing our app"""
        # Simple heuristic: if server is receiving requests, assume browser is active
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Try to get recent access logs or just check if server responds
            response = requests.get(f"{self.server_manager.server_url}/health", 
                                  verify=False, timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _show_control_panel(self):
        """Show simple control panel when system tray is not available"""
        root = tk.Tk()
        root.title(f"{APP_NAME} - Control Panel")
        root.geometry("400x300")
        
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_frame, text=APP_NAME, 
                               font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        status_label = ttk.Label(main_frame, text="Server Running")
        status_label.pack(pady=(0, 10))
        
        url_label = ttk.Label(main_frame, text=self.server_manager.server_url)
        url_label.pack(pady=(0, 20))
        
        # Buttons
        ttk.Button(main_frame, text="Open Dashboard",
                  command=lambda: webbrowser.open(f"{self.server_manager.server_url}/admin/dashboard")).pack(pady=5)
        
        ttk.Button(main_frame, text="Open Setup",
                  command=lambda: webbrowser.open(f"{self.server_manager.server_url}/setup")).pack(pady=5)
        
        ttk.Button(main_frame, text="View Logs",
                  command=lambda: os.startfile("launcher.log") if sys.platform == "win32" else subprocess.run(["open", "launcher.log"])).pack(pady=5)
        
        ttk.Button(main_frame, text="Stop & Exit",
                  command=self._quit_application).pack(pady=(20, 0))
        
        root.protocol("WM_DELETE_WINDOW", self._quit_application)
        root.mainloop()
    
    def _quit_application(self):
        """Clean shutdown"""
        self.logger.info("Shutting down Financial Command Center Launcher...")
        self.server_manager.stop_server()
        sys.exit(0)

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        print(f"{APP_NAME} Launcher v{LAUNCHER_VERSION}")
        return
    
    launcher = FinancialLauncher()

    # Allow forcing the setup wizard with --setup
    force_setup = any(arg.lower() in ('--setup', '/setup') for arg in sys.argv[1:])
    if not force_setup and launcher._is_installed():
        # Skip installer: start server, open browser, system tray
        launcher.logger.info("Detected prior installation. Skipping installer wizard.")
        if launcher.server_manager.start_server():
            try:
                launcher._create_shortcuts_if_needed()
            except Exception as e:
                launcher.logger.warning(f"Shortcut creation skipped: {e}")
            launcher.tray_manager.setup_system_tray()
            launcher._open_start_url(prefer_setup=False)  # Prefer dashboard for regular launches
            launcher._keep_alive()
            return
        else:
            launcher.logger.warning("Server failed to start on resume; launching installer.")

    launcher.run()

if __name__ == "__main__":
    main()





