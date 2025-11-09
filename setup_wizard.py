"""
Professional Setup Wizard for Financial Command Center
Handles secure configuration storage and API validation
"""

import os
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
import hashlib
import logging
import threading

# -----------------------------------------------------------------------------
# In-memory credential staging for setup wizard flows
# -----------------------------------------------------------------------------

_staged_credentials_lock = threading.Lock()
_staged_credentials: Dict[str, Dict[str, str]] = {}


def _normalize_service_name(service: Optional[str]) -> str:
    return (service or '').strip().lower()


def stage_service_credentials(service: str, credentials: Dict[str, Any]) -> Dict[str, str]:
    """Stage credentials for a service so other setup steps can use them immediately."""
    normalized = _normalize_service_name(service)
    if not normalized:
        return {}

    sanitized: Dict[str, str] = {}
    for key, value in (credentials or {}).items():
        if value is None:
            continue
        sanitized[key] = str(value)

    with _staged_credentials_lock:
        if sanitized:
            _staged_credentials[normalized] = sanitized
        else:
            _staged_credentials.pop(normalized, None)

    return sanitized.copy()


def get_staged_credentials(service: str) -> Dict[str, str]:
    """Get staged credentials for a service, if any."""
    normalized = _normalize_service_name(service)
    if not normalized:
        return {}

    with _staged_credentials_lock:
        data = _staged_credentials.get(normalized, {})
        return data.copy()


def clear_staged_credentials(service: Optional[str] = None) -> None:
    """Clear staged credentials for a service or all services."""
    with _staged_credentials_lock:
        if service is None:
            _staged_credentials.clear()
            return

        normalized = _normalize_service_name(service)
        if normalized:
            _staged_credentials.pop(normalized, None)


class ConfigurationManager:
    """Secure configuration manager for API credentials"""
    
    def __init__(self, config_dir: str = "secure_config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Configuration files
        self.master_key_file = self.config_dir / "master.key"
        self.config_file = self.config_dir / "config.enc"
        self.metadata_file = self.config_dir / "metadata.json"
        
        # Initialize encryption
        self._initialize_encryption()
        
    def _initialize_encryption(self):
        """Initialize or load encryption key"""
        if self.master_key_file.exists():
            # Load existing key
            with open(self.master_key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            # Generate new key
            self.encryption_key = Fernet.generate_key()
            with open(self.master_key_file, 'wb') as f:
                f.write(self.encryption_key)
            
            # Secure the key file (Windows)
            try:
                os.chmod(self.master_key_file, 0o600)
            except:
                pass  # Best effort on Windows
                
        self.cipher = Fernet(self.encryption_key)
        
    def encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """Encrypt configuration data"""
        json_data = json.dumps(data).encode()
        return self.cipher.encrypt(json_data)
        
    def decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt configuration data"""
        decrypted_json = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted_json.decode())
        
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save encrypted configuration to file"""
        try:
            # Add metadata
            config['_metadata'] = {
                'created_at': datetime.now().isoformat(),
                'version': '1.0',
                'encrypted': True
            }
            
            # Encrypt and save
            encrypted_data = self.encrypt_data(config)
            with open(self.config_file, 'wb') as f:
                f.write(encrypted_data)
                f.flush()  # Force write to disk
                os.fsync(f.fileno())  # Ensure data is written to disk

            # Save metadata separately (unencrypted for info)
            metadata = {
                'last_updated': datetime.now().isoformat(),
                'services_configured': list(config.keys()),
                'config_version': '1.0'
            }

            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                f.flush()  # Force write to disk
                os.fsync(f.fileno())  # Ensure data is written to disk
                
            return True
            
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
            
    def load_config(self) -> Optional[Dict[str, Any]]:
        """Load and decrypt configuration"""
        try:
            if not self.config_file.exists():
                return None
                
            with open(self.config_file, 'rb') as f:
                encrypted_data = f.read()
                
            return self.decrypt_data(encrypted_data)
            
        except Exception as e:
            print(f"Error loading config: {e}")
            return None
            
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific service"""
        config = self.load_config()
        return config.get(service_name) if config else None
        
    def is_service_configured(self, service_name: str) -> bool:
        """Check if a service is configured"""
        service_config = self.get_service_config(service_name)
        if not service_config:
            return False
            
        # Check if skipped or has actual credentials
        return not service_config.get('skipped', False) and bool(service_config)
        
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get overall configuration status"""
        config = self.load_config()
        if not config:
            return {
                'configured': False,
                'services': {},
                'last_updated': None
            }
            
        # Check metadata
        metadata = {}
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
                
        services = {}
        for service in ['stripe', 'xero', 'plaid']:
            service_config = config.get(service, {})
            skipped = service_config.get('skipped', False)
            has_credentials = bool(service_config) and not skipped
            configured = has_credentials and bool(service_config.get('configured_at'))
            services[service] = {
                'configured': configured,
                'skipped': skipped,
                'has_credentials': has_credentials,
                'configured_at': service_config.get('configured_at')
            }
        
        overall_configured = all(
            data.get('configured') or data.get('skipped')
            for data in services.values()
        )
            
        return {
            'configured': overall_configured,
            'services': services,
            'last_updated': metadata.get('last_updated'),
            'config_version': metadata.get('config_version')
        }


class APIValidator:
    """Validates API connections for different services"""
    
    @staticmethod
    def validate_stripe_credentials(api_key: str, publishable_key: str = None) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate Stripe API credentials"""
        stripe = None
        try:
            import stripe
            
            # Set the API key
            stripe.api_key = api_key
            
            # Test the connection by retrieving account info
            account = stripe.Account.retrieve()
            
            # Additional validation for publishable key if provided
            publishable_valid = True
            if publishable_key:
                # Basic format validation
                if not (publishable_key.startswith('pk_test_') or publishable_key.startswith('pk_live_')):
                    publishable_valid = False
                    
                # Check if key types match (test vs live)
                is_test_secret = api_key.startswith('sk_test_')
                is_test_publishable = publishable_key.startswith('pk_test_')
                
                if is_test_secret != is_test_publishable:
                    return False, "Mismatch between test/live keys", {}
            
            if not publishable_valid:
                return False, "Invalid publishable key format", {}
                
            return True, "Connection successful", {
                'account_id': account.id,
                'account_name': account.business_profile.name if account.business_profile else None,
                'country': account.country,
                'currency': account.default_currency,
                'type': account.type
            }
            
        except ImportError:
            return False, "Stripe library not installed", {}
        except Exception as e:
            # Handle Stripe-specific errors if stripe was imported successfully
            if stripe is not None:
                try:
                    if hasattr(stripe, 'error'):
                        if isinstance(e, stripe.error.AuthenticationError):
                            return False, "Invalid API key", {}
                        elif isinstance(e, stripe.error.InvalidRequestError):
                            return False, f"Invalid request: {str(e)}", {}
                except:
                    pass
            return False, f"Connection failed: {str(e)}", {}
    
    @staticmethod 
    def validate_xero_credentials(client_id: str, client_secret: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate Xero OAuth credentials"""
        try:
            # Basic format validation
            if not client_id or not client_secret:
                return False, "Client ID and Secret are required", {}
                
            if len(client_id) < 30:  # Xero client IDs are typically longer
                return False, "Invalid Client ID format", {}
                
            if len(client_secret) < 40:  # Xero client secrets are typically longer
                return False, "Invalid Client Secret format", {}
                
            # For Xero, we can only validate format and basic structure
            # Full validation requires OAuth flow with user consent
            return True, "Configuration validated (OAuth flow required for full connection)", {
                'client_id': client_id[:8] + "...",  # Masked for security
                'validation': 'format_check',
                'note': 'Full validation requires user OAuth consent'
            }
            
        except Exception as e:
            return False, f"Validation failed: {str(e)}", {}
    
    @staticmethod
    def validate_plaid_credentials(client_id: str, secret: str, environment: str = "sandbox") -> Tuple[bool, str, Dict[str, Any]]:
        """Validate Plaid API credentials"""
        try:
            import plaid
            from plaid.api import plaid_api
            from plaid.model.accounts_get_request import AccountsGetRequest
            
            # Basic format validation
            if not client_id or not secret:
                return False, "Client ID and Secret are required", {}
                
            if len(client_id) < 20:  # Plaid client IDs are typically longer
                return False, "Invalid Client ID format", {}
                
            if len(secret) < 30:  # Plaid secrets are typically longer
                return False, "Invalid Secret format", {}
            
            # Validate environment
            valid_envs = ['sandbox', 'development', 'production']
            if environment.lower() not in valid_envs:
                return False, f"Environment must be one of: {', '.join(valid_envs)}", {}
            
            # Set up Plaid client
            env_map = {
                'sandbox': getattr(plaid.Environment, 'Sandbox', plaid.Environment.Production),
                'development': getattr(plaid.Environment, 'Development', plaid.Environment.Sandbox),
                'production': getattr(plaid.Environment, 'Production', plaid.Environment.Sandbox)
            }
            
            host = env_map.get(environment.lower(), plaid.Environment.Sandbox)
            
            configuration = plaid.Configuration(
                host=host,
                api_key={
                    'clientId': client_id,
                    'secret': secret
                }
            )
            
            api_client = plaid.ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)
            
            # Test connection - we can't test with real accounts without tokens,
            # but we can test if credentials are valid format and environment is reachable
            # For now, we'll do basic validation
            
            return True, f"Configuration validated for {environment} environment", {
                'client_id': client_id[:8] + "...",  # Masked for security
                'environment': environment,
                'validation': 'format_check',
                'note': 'Full validation requires account linking'
            }
            
        except ImportError:
            return False, "Plaid library not installed", {}
        except Exception as e:
            return False, f"Validation failed: {str(e)}", {}


class SetupWizardAPI:
    """Flask API endpoints for the setup wizard"""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.api_validator = APIValidator()
        
    def test_stripe_connection(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test Stripe API connection"""
        try:
            api_key = request_data.get('stripe_api_key', '').strip()
            publishable_key = request_data.get('stripe_publishable_key', '').strip()
            
            if not api_key:
                return {
                    'success': False,
                    'error': 'Stripe API key is required'
                }
                
            # Validate credentials
            success, message, details = self.api_validator.validate_stripe_credentials(
                api_key, publishable_key or None
            )
            
            if success:
                return {
                    'success': True,
                    'message': message,
                    'account_name': details.get('account_name'),
                    'account_country': details.get('country'),
                    'account_currency': details.get('currency'),
                    'account_type': details.get('type')
                }
            else:
                return {
                    'success': False,
                    'error': message
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def test_plaid_connection(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test Plaid API connection"""
        try:
            client_id = request_data.get('plaid_client_id', '').strip()
            secret = request_data.get('plaid_secret', '').strip()
            environment = request_data.get('plaid_environment', 'sandbox').strip().lower()
            
            if not client_id or not secret:
                return {
                    'success': False,
                    'error': 'Plaid Client ID and Secret are required'
                }
            
            # Validate credentials
            success, message, details = self.api_validator.validate_plaid_credentials(
                client_id, secret, environment
            )
            
            if success:
                return {
                    'success': True,
                    'message': message,
                    'client_id_preview': details.get('client_id'),
                    'environment': details.get('environment'),
                    'validation_type': details.get('validation'),
                    'note': details.get('note')
                }
            else:
                return {
                    'success': False,
                    'error': message
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
            
    def test_xero_connection(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test Xero OAuth configuration"""
        try:
            client_id = request_data.get('xero_client_id', '').strip()
            client_secret = request_data.get('xero_client_secret', '').strip()
            
            if not client_id or not client_secret:
                stage_service_credentials('xero', {})
                return {
                    'success': False,
                    'error': 'Both Client ID and Client Secret are required'
                }
                
            # Validate credentials
            success, message, details = self.api_validator.validate_xero_credentials(
                client_id, client_secret
            )
            
            if success:
                stage_service_credentials('xero', {
                    'client_id': client_id,
                    'client_secret': client_secret,
                })
                return {
                    'success': True,
                    'message': message,
                    'client_id_preview': details.get('client_id'),
                    'validation_type': details.get('validation'),
                    'note': details.get('note')
                }
            else:
                stage_service_credentials('xero', {})
                return {
                    'success': False,
                    'error': message
                }
                
        except Exception as e:
            stage_service_credentials('xero', {})
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
            
    def save_configuration(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save the complete configuration"""
        try:
            existing_config = self.config_manager.load_config() or {}
            config = {
                key: value for key, value in existing_config.items()
                if isinstance(value, dict) and not key.startswith('_')
            }
            
            # Process Stripe configuration
            stripe_config = request_data.get('stripe', {})
            if stripe_config.get('skipped'):
                config['stripe'] = {'skipped': True}
            elif 'api_key' in stripe_config:
                merged = dict(config.get('stripe', {}))
                merged.update({
                    'api_key': stripe_config['api_key'],
                    'publishable_key': stripe_config.get('publishable_key', ''),
                    'configured_at': datetime.now().isoformat()
                })
                merged.pop('skipped', None)
                config['stripe'] = merged
                
            # Process Xero configuration  
            xero_config = request_data.get('xero', {})
            if xero_config.get('skipped'):
                config['xero'] = {'skipped': True}
            elif 'client_id' in xero_config:
                merged = dict(config.get('xero', {}))
                merged.update({
                    'client_id': xero_config['client_id'],
                    'client_secret': xero_config['client_secret'],
                    'configured_at': datetime.now().isoformat()
                })
                merged.pop('skipped', None)
                config['xero'] = merged
            
            # Process Plaid configuration
            plaid_config = request_data.get('plaid', {})
            if plaid_config.get('skipped'):
                config['plaid'] = {'skipped': True}
            elif 'client_id' in plaid_config:
                merged = dict(config.get('plaid', {}))
                merged.update({
                    'client_id': plaid_config['client_id'],
                    'secret': plaid_config['secret'],
                    'environment': plaid_config.get('environment', 'sandbox'),
                    'configured_at': datetime.now().isoformat()
                })
                merged.pop('skipped', None)
                config['plaid'] = merged
                
            # Save encrypted configuration
            success = self.config_manager.save_config(config)
            
            if success:
                clear_staged_credentials('xero')
                configured_services = [
                    name for name, data in config.items()
                    if isinstance(data, dict)
                    and not data.get('skipped', False)
                    and data.get('configured_at')
                ]
                skipped_services = [
                    name for name, data in config.items()
                    if isinstance(data, dict) and data.get('skipped', False)
                ]
                return {
                    'success': True,
                    'message': 'Configuration saved successfully',
                    'services_configured': len(configured_services),
                    'services_skipped': len(skipped_services),
                    'redirect_url': '/health'  # Redirect to health check after successful setup
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to save configuration'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Configuration save failed: {str(e)}'
            }
            
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get current configuration status"""
        try:
            status = self.config_manager.get_configuration_status()
            return {
                'success': True,
                'status': status
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get status: {str(e)}'
            }


# Helper functions for app integration


# -----------------------------------------------------------------------------
# Environment helpers
# -----------------------------------------------------------------------------

def sync_credentials_to_env(env: Dict[str, str] | None = None) -> Dict[str, str]:
    """Load stored Stripe/Xero/Plaid credentials and apply them to *env*."""
    logger = logging.getLogger(__name__)
    target_env = env if env is not None else os.environ
    try:
        config_manager = ConfigurationManager()
        config = config_manager.load_config() or {}
    except Exception as exc:
        logger.warning(f"Unable to sync setup credentials to environment: {exc}")
        return {}

    env_updates: Dict[str, str] = {}

    def _store(key: str, value: Any) -> None:
        if value is None:
            return
        env_updates[key] = str(value)

    stripe_cfg = config.get('stripe')
    if isinstance(stripe_cfg, dict) and not stripe_cfg.get('skipped'):
        _store('STRIPE_API_KEY', stripe_cfg.get('api_key'))
        _store('STRIPE_CLIENT_ID', stripe_cfg.get('client_id'))
        _store('STRIPE_CLIENT_SECRET', stripe_cfg.get('client_secret') or stripe_cfg.get('api_key'))
        _store('STRIPE_REDIRECT_URI', stripe_cfg.get('redirect_uri'))
        if stripe_cfg.get('publishable_key'):
            _store('STRIPE_PUBLISHABLE_KEY', stripe_cfg.get('publishable_key'))

    xero_cfg = config.get('xero')
    if isinstance(xero_cfg, dict) and not xero_cfg.get('skipped'):
        _store('XERO_CLIENT_ID', xero_cfg.get('client_id'))
        _store('XERO_CLIENT_SECRET', xero_cfg.get('client_secret'))
        _store('XERO_REDIRECT_URI', xero_cfg.get('redirect_uri'))
        _store('XERO_SCOPE', xero_cfg.get('scope'))

    plaid_cfg = config.get('plaid')
    if isinstance(plaid_cfg, dict) and not plaid_cfg.get('skipped'):
        _store('PLAID_CLIENT_ID', plaid_cfg.get('client_id'))
        _store('PLAID_SECRET', plaid_cfg.get('secret'))
        _store('PLAID_ENV', plaid_cfg.get('environment', 'sandbox'))
        _store('PLAID_REDIRECT_URI', plaid_cfg.get('redirect_uri'))

    for key, value in env_updates.items():
        target_env[key] = value

    if env_updates:
        logger.info("Setup credentials synced for keys: %s", ", ".join(sorted(env_updates)))

    return env_updates


def get_configured_credentials() -> Dict[str, str]:
    """Get configured credentials from secure storage or environment variables"""
    # Try to load from secure configuration first
    config_manager = ConfigurationManager()
    config = config_manager.load_config()
    
    if config:
        credentials = {}
        # Copy credentials from secure config
        if 'stripe' in config and isinstance(config['stripe'], dict) and not config['stripe'].get('skipped', False):
            stripe_cfg = config['stripe']
            credentials['STRIPE_API_KEY'] = stripe_cfg.get('api_key', '')
            credentials['STRIPE_CLIENT_ID'] = stripe_cfg.get('client_id', '')
            credentials['STRIPE_CLIENT_SECRET'] = stripe_cfg.get('client_secret', stripe_cfg.get('api_key', ''))
            credentials['STRIPE_REDIRECT_URI'] = stripe_cfg.get('redirect_uri', '')
            credentials['STRIPE_PUBLISHABLE_KEY'] = stripe_cfg.get('publishable_key', '')
        if 'xero' in config and isinstance(config['xero'], dict) and not config['xero'].get('skipped', False):
            xero_cfg = config['xero']
            credentials['XERO_CLIENT_ID'] = xero_cfg.get('client_id', '')
            credentials['XERO_CLIENT_SECRET'] = xero_cfg.get('client_secret', '')
            credentials['XERO_REDIRECT_URI'] = xero_cfg.get('redirect_uri', '')
            credentials['XERO_SCOPE'] = xero_cfg.get('scope', '')
        if 'plaid' in config and isinstance(config['plaid'], dict) and not config['plaid'].get('skipped', False):
            plaid_cfg = config['plaid']
            credentials['PLAID_CLIENT_ID'] = plaid_cfg.get('client_id', '')
            credentials['PLAID_SECRET'] = plaid_cfg.get('secret', '')
            credentials['PLAID_REDIRECT_URI'] = plaid_cfg.get('redirect_uri', '')
            credentials['PLAID_ENV'] = plaid_cfg.get('environment', 'sandbox')
        return _apply_env_overrides(credentials)
    
    # Fall back to environment variables (for backward compatibility)
    return _apply_env_overrides({
        'STRIPE_API_KEY': os.getenv('STRIPE_API_KEY', ''),
        'STRIPE_CLIENT_ID': os.getenv('STRIPE_CLIENT_ID', ''),
        'STRIPE_CLIENT_SECRET': os.getenv('STRIPE_CLIENT_SECRET', ''),
        'STRIPE_REDIRECT_URI': os.getenv('STRIPE_REDIRECT_URI', ''),
        'STRIPE_PUBLISHABLE_KEY': os.getenv('STRIPE_PUBLISHABLE_KEY', ''),
        'XERO_CLIENT_ID': os.getenv('XERO_CLIENT_ID', ''),
        'XERO_CLIENT_SECRET': os.getenv('XERO_CLIENT_SECRET', ''),
        'XERO_REDIRECT_URI': os.getenv('XERO_REDIRECT_URI', ''),
        'XERO_SCOPE': os.getenv('XERO_SCOPE', ''),
        'PLAID_CLIENT_ID': os.getenv('PLAID_CLIENT_ID', ''),
        'PLAID_SECRET': os.getenv('PLAID_SECRET', ''),
        'PLAID_REDIRECT_URI': os.getenv('PLAID_REDIRECT_URI', ''),
        'PLAID_ENV': os.getenv('PLAID_ENV', 'sandbox')
    })


def _apply_env_overrides(credentials: Dict[str, str]) -> Dict[str, str]:
    """Ensure environment variables always override secure config for each service."""
    env_map = {
        'STRIPE_API_KEY': 'STRIPE_API_KEY',
        'STRIPE_CLIENT_ID': 'STRIPE_CLIENT_ID',
        'STRIPE_CLIENT_SECRET': 'STRIPE_CLIENT_SECRET',
        'STRIPE_REDIRECT_URI': 'STRIPE_REDIRECT_URI',
        'STRIPE_PUBLISHABLE_KEY': 'STRIPE_PUBLISHABLE_KEY',
        'XERO_CLIENT_ID': 'XERO_CLIENT_ID',
        'XERO_CLIENT_SECRET': 'XERO_CLIENT_SECRET',
        'XERO_REDIRECT_URI': 'XERO_REDIRECT_URI',
        'XERO_SCOPE': 'XERO_SCOPE',
        'PLAID_CLIENT_ID': 'PLAID_CLIENT_ID',
        'PLAID_SECRET': 'PLAID_SECRET',
        'PLAID_REDIRECT_URI': 'PLAID_REDIRECT_URI',
        'PLAID_ENV': 'PLAID_ENV',
    }
    for key, env_key in env_map.items():
        value = os.getenv(env_key)
        if value:
            credentials[key] = value
    return credentials


def is_setup_required() -> bool:
    """Check if setup wizard should be shown"""
    try:
        config_manager = ConfigurationManager()
        status = config_manager.get_configuration_status()
        return not status['configured']
    except:
        return True


def get_integration_status() -> Dict[str, Dict[str, Any]]:
    """Get detailed status of all integrations"""
    try:
        config_manager = ConfigurationManager()
        status = config_manager.get_configuration_status()
        return status.get('services', {})
    except:
        return {
            'stripe': {'configured': False, 'skipped': False, 'has_credentials': False},
            'xero': {'configured': False, 'skipped': False, 'has_credentials': False},
            'plaid': {'configured': False, 'skipped': False, 'has_credentials': False}
        }


def upsert_service_configuration(service: str, updates: Dict[str, Any], *, mark_configured: bool = False) -> Dict[str, Any]:
    """Merge updates into a service configuration and persist to secure storage."""
    config_manager = ConfigurationManager()
    config = config_manager.load_config() or {}
    existing = dict(config.get(service, {}))

    for key, value in (updates or {}).items():
        if value is not None:
            existing[key] = value

    if mark_configured:
        existing.pop('skipped', None)
        existing['configured_at'] = existing.get('configured_at') or datetime.now().isoformat()

    config[service] = existing
    config_manager.save_config(config)
    return existing


if __name__ == "__main__":
    # Test the configuration manager
    print("🔧 Testing Configuration Manager...")
    
    config_manager = ConfigurationManager()
    
    # Test encryption/decryption
    test_config = {
        'stripe': {
            'api_key': 'sk_test_example',
            'publishable_key': 'pk_test_example'
        },
        'xero': {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret'
        }
    }
    
    # Save config
    success = config_manager.save_config(test_config)
    print(f"Save config: {'✅ Success' if success else '❌ Failed'}")
    
    # Load config
    loaded_config = config_manager.load_config()
    print(f"Load config: {'✅ Success' if loaded_config else '❌ Failed'}")
    
    # Get status
    status = config_manager.get_configuration_status()
    print(f"Configuration status: {json.dumps(status, indent=2)}")
    
    print("🔧 Configuration Manager test complete!")
