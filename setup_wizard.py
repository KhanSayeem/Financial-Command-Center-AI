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
                
            # Save metadata separately (unencrypted for info)
            metadata = {
                'last_updated': datetime.now().isoformat(),
                'services_configured': list(config.keys()),
                'config_version': '1.0'
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
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
        for service in ['stripe', 'xero']:
            service_config = config.get(service, {})
            services[service] = {
                'configured': not service_config.get('skipped', False) and bool(service_config),
                'skipped': service_config.get('skipped', False),
                'has_credentials': bool(service_config and not service_config.get('skipped', False))
            }
            
        return {
            'configured': True,
            'services': services,
            'last_updated': metadata.get('last_updated'),
            'config_version': metadata.get('config_version')
        }


class APIValidator:
    """Validates API connections for different services"""
    
    @staticmethod
    def validate_stripe_credentials(api_key: str, publishable_key: str = None) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate Stripe API credentials"""
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
            
        except stripe.error.AuthenticationError:
            return False, "Invalid API key", {}
        except stripe.error.InvalidRequestError as e:
            return False, f"Invalid request: {str(e)}", {}
        except Exception as e:
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
            
    def test_xero_connection(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test Xero OAuth configuration"""
        try:
            client_id = request_data.get('xero_client_id', '').strip()
            client_secret = request_data.get('xero_client_secret', '').strip()
            
            if not client_id or not client_secret:
                return {
                    'success': False,
                    'error': 'Both Client ID and Client Secret are required'
                }
                
            # Validate credentials
            success, message, details = self.api_validator.validate_xero_credentials(
                client_id, client_secret
            )
            
            if success:
                return {
                    'success': True,
                    'message': message,
                    'client_id_preview': details.get('client_id'),
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
            
    def save_configuration(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save the complete configuration"""
        try:
            config = {}
            
            # Process Stripe configuration
            stripe_config = request_data.get('stripe', {})
            if stripe_config.get('skipped'):
                config['stripe'] = {'skipped': True}
            elif 'api_key' in stripe_config:
                config['stripe'] = {
                    'api_key': stripe_config['api_key'],
                    'publishable_key': stripe_config.get('publishable_key', ''),
                    'configured_at': datetime.now().isoformat()
                }
                
            # Process Xero configuration  
            xero_config = request_data.get('xero', {})
            if xero_config.get('skipped'):
                config['xero'] = {'skipped': True}
            elif 'client_id' in xero_config:
                config['xero'] = {
                    'client_id': xero_config['client_id'],
                    'client_secret': xero_config['client_secret'],
                    'configured_at': datetime.now().isoformat()
                }
                
            # Save encrypted configuration
            success = self.config_manager.save_config(config)
            
            if success:
                return {
                    'success': True,
                    'message': 'Configuration saved successfully',
                    'services_configured': len([k for k in config.keys() if not config[k].get('skipped', False)]),
                    'services_skipped': len([k for k in config.keys() if config[k].get('skipped', False)])
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
def get_configured_credentials() -> Dict[str, Any]:
    """Get decrypted credentials for use in the main app"""
    try:
        config_manager = ConfigurationManager()
        config = config_manager.load_config()
        
        if not config:
            return {}
            
        credentials = {}
        
        # Extract Stripe credentials
        stripe_config = config.get('stripe', {})
        if not stripe_config.get('skipped', False):
            credentials['STRIPE_API_KEY'] = stripe_config.get('api_key')
            credentials['STRIPE_PUBLISHABLE_KEY'] = stripe_config.get('publishable_key', '')
            
        # Extract Xero credentials
        xero_config = config.get('xero', {})
        if not xero_config.get('skipped', False):
            credentials['XERO_CLIENT_ID'] = xero_config.get('client_id')
            credentials['XERO_CLIENT_SECRET'] = xero_config.get('client_secret')
            
        return credentials
        
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return {}


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
            'xero': {'configured': False, 'skipped': False, 'has_credentials': False}
        }


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