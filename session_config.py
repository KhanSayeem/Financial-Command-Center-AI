"""
Flask Session Configuration Module
==================================

Provides enhanced Flask session configuration for OAuth token persistence
and secure session management in the Financial Command Center AI application.

Features:
- Secure session configuration with proper secret keys
- Session persistence across application restarts
- Enhanced security settings for production use
- Session debugging and monitoring utilities
"""

import os
import secrets
from datetime import timedelta, datetime
from pathlib import Path
import json
import logging

# Configure logging for session management
logger = logging.getLogger(__name__)

class SessionConfigManager:
    """Manages Flask session configuration with enhanced security and persistence"""
    
    def __init__(self, app=None):
        self.app = app
        self.config_dir = self._get_config_directory()
        self.secret_key_file = self.config_dir / 'flask_secret.key'
        
        if app:
            self.init_app(app)
    
    def _get_config_directory(self) -> Path:
        """Get or create the configuration directory"""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('LOCALAPPDATA', '~')) / 'Financial-Command-Center-AI' / 'config'
        else:  # Unix-like
            config_dir = Path.home() / '.config' / 'financial-command-center-ai'
        
        config_dir = config_dir.expanduser()
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def _get_or_generate_secret_key(self) -> str:
        """Get existing secret key or generate a new one"""
        try:
            if self.secret_key_file.exists():
                with open(self.secret_key_file, 'r', encoding='utf-8') as f:
                    key = f.read().strip()
                    if key and len(key) >= 32:
                        logger.info("Loaded existing Flask secret key")
                        return key
        except Exception as e:
            logger.warning(f"Failed to load existing secret key: {e}")
        
        # Generate new secret key
        logger.info("Generating new Flask secret key")
        key = secrets.token_urlsafe(64)
        
        try:
            with open(self.secret_key_file, 'w', encoding='utf-8') as f:
                f.write(key)
            
            # Set secure permissions on the secret key file
            if os.name != 'nt':  # Unix-like systems
                os.chmod(self.secret_key_file, 0o600)
            
            logger.info(f"Secret key saved to {self.secret_key_file}")
        except Exception as e:
            logger.error(f"Failed to save secret key: {e}")
        
        return key
    
    def init_app(self, app):
        """Initialize Flask session configuration"""
        self.app = app
        
        # Set the secret key
        secret_key = os.getenv('FLASK_SECRET_KEY') or self._get_or_generate_secret_key()
        app.config['SECRET_KEY'] = secret_key
        
        # Session configuration for enhanced security and persistence
        app.config.update({
            # Session persistence settings
            'SESSION_PERMANENT': True,
            'PERMANENT_SESSION_LIFETIME': timedelta(days=7),  # Sessions last 7 days
            
            # Security settings
            'SESSION_COOKIE_SECURE': True,     # Only send cookies over HTTPS
            'SESSION_COOKIE_HTTPONLY': True,   # Prevent JavaScript access to cookies
            'SESSION_COOKIE_SAMESITE': 'Lax',  # CSRF protection
            
            # Session configuration
            'SESSION_USE_SIGNER': True,        # Sign session cookies
            'SESSION_KEY_PREFIX': 'fcc:',      # Prefix for session keys
            
            # Enhanced cookie settings
            'SESSION_COOKIE_NAME': 'fcc_session',
            'APPLICATION_ROOT': '/',
            'PREFERRED_URL_SCHEME': 'https',
        })
        
        # Add session debugging if in debug mode
        if app.config.get('DEBUG', False):
            self._setup_session_debugging(app)
        
        logger.info("Flask session configuration initialized")
        logger.info(f"Session lifetime: {app.config['PERMANENT_SESSION_LIFETIME']}")
        logger.info(f"Session security: HTTPS={app.config['SESSION_COOKIE_SECURE']}, HttpOnly={app.config['SESSION_COOKIE_HTTPONLY']}")
    
    def _setup_session_debugging(self, app):
        """Setup session debugging utilities for development"""
        @app.before_request
        def log_session_info():
            from flask import session, request
            if request.endpoint and not request.endpoint.startswith('static'):
                session_data = dict(session) if session else {}
                # Don't log sensitive data in production
                safe_session = {k: ('***' if 'token' in k.lower() or 'secret' in k.lower() else v) 
                               for k, v in session_data.items()}
                logger.debug(f"Session for {request.endpoint}: {safe_session}")
    
    def configure_oauth_session_handlers(self, api_client):
        """Configure OAuth session handlers with enhanced error handling"""
        from flask import session

        @api_client.oauth2_token_getter
        def get_token_from_session():
            """Retrieve the latest OAuth token from session metadata or disk storage"""
            try:
                token = session.get('token')
                if not token:
                    try:
                        from xero_client import get_stored_token
                        token = get_stored_token()
                    except Exception as store_error:
                        logger.debug(f"Token store unavailable: {store_error}")
                if token:
                    logger.debug("OAuth token retrieved from persistent store")
                    required_fields = ['access_token', 'token_type']
                    if all(field in token for field in required_fields):
                        return token
                    logger.warning("OAuth token missing required fields")
                    return None
                logger.debug("No OAuth token available in session or store")
                return None
            except Exception as e:
                logger.error(f"Error retrieving OAuth token: {e}")
                return None

        @api_client.oauth2_token_saver
        def save_token_to_session(token):
            """Persist OAuth tokens to disk and keep lightweight session metadata"""
            try:
                if not token:
                    logger.warning("Attempted to save empty OAuth token")
                    return

                allowed_fields = {
                    "access_token", "refresh_token", "token_type",
                    "expires_in", "expires_at", "scope", "id_token"
                }
                filtered_token = {k: v for k, v in token.items() if k in allowed_fields}

                if not filtered_token.get('access_token'):
                    logger.error("OAuth token missing access_token")
                    return

                try:
                    from xero_client import store_token
                    store_token(filtered_token)
                except Exception as storage_error:
                    logger.warning(f"Failed to persist OAuth token to disk: {storage_error}")

                session.permanent = True
                session.pop('token', None)
                session['token_meta'] = {
                    'has_refresh_token': bool(filtered_token.get('refresh_token')),
                    'stored_at': datetime.now().isoformat()
                }
                session.modified = True

                logger.info("OAuth token metadata saved to session")
                logger.debug(f"Token fields: {list(filtered_token.keys())}")

                if self.app and self.app.config.get('DEBUG', False):
                    self._backup_token_for_debug(filtered_token)

            except Exception as e:
                logger.error(f"Error saving OAuth token: {e}")
                raise

    def _backup_token_for_debug(self, token):
        """Backup token for debugging purposes (development only)"""
        try:
            debug_token_file = self.config_dir / 'debug_token.json'
            # Remove sensitive data for debug backup
            debug_token = {k: ('***' if k == 'access_token' else v) for k, v in token.items()}
            debug_token['timestamp'] = str(datetime.now())
            
            with open(debug_token_file, 'w', encoding='utf-8') as f:
                json.dump(debug_token, f, indent=2, default=str)
            
            logger.debug(f"Debug token backup saved to {debug_token_file}")
        except Exception as e:
            logger.warning(f"Failed to backup debug token: {e}")
    
    def health_check(self):
        """Check session configuration health"""
        checks = {
            'secret_key_configured': bool(self.app.config.get('SECRET_KEY')),
            'secret_key_secure': len(self.app.config.get('SECRET_KEY', '')) >= 32,
            'session_security_enabled': self.app.config.get('SESSION_COOKIE_SECURE', False),
            'session_httponly_enabled': self.app.config.get('SESSION_COOKIE_HTTPONLY', False),
            'session_permanent_enabled': self.app.config.get('SESSION_PERMANENT', False),
            'config_directory_writable': os.access(self.config_dir, os.W_OK),
            'secret_key_file_exists': self.secret_key_file.exists(),
        }
        
        return {
            'status': 'healthy' if all(checks.values()) else 'warning',
            'checks': checks,
            'config_directory': str(self.config_dir),
            'session_lifetime': str(self.app.config.get('PERMANENT_SESSION_LIFETIME')),
        }


def configure_flask_sessions(app, api_client=None):
    """
    Convenience function to configure Flask sessions with OAuth support
    
    Args:
        app: Flask application instance
        api_client: Optional Xero API client for OAuth token handlers
    
    Returns:
        SessionConfigManager instance
    """
    session_config = SessionConfigManager(app)
    
    if api_client:
        session_config.configure_oauth_session_handlers(api_client)
    
    return session_config


# For backward compatibility
def setup_session_config(app, api_client=None):
    """Legacy function name for backward compatibility"""
    return configure_flask_sessions(app, api_client)


if __name__ == '__main__':
    # Test configuration
    from datetime import datetime
    import tempfile
    
    print("Testing Session Configuration...")
    
    class MockApp:
        def __init__(self):
            self.config = {}
        def update(self, d):
            self.config.update(d)
    
    app = MockApp()
    session_config = SessionConfigManager(app)
    
    print(f"Generated secret key length: {len(app.config['SECRET_KEY'])}")
    print(f"Config directory: {session_config.config_dir}")
    print(f"Health check: {session_config.health_check()}")
    print("Session configuration test completed successfully!")
