# automation_config_manager.py
# Advanced configuration management for Financial Command Center AI automation
# Provides GUI and CLI tools for managing automation settings

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomationConfigManager:
    """GUI and programmatic interface for managing automation configuration"""

    def __init__(self):
        self.root_path = Path(__file__).resolve().parent
        self.config_file = self.root_path / "automation_config.json"
        self.backup_dir = self.root_path / "config_backups"
        self.backup_dir.mkdir(exist_ok=True)

        self.default_config = {
            "email_settings": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "recipients": [],
                "use_tls": True
            },
            "payment_reminders": {
                "enabled": True,
                "days_before_due": [7, 3, 1],
                "overdue_days": [1, 3, 7, 14, 30],
                "template": "default",
                "auto_escalate": True
            },
            "expense_categorization": {
                "enabled": True,
                "confidence_threshold": 0.7,
                "auto_apply": False,
                "custom_categories": [],
                "learning_mode": True
            },
            "recurring_invoices": {
                "enabled": True,
                "default_terms": "NET30",
                "auto_send": False,
                "grace_period_days": 3,
                "templates": []
            },
            "alerts": {
                "low_balance_threshold": 1000.0,
                "low_balance_enabled": True,
                "large_transaction_threshold": 5000.0,
                "large_transaction_enabled": True,
                "payment_received_enabled": True,
                "payment_received_minimum": 0.0,
                "unusual_activity_enabled": True,
                "weekend_monitoring": False
            },
            "automation_schedule": {
                "payment_reminders": "09:00",
                "expense_categorization": "10:00",
                "recurring_invoices": "08:00",
                "balance_checks": "hourly",
                "transaction_monitoring": "real-time",
                "timezone": "UTC"
            },
            "integrations": {
                "plaid_enabled": True,
                "stripe_enabled": False,
                "xero_enabled": False,
                "quickbooks_enabled": False
            },
            "security": {
                "api_key_rotation_days": 90,
                "audit_logging": True,
                "data_retention_days": 365,
                "encryption_enabled": True
            },
            "performance": {
                "batch_size": 100,
                "rate_limit_requests_per_minute": 60,
                "cache_duration_minutes": 30,
                "concurrent_processes": 2
            }
        }

        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file with fallback to defaults"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return self._merge_config(self.default_config, loaded_config)
            else:
                # Create default config file
                self.save_config(self.default_config)
                return self.default_config.copy()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.default_config.copy()

    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge loaded config with defaults"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def save_config(self, config: Dict[str, Any] = None) -> bool:
        """Save configuration to file with backup"""
        try:
            if config is None:
                config = self.config

            # Create backup of existing config
            if self.config_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"automation_config_backup_{timestamp}.json"
                backup_file.write_text(self.config_file.read_text())

            # Save new config
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

            self.config = config
            logger.info(f"Configuration saved to {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

    def validate_config(self, config: Dict[str, Any] = None) -> List[str]:
        """Validate configuration and return list of errors"""
        if config is None:
            config = self.config

        errors = []

        # Validate email settings
        email = config.get("email_settings", {})
        if email.get("enabled", True):
            if not email.get("sender_email"):
                errors.append("Email sender address is required")
            if not email.get("sender_password"):
                errors.append("Email sender password is required")
            if not email.get("recipients"):
                errors.append("At least one email recipient is required")

        # Validate thresholds
        alerts = config.get("alerts", {})
        if alerts.get("low_balance_threshold", 0) < 0:
            errors.append("Low balance threshold must be positive")
        if alerts.get("large_transaction_threshold", 0) < 0:
            errors.append("Large transaction threshold must be positive")

        # Validate schedule times
        schedule = config.get("automation_schedule", {})
        time_fields = ["payment_reminders", "expense_categorization", "recurring_invoices"]
        for field in time_fields:
            time_str = schedule.get(field, "")
            if time_str and time_str != "hourly" and time_str != "real-time":
                try:
                    datetime.strptime(time_str, "%H:%M")
                except ValueError:
                    errors.append(f"Invalid time format for {field}: {time_str}")

        return errors

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        config = self.config
        return {
            "automation_modules": {
                "payment_reminders": config["payment_reminders"]["enabled"],
                "expense_categorization": config["expense_categorization"]["enabled"],
                "recurring_invoices": config["recurring_invoices"]["enabled"]
            },
            "alert_thresholds": {
                "low_balance": config["alerts"]["low_balance_threshold"],
                "large_transaction": config["alerts"]["large_transaction_threshold"]
            },
            "integrations": config["integrations"],
            "email_configured": bool(config["email_settings"]["sender_email"]),
            "recipients_count": len(config["email_settings"]["recipients"]),
            "validation_errors": self.validate_config()
        }

class AutomationConfigGUI:
    """Tkinter GUI for automation configuration"""

    def __init__(self):
        self.manager = AutomationConfigManager()
        self.root = tk.Tk()
        self.root.title("Financial Automation Configuration")
        self.root.geometry("800x600")

        self.create_widgets()
        self.load_current_config()

    def create_widgets(self):
        """Create the GUI widgets"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Email Settings Tab
        self.create_email_tab()

        # Automation Tab
        self.create_automation_tab()

        # Alerts Tab
        self.create_alerts_tab()

        # Schedule Tab
        self.create_schedule_tab()

        # Advanced Tab
        self.create_advanced_tab()

        # Control buttons
        self.create_control_buttons()

    def create_email_tab(self):
        """Create email configuration tab"""
        email_frame = ttk.Frame(self.notebook)
        self.notebook.add(email_frame, text="Email Settings")

        # SMTP Settings
        ttk.Label(email_frame, text="SMTP Server:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.smtp_server = tk.StringVar()
        ttk.Entry(email_frame, textvariable=self.smtp_server, width=40).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(email_frame, text="SMTP Port:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.smtp_port = tk.StringVar()
        ttk.Entry(email_frame, textvariable=self.smtp_port, width=40).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(email_frame, text="Sender Email:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.sender_email = tk.StringVar()
        ttk.Entry(email_frame, textvariable=self.sender_email, width=40).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(email_frame, text="Password:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.sender_password = tk.StringVar()
        ttk.Entry(email_frame, textvariable=self.sender_password, show="*", width=40).grid(row=3, column=1, padx=5, pady=5)

        # Recipients
        ttk.Label(email_frame, text="Recipients (one per line):").grid(row=4, column=0, sticky="nw", padx=5, pady=5)
        self.recipients_text = tk.Text(email_frame, height=5, width=40)
        self.recipients_text.grid(row=4, column=1, padx=5, pady=5)

        # TLS Setting
        self.use_tls = tk.BooleanVar()
        ttk.Checkbutton(email_frame, text="Use TLS", variable=self.use_tls).grid(row=5, column=1, sticky="w", padx=5, pady=5)

    def create_automation_tab(self):
        """Create automation modules tab"""
        auto_frame = ttk.Frame(self.notebook)
        self.notebook.add(auto_frame, text="Automation")

        # Payment Reminders
        ttk.LabelFrame(auto_frame, text="Payment Reminders").grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.payment_reminders_enabled = tk.BooleanVar()
        ttk.Checkbutton(auto_frame, text="Enable Payment Reminders", variable=self.payment_reminders_enabled).grid(row=1, column=0, sticky="w", padx=10, pady=2)

        # Expense Categorization
        ttk.LabelFrame(auto_frame, text="Expense Categorization").grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.expense_categorization_enabled = tk.BooleanVar()
        ttk.Checkbutton(auto_frame, text="Enable AI Categorization", variable=self.expense_categorization_enabled).grid(row=3, column=0, sticky="w", padx=10, pady=2)

        ttk.Label(auto_frame, text="Confidence Threshold:").grid(row=4, column=0, sticky="w", padx=10, pady=2)
        self.confidence_threshold = tk.StringVar()
        ttk.Entry(auto_frame, textvariable=self.confidence_threshold, width=10).grid(row=4, column=1, sticky="w", padx=5, pady=2)

        self.auto_apply_categorization = tk.BooleanVar()
        ttk.Checkbutton(auto_frame, text="Auto-apply suggestions", variable=self.auto_apply_categorization).grid(row=5, column=0, sticky="w", padx=10, pady=2)

        # Recurring Invoices
        ttk.LabelFrame(auto_frame, text="Recurring Invoices").grid(row=6, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.recurring_invoices_enabled = tk.BooleanVar()
        ttk.Checkbutton(auto_frame, text="Enable Recurring Invoices", variable=self.recurring_invoices_enabled).grid(row=7, column=0, sticky="w", padx=10, pady=2)

        self.auto_send_invoices = tk.BooleanVar()
        ttk.Checkbutton(auto_frame, text="Auto-send invoices", variable=self.auto_send_invoices).grid(row=8, column=0, sticky="w", padx=10, pady=2)

    def create_alerts_tab(self):
        """Create alerts configuration tab"""
        alerts_frame = ttk.Frame(self.notebook)
        self.notebook.add(alerts_frame, text="Alerts")

        # Low Balance Alerts
        ttk.LabelFrame(alerts_frame, text="Balance Monitoring").grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.low_balance_enabled = tk.BooleanVar()
        ttk.Checkbutton(alerts_frame, text="Enable Low Balance Alerts", variable=self.low_balance_enabled).grid(row=1, column=0, sticky="w", padx=10, pady=2)

        ttk.Label(alerts_frame, text="Low Balance Threshold ($):").grid(row=2, column=0, sticky="w", padx=10, pady=2)
        self.low_balance_threshold = tk.StringVar()
        ttk.Entry(alerts_frame, textvariable=self.low_balance_threshold, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # Transaction Monitoring
        ttk.LabelFrame(alerts_frame, text="Transaction Monitoring").grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.large_transaction_enabled = tk.BooleanVar()
        ttk.Checkbutton(alerts_frame, text="Enable Large Transaction Alerts", variable=self.large_transaction_enabled).grid(row=4, column=0, sticky="w", padx=10, pady=2)

        ttk.Label(alerts_frame, text="Large Transaction Threshold ($):").grid(row=5, column=0, sticky="w", padx=10, pady=2)
        self.large_transaction_threshold = tk.StringVar()
        ttk.Entry(alerts_frame, textvariable=self.large_transaction_threshold, width=15).grid(row=5, column=1, sticky="w", padx=5, pady=2)

        # Payment Notifications
        self.payment_received_enabled = tk.BooleanVar()
        ttk.Checkbutton(alerts_frame, text="Enable Payment Received Notifications", variable=self.payment_received_enabled).grid(row=6, column=0, sticky="w", padx=10, pady=2)

        ttk.Label(alerts_frame, text="Minimum Payment Amount ($):").grid(row=7, column=0, sticky="w", padx=10, pady=2)
        self.payment_received_minimum = tk.StringVar()
        ttk.Entry(alerts_frame, textvariable=self.payment_received_minimum, width=15).grid(row=7, column=1, sticky="w", padx=5, pady=2)

    def create_schedule_tab(self):
        """Create scheduling configuration tab"""
        schedule_frame = ttk.Frame(self.notebook)
        self.notebook.add(schedule_frame, text="Schedule")

        # Schedule times
        ttk.Label(schedule_frame, text="Payment Reminders Time:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.payment_reminders_time = tk.StringVar()
        ttk.Entry(schedule_frame, textvariable=self.payment_reminders_time, width=10).grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(schedule_frame, text="Expense Categorization Time:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.expense_categorization_time = tk.StringVar()
        ttk.Entry(schedule_frame, textvariable=self.expense_categorization_time, width=10).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(schedule_frame, text="Recurring Invoices Time:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.recurring_invoices_time = tk.StringVar()
        ttk.Entry(schedule_frame, textvariable=self.recurring_invoices_time, width=10).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(schedule_frame, text="Balance Check Frequency:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.balance_checks_frequency = ttk.Combobox(schedule_frame, values=["hourly", "daily", "real-time"], width=10)
        self.balance_checks_frequency.grid(row=3, column=1, sticky="w", padx=5, pady=5)

    def create_advanced_tab(self):
        """Create advanced settings tab"""
        advanced_frame = ttk.Frame(self.notebook)
        self.notebook.add(advanced_frame, text="Advanced")

        # Integration toggles
        ttk.LabelFrame(advanced_frame, text="Integrations").grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.plaid_enabled = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="Plaid Integration", variable=self.plaid_enabled).grid(row=1, column=0, sticky="w", padx=10, pady=2)

        self.stripe_enabled = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="Stripe Integration", variable=self.stripe_enabled).grid(row=2, column=0, sticky="w", padx=10, pady=2)

        self.xero_enabled = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="Xero Integration", variable=self.xero_enabled).grid(row=3, column=0, sticky="w", padx=10, pady=2)

        # Performance settings
        ttk.LabelFrame(advanced_frame, text="Performance").grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        ttk.Label(advanced_frame, text="Batch Size:").grid(row=5, column=0, sticky="w", padx=10, pady=2)
        self.batch_size = tk.StringVar()
        ttk.Entry(advanced_frame, textvariable=self.batch_size, width=10).grid(row=5, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(advanced_frame, text="Rate Limit (req/min):").grid(row=6, column=0, sticky="w", padx=10, pady=2)
        self.rate_limit = tk.StringVar()
        ttk.Entry(advanced_frame, textvariable=self.rate_limit, width=10).grid(row=6, column=1, sticky="w", padx=5, pady=2)

    def create_control_buttons(self):
        """Create control buttons"""
        button_frame = ttk.Frame(self.root)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        ttk.Button(button_frame, text="Save Configuration", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Defaults", command=self.load_defaults).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Validate", command=self.validate_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export", command=self.export_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Import", command=self.import_config).pack(side=tk.LEFT, padx=5)

    def load_current_config(self):
        """Load current configuration into GUI"""
        config = self.manager.config

        # Email settings
        email = config.get("email_settings", {})
        self.smtp_server.set(email.get("smtp_server", ""))
        self.smtp_port.set(str(email.get("smtp_port", 587)))
        self.sender_email.set(email.get("sender_email", ""))
        self.sender_password.set(email.get("sender_password", ""))
        self.use_tls.set(email.get("use_tls", True))

        recipients = email.get("recipients", [])
        self.recipients_text.delete(1.0, tk.END)
        self.recipients_text.insert(1.0, "\n".join(recipients))

        # Automation settings
        self.payment_reminders_enabled.set(config.get("payment_reminders", {}).get("enabled", True))
        self.expense_categorization_enabled.set(config.get("expense_categorization", {}).get("enabled", True))
        self.confidence_threshold.set(str(config.get("expense_categorization", {}).get("confidence_threshold", 0.7)))
        self.auto_apply_categorization.set(config.get("expense_categorization", {}).get("auto_apply", False))
        self.recurring_invoices_enabled.set(config.get("recurring_invoices", {}).get("enabled", True))
        self.auto_send_invoices.set(config.get("recurring_invoices", {}).get("auto_send", False))

        # Alert settings
        alerts = config.get("alerts", {})
        self.low_balance_enabled.set(alerts.get("low_balance_enabled", True))
        self.low_balance_threshold.set(str(alerts.get("low_balance_threshold", 1000)))
        self.large_transaction_enabled.set(alerts.get("large_transaction_enabled", True))
        self.large_transaction_threshold.set(str(alerts.get("large_transaction_threshold", 5000)))
        self.payment_received_enabled.set(alerts.get("payment_received_enabled", True))
        self.payment_received_minimum.set(str(alerts.get("payment_received_minimum", 0)))

        # Schedule settings
        schedule = config.get("automation_schedule", {})
        self.payment_reminders_time.set(schedule.get("payment_reminders", "09:00"))
        self.expense_categorization_time.set(schedule.get("expense_categorization", "10:00"))
        self.recurring_invoices_time.set(schedule.get("recurring_invoices", "08:00"))
        self.balance_checks_frequency.set(schedule.get("balance_checks", "hourly"))

        # Advanced settings
        integrations = config.get("integrations", {})
        self.plaid_enabled.set(integrations.get("plaid_enabled", True))
        self.stripe_enabled.set(integrations.get("stripe_enabled", False))
        self.xero_enabled.set(integrations.get("xero_enabled", False))

        performance = config.get("performance", {})
        self.batch_size.set(str(performance.get("batch_size", 100)))
        self.rate_limit.set(str(performance.get("rate_limit_requests_per_minute", 60)))

    def save_config(self):
        """Save current GUI settings to configuration"""
        try:
            config = self.manager.config.copy()

            # Email settings
            config["email_settings"].update({
                "smtp_server": self.smtp_server.get(),
                "smtp_port": int(self.smtp_port.get()),
                "sender_email": self.sender_email.get(),
                "sender_password": self.sender_password.get(),
                "use_tls": self.use_tls.get(),
                "recipients": [line.strip() for line in self.recipients_text.get(1.0, tk.END).strip().split("\n") if line.strip()]
            })

            # Automation settings
            config["payment_reminders"]["enabled"] = self.payment_reminders_enabled.get()
            config["expense_categorization"]["enabled"] = self.expense_categorization_enabled.get()
            config["expense_categorization"]["confidence_threshold"] = float(self.confidence_threshold.get())
            config["expense_categorization"]["auto_apply"] = self.auto_apply_categorization.get()
            config["recurring_invoices"]["enabled"] = self.recurring_invoices_enabled.get()
            config["recurring_invoices"]["auto_send"] = self.auto_send_invoices.get()

            # Alert settings
            config["alerts"].update({
                "low_balance_enabled": self.low_balance_enabled.get(),
                "low_balance_threshold": float(self.low_balance_threshold.get()),
                "large_transaction_enabled": self.large_transaction_enabled.get(),
                "large_transaction_threshold": float(self.large_transaction_threshold.get()),
                "payment_received_enabled": self.payment_received_enabled.get(),
                "payment_received_minimum": float(self.payment_received_minimum.get())
            })

            # Schedule settings
            config["automation_schedule"].update({
                "payment_reminders": self.payment_reminders_time.get(),
                "expense_categorization": self.expense_categorization_time.get(),
                "recurring_invoices": self.recurring_invoices_time.get(),
                "balance_checks": self.balance_checks_frequency.get()
            })

            # Advanced settings
            config["integrations"].update({
                "plaid_enabled": self.plaid_enabled.get(),
                "stripe_enabled": self.stripe_enabled.get(),
                "xero_enabled": self.xero_enabled.get()
            })

            config["performance"].update({
                "batch_size": int(self.batch_size.get()),
                "rate_limit_requests_per_minute": int(self.rate_limit.get())
            })

            if self.manager.save_config(config):
                messagebox.showinfo("Success", "Configuration saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save configuration")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving configuration: {str(e)}")

    def validate_config(self):
        """Validate current configuration"""
        try:
            # Create temporary config from GUI
            temp_config = self.manager.config.copy()
            # Update with current GUI values (simplified)
            errors = self.manager.validate_config(temp_config)

            if errors:
                error_msg = "Configuration validation errors:\n\n" + "\n".join(f"• {error}" for error in errors)
                messagebox.showerror("Validation Errors", error_msg)
            else:
                messagebox.showinfo("Validation Success", "Configuration is valid!")

        except Exception as e:
            messagebox.showerror("Error", f"Error validating configuration: {str(e)}")

    def load_defaults(self):
        """Load default configuration"""
        if messagebox.askyesno("Confirm", "This will reset all settings to defaults. Continue?"):
            self.manager.config = self.manager.default_config.copy()
            self.load_current_config()

    def export_config(self):
        """Export configuration to file"""
        filename = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.manager.config, f, indent=2)
                messagebox.showinfo("Success", f"Configuration exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting configuration: {str(e)}")

    def import_config(self):
        """Import configuration from file"""
        filename = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    imported_config = json.load(f)

                errors = self.manager.validate_config(imported_config)
                if errors:
                    error_msg = "Imported configuration has errors:\n\n" + "\n".join(f"• {error}" for error in errors)
                    if not messagebox.askyesno("Import Warning", error_msg + "\n\nImport anyway?"):
                        return

                self.manager.config = imported_config
                self.load_current_config()
                messagebox.showinfo("Success", "Configuration imported successfully!")

            except Exception as e:
                messagebox.showerror("Error", f"Error importing configuration: {str(e)}")

    def run(self):
        """Run the GUI"""
        self.root.mainloop()

# CLI interface
def cli_interface():
    """Command line interface for configuration management"""
    import argparse

    parser = argparse.ArgumentParser(description="Financial Automation Configuration Manager")
    parser.add_argument("--gui", action="store_true", help="Launch GUI interface")
    parser.add_argument("--export", help="Export configuration to file")
    parser.add_argument("--import", dest="import_file", help="Import configuration from file")
    parser.add_argument("--validate", action="store_true", help="Validate current configuration")
    parser.add_argument("--summary", action="store_true", help="Show configuration summary")
    parser.add_argument("--reset", action="store_true", help="Reset to default configuration")

    args = parser.parse_args()

    manager = AutomationConfigManager()

    if args.gui:
        gui = AutomationConfigGUI()
        gui.run()
    elif args.export:
        with open(args.export, 'w') as f:
            json.dump(manager.config, f, indent=2)
        print(f"Configuration exported to {args.export}")
    elif args.import_file:
        with open(args.import_file, 'r') as f:
            imported_config = json.load(f)
        errors = manager.validate_config(imported_config)
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  • {error}")
        if not errors or input("Import anyway? (y/N): ").lower() == 'y':
            manager.save_config(imported_config)
            print("Configuration imported successfully")
    elif args.validate:
        errors = manager.validate_config()
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  • {error}")
        else:
            print("Configuration is valid")
    elif args.summary:
        summary = manager.get_config_summary()
        print("Configuration Summary:")
        print(json.dumps(summary, indent=2))
    elif args.reset:
        if input("Reset to default configuration? (y/N): ").lower() == 'y':
            manager.save_config(manager.default_config)
            print("Configuration reset to defaults")
    else:
        parser.print_help()

if __name__ == "__main__":
    cli_interface()