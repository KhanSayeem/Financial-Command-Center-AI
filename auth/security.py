# auth/security.py - Security module for Financial Command Center
import os
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Dict, Optional
from cryptography.fernet import Fernet

class SecurityManager:
    def __init__(self):
        # Use Windows-friendly paths
        self.auth_file = Path("auth") / "api_keys.json"
        self.rate_limit_file = Path("auth") / "rate_limits.json"
        self.audit_file = Path("audit") / "security_audit.json"
        
        # Ensure directories exist
        self.auth_file.parent.mkdir(exist_ok=True)
        self.audit_file.parent.mkdir(exist_ok=True)
        
        self.cipher_suite = self._get_or_create_encryption_key()
        self._ensure_files_exist()
    
    def _get_or_create_encryption_key(self):
        """Get or create encryption key"""
        key_file = Path("auth") / "encryption.key"
        
        try:
            with open(key_file, 'rb') as f:
                key = f.read()
        except FileNotFoundError:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            print("New encryption key generated")
        return Fernet(key)
    
    def _ensure_files_exist(self):
        """Ensure required JSON files exist"""
        for file_path in [self.auth_file, self.rate_limit_file, self.audit_file]:
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump({}, f)
    
    def _load_json(self, file_path: Path) -> dict:
        """Safely load JSON file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_json(self, file_path: Path, data: dict):
        """Safely save JSON file"""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data like API keys"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def generate_api_key(self, client_name: str, permissions: list = None) -> str:
        """Generate secure API key for clients"""
        api_key = f"fc_{secrets.token_urlsafe(32)}"
        
        # Load existing keys
        api_keys = self._load_json(self.auth_file)
        
        # Store new key
        api_keys[api_key] = {
            "client_name": client_name,
            "permissions": permissions or ["read", "write"],
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "active": True,
            "daily_limit": 1000,
            "monthly_limit": 30000
        }
        
        self._save_json(self.auth_file, api_keys)
        
        # Log creation
        self.log_security_event("api_key_created", client_name, {"api_key": api_key[:10] + "..."})
        
        print(f"API key generated for {client_name}: {api_key}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[dict]:
        """Validate API key and return client info"""
        api_keys = self._load_json(self.auth_file)
        
        if api_key not in api_keys:
            self.log_security_event("invalid_api_key", "unknown", {"api_key": api_key[:10] + "..."})
            return None
        
        key_info = api_keys[api_key]
        
        if not key_info.get("active", False):
            self.log_security_event("inactive_api_key", key_info["client_name"], {"api_key": api_key[:10] + "..."})
            return None
        
        # Update last used
        key_info["last_used"] = datetime.now().isoformat()
        api_keys[api_key] = key_info
        self._save_json(self.auth_file, api_keys)
        
        return key_info
    
    def check_rate_limit(self, api_key: str, operation: str = "general") -> bool:
        """Check if API key is within rate limits"""
        rate_limits = self._load_json(self.rate_limit_file)
        
        today = datetime.now().strftime("%Y-%m-%d")
        hour = datetime.now().strftime("%Y-%m-%d-%H")
        
        key_limits = rate_limits.get(api_key, {})
        
        # Check hourly limit (100 requests)
        hourly_count = key_limits.get("hourly", {}).get(hour, 0)
        if hourly_count >= 100:
            self.log_security_event("rate_limit_exceeded", api_key, {"period": "hourly", "count": hourly_count})
            return False
        
        # Check daily limit (1000 requests)
        daily_count = key_limits.get("daily", {}).get(today, 0)
        if daily_count >= 1000:
            self.log_security_event("rate_limit_exceeded", api_key, {"period": "daily", "count": daily_count})
            return False
        
        # Update counters
        if api_key not in rate_limits:
            rate_limits[api_key] = {"hourly": {}, "daily": {}}
        
        rate_limits[api_key]["hourly"][hour] = hourly_count + 1
        rate_limits[api_key]["daily"][today] = daily_count + 1
        
        # Clean old entries (keep only last 7 days)
        self._cleanup_old_rate_limits(rate_limits)
        
        self._save_json(self.rate_limit_file, rate_limits)
        return True
    
    def _cleanup_old_rate_limits(self, rate_limits: dict):
        """Remove rate limit entries older than 7 days"""
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for api_key in rate_limits:
            # Clean daily entries
            daily_entries = rate_limits[api_key].get("daily", {})
            for date_str in list(daily_entries.keys()):
                try:
                    entry_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if entry_date < cutoff_date:
                        del daily_entries[date_str]
                except ValueError:
                    continue
            
            # Clean hourly entries (keep only last 24 hours)
            hourly_entries = rate_limits[api_key].get("hourly", {})
            cutoff_hour = datetime.now() - timedelta(hours=24)
            for hour_str in list(hourly_entries.keys()):
                try:
                    entry_hour = datetime.strptime(hour_str, "%Y-%m-%d-%H")
                    if entry_hour < cutoff_hour:
                        del hourly_entries[hour_str]
                except ValueError:
                    continue
    
    def log_security_event(self, event_type: str, client_name: str, details: dict):
        """Log security events for audit"""
        audit_log = self._load_json(self.audit_file)
        
        event_id = secrets.token_hex(8)
        timestamp = datetime.now().isoformat()
        
        if "events" not in audit_log:
            audit_log["events"] = []
        
        audit_log["events"].append({
            "event_id": event_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "client_name": client_name,
            "details": details
        })
        
        # Keep only last 1000 events
        if len(audit_log["events"]) > 1000:
            audit_log["events"] = audit_log["events"][-1000:]
        
        self._save_json(self.audit_file, audit_log)
    
    def get_client_stats(self, api_key: str) -> dict:
        """Get usage statistics for a client"""
        rate_limits = self._load_json(self.rate_limit_file)
        api_keys = self._load_json(self.auth_file)
        
        if api_key not in api_keys:
            return {"error": "API key not found"}
        
        client_info = api_keys[api_key]
        usage = rate_limits.get(api_key, {"daily": {}, "hourly": {}})
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_usage = usage["daily"].get(today, 0)
        
        return {
            "client_name": client_info["client_name"],
            "created_at": client_info["created_at"],
            "last_used": client_info["last_used"],
            "daily_usage": today_usage,
            "daily_limit": client_info.get("daily_limit", 1000),
            "remaining_today": client_info.get("daily_limit", 1000) - today_usage,
            "permissions": client_info.get("permissions", [])
        }

def require_api_key(f):
    """Decorator to require API key authentication with helpful guidance."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify, url_for

        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if not api_key:
            # Provide actionable guidance to obtain a key
            help_payload = {
                'error': 'API key required',
                'code': 'AUTH_REQUIRED',
                'header': 'X-API-Key: <your_key>',
                'create_demo_key_url': '/admin/create-demo-key',
                'how_to_fix': [
                    'Visit /admin/create-demo-key to generate a demo key',
                    'Send header X-API-Key with that value',
                ],
                'examples': {
                    'curl': 'curl -H "X-API-Key: YOUR_KEY" https://127.0.0.1:8000/health',
                    'browser': 'https://127.0.0.1:8000/health?api_key=YOUR_KEY'
                }
            }
            try:
                help_payload['dashboard'] = url_for('admin_dashboard')
            except Exception:
                pass
            return jsonify(help_payload), 401

        security = SecurityManager()
        client_info = security.validate_api_key(api_key)

        if not client_info:
            return jsonify({
                'error': 'Invalid API key',
                'code': 'AUTH_INVALID',
                'create_demo_key_url': '/admin/create-demo-key'
            }), 401

        # Check rate limits
        if not security.check_rate_limit(api_key):
            return jsonify({
                'error': 'Rate limit exceeded',
                'code': 'RATE_LIMIT_EXCEEDED',
                'retry_after': 3600
            }), 429

        # Add client info to request context
        request.client_info = client_info
        request.api_key = api_key

        return f(*args, **kwargs)
    return decorated_function

def log_transaction(operation: str, amount: float, currency: str, status: str):
    """Log financial transactions for audit"""
    from flask import request
    
    security = SecurityManager()
    client_name = getattr(request, 'client_info', {}).get('client_name', 'unknown')
    
    security.log_security_event("financial_transaction", client_name, {
        "operation": operation,
        "amount": amount,
        "currency": currency,
        "status": status,
        "timestamp": datetime.now().isoformat()
    })

# CLI utility functions
def create_demo_api_key():
    """Create a demo API key for testing"""
    security = SecurityManager()
    demo_key = security.generate_api_key("Demo Client", ["read", "write", "admin"])
    
    print(f"""
Demo API key created!
Client: Demo Client
API Key: {demo_key}

Test it with:
curl -H "X-API-Key: {demo_key}" https://127.0.0.1:8000/api/ping

Save this key - you'll need it for testing!
""")
    return demo_key

if __name__ == "__main__":
    # Create demo API key when run directly
    create_demo_api_key()
