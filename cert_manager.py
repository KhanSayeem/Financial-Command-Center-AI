#!/usr/bin/env python3
"""
SSL Certificate Manager for Financial Command Center AI
Handles automatic certificate generation, trust store management, and client instructions
"""

import os
import sys
import json
import subprocess
import socket
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa


class CertificateManager:
    """Manages SSL certificates for local development and production"""
    
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.certs_dir = self.base_dir / "certs"
        self.config_file = self.certs_dir / "cert_config.json"
        
        # Ensure certs directory exists
        self.certs_dir.mkdir(exist_ok=True, parents=True)
        
        # Default configuration
        self.config = {
            "cert_file": str(self.certs_dir / "server.crt"),
            "key_file": str(self.certs_dir / "server.key"),
            "ca_cert": str(self.certs_dir / "ca.crt"),
            "ca_key": str(self.certs_dir / "ca.key"),
            "validity_days": 365,
            "last_generated": None,
            "hostnames": ["localhost", "127.0.0.1", "::1"],
            "organization": "Financial Command Center AI",
            "country": "US"
        }
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file if it exists"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
            except Exception as e:
                print(f"⚠️  Warning: Could not load certificate config: {e}")
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save certificate config: {e}")
    
    def generate_ca_certificate(self):
        """Generate a Certificate Authority (CA) certificate"""
        print("🔐 Generating Certificate Authority (CA)...")
        
        # Generate private key
        ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create CA certificate
        ca_name = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, self.config["country"]),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, f"{self.config['organization']} CA"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Financial Command Center AI CA"),
        ])
        
        ca_cert = x509.CertificateBuilder().subject_name(
            ca_name
        ).issuer_name(
            ca_name
        ).public_key(
            ca_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=self.config["validity_days"] * 2)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                key_encipherment=False,
                key_agreement=False,
                content_commitment=False,
                data_encipherment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(ca_key, hashes.SHA256())
        
        # Save CA certificate and key
        with open(self.config["ca_cert"], "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
        
        with open(self.config["ca_key"], "wb") as f:
            f.write(ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        
        # Set restrictive permissions
        os.chmod(self.config["ca_key"], 0o600)
        print(f"✅ CA certificate saved to: {self.config['ca_cert']}")
        
        return ca_cert, ca_key
    
    def generate_server_certificate(self):
        """Generate server certificate signed by CA"""
        print("🔐 Generating server certificate...")
        
        # Load or generate CA
        if not (Path(self.config["ca_cert"]).exists() and Path(self.config["ca_key"]).exists()):
            ca_cert, ca_key = self.generate_ca_certificate()
        else:
            # Load existing CA
            with open(self.config["ca_cert"], "rb") as f:
                ca_cert = x509.load_pem_x509_certificate(f.read())
            
            with open(self.config["ca_key"], "rb") as f:
                ca_key = serialization.load_pem_private_key(f.read(), password=None)
        
        # Generate server private key
        server_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create server certificate
        server_name = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, self.config["country"]),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.config["organization"]),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        # Build SAN (Subject Alternative Names)
        san_list = []
        for hostname in self.config["hostnames"]:
            if hostname.replace('.', '').replace(':', '').isdigit() or ':' in hostname:
                # IP address
                import ipaddress
                try:
                    ip = ipaddress.ip_address(hostname)
                    san_list.append(x509.IPAddress(ip))
                except:
                    san_list.append(x509.DNSName(hostname))
            else:
                # DNS name
                san_list.append(x509.DNSName(hostname))
        
        server_cert = x509.CertificateBuilder().subject_name(
            server_name
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            server_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=self.config["validity_days"])
        ).add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=False,
                crl_sign=False,
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                content_commitment=False,
                data_encipherment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=True,
        ).sign(ca_key, hashes.SHA256())
        
        # Save server certificate and key
        with open(self.config["cert_file"], "wb") as f:
            f.write(server_cert.public_bytes(serialization.Encoding.PEM))
        
        with open(self.config["key_file"], "wb") as f:
            f.write(server_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        
        # Set restrictive permissions
        os.chmod(self.config["key_file"], 0o600)
        
        # Update config
        self.config["last_generated"] = datetime.now().isoformat()
        self._save_config()
        
        print(f"✅ Server certificate saved to: {self.config['cert_file']}")
        print(f"✅ Server key saved to: {self.config['key_file']}")
        
        return server_cert, server_key
    
    def is_certificate_valid(self):
        """Check if existing certificate is valid"""
        try:
            if not (Path(self.config["cert_file"]).exists() and Path(self.config["key_file"]).exists()):
                return False
            
            with open(self.config["cert_file"], "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
            
            # Check if certificate is still valid for at least 7 days
            expires_soon = datetime.utcnow() + timedelta(days=7)
            return cert.not_valid_after > expires_soon
        except Exception as e:
            print(f"⚠️  Certificate validation error: {e}")
            return False
    
    def ensure_certificates(self):
        """Ensure valid certificates exist, generate if needed"""
        if not self.is_certificate_valid():
            print("🔄 Generating new SSL certificates...")
            self.generate_server_certificate()
            return True
        else:
            print("✅ SSL certificates are valid")
            return False
    
    def get_ssl_context(self):
        """Get SSL context for Flask"""
        self.ensure_certificates()
        return (self.config["cert_file"], self.config["key_file"])
    
    def install_ca_instructions(self):
        """Generate instructions for installing the CA certificate"""
        ca_cert_path = Path(self.config["ca_cert"])
        if not ca_cert_path.exists():
            return "CA certificate not found. Run certificate generation first."
        
        instructions = f"""
# 🔐 SSL Certificate Installation Instructions

## Automatic Trust (Recommended)

### Windows (Run as Administrator):
```cmd
certlm.msc
# Navigate to: Trusted Root Certification Authorities → Certificates
# Right-click → All Tasks → Import → Browse to: {ca_cert_path.absolute()}
```

### macOS:
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "{ca_cert_path.absolute()}"
```

### Linux (Ubuntu/Debian):
```bash
sudo cp "{ca_cert_path.absolute()}" /usr/local/share/ca-certificates/financial-command-center-ca.crt
sudo update-ca-certificates
```

## Manual Browser Trust

### Chrome/Edge:
1. Visit: https://localhost:8000
2. Click "Advanced" → "Proceed to localhost (unsafe)"
3. Click the lock icon → "Certificate" → "Details" tab
4. Click "Copy to File" → Save as .cer file
5. Settings → Privacy and Security → Manage Certificates
6. Import to "Trusted Root Certification Authorities"

### Firefox:
1. Visit: https://localhost:8000
2. Click "Advanced" → "Accept the Risk and Continue"
3. Click lock icon → "Connection not secure" → "More Information"
4. "Security" tab → "View Certificate" → "Download"
5. Settings → Privacy & Security → Certificates → "View Certificates"
6. Import to "Authorities" tab

## Verify Installation:
```bash
curl -I https://localhost:8000/health
# Should return HTTP/2 200 without certificate errors
```

## Certificate Details:
- **CA Certificate**: {ca_cert_path.absolute()}
- **Server Certificate**: {Path(self.config['cert_file']).absolute()}
- **Valid Until**: {self._get_cert_expiry()}
- **Hostnames**: {', '.join(self.config['hostnames'])}
"""
        return instructions
    
    def _get_cert_expiry(self):
        """Get certificate expiry date"""
        try:
            with open(self.config["cert_file"], "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
            return cert.not_valid_after.strftime("%Y-%m-%d %H:%M:%S UTC")
        except:
            return "Unknown"
    
    def create_client_bundle(self):
        """Create a client bundle with certificate and instructions"""
        bundle_dir = self.certs_dir / "client_bundle"
        bundle_dir.mkdir(exist_ok=True)
        
        # Copy CA certificate
        ca_dest = bundle_dir / "ca_certificate.crt"
        if Path(self.config["ca_cert"]).exists():
            import shutil
            shutil.copy2(self.config["ca_cert"], ca_dest)
        
        # Create installation script for Windows
        windows_script = bundle_dir / "install_certificate_windows.bat"
        with open(windows_script, 'w', encoding='utf-8') as f:
            f.write(f"""@echo off
echo.
echo ================================================
echo  Financial Command Center AI - Certificate Setup
echo ================================================
echo.
echo This script will install the SSL certificate to eliminate browser warnings.
echo.
set "CERT_FILE={ca_dest.absolute()}"

REM Check if certificate file exists
if not exist "%CERT_FILE%" (
    echo Error: Certificate file not found!
    echo Expected location: %CERT_FILE%
    echo.
    pause
    exit /b 1
)

echo Certificate file found: %CERT_FILE%
echo.
echo Installing certificate to Trusted Root Certification Authorities...
echo.

REM Try to install using certlm (requires admin privileges)
powershell -Command "& {{try {{ Import-Certificate -FilePath '%CERT_FILE%' -CertStoreLocation 'Cert:\\LocalMachine\\Root' -ErrorAction Stop; Write-Host 'Certificate installed successfully!' -ForegroundColor Green }} catch {{ Write-Host 'Error installing certificate. Trying manual method...' -ForegroundColor Yellow; Start-Process certlm.msc -Verb RunAs }}}}"

if %errorlevel% neq 0 (
    echo.
    echo Automatic installation failed. Opening Certificate Manager...
    echo Please manually import the certificate:
    echo 1. Navigate to: Trusted Root Certification Authorities ^> Certificates
    echo 2. Right-click ^> All Tasks ^> Import
    echo 3. Browse to: %CERT_FILE%
    echo 4. Complete the wizard
    echo.
    powershell -Command "Start-Process certlm.msc -Verb RunAs"
) else (
    echo.
    echo ================================================
    echo  Certificate Installation Complete!
    echo ================================================
    echo.
    echo You can now access https://localhost:8000 without warnings.
    echo Please restart your browser to see the changes.
)

echo.
pause
""")
        
        # Create installation script for macOS/Linux
        unix_script = bundle_dir / "install_certificate_unix.sh"
        with open(unix_script, 'w', encoding='utf-8') as f:
            f.write(f"""#!/bin/bash

echo "================================================"
echo " Financial Command Center AI - Certificate Setup"
echo "================================================"
echo
echo "This script will install the SSL certificate to eliminate browser warnings."
echo

CERT_FILE="{ca_dest.absolute()}"

# Check if certificate file exists
if [ ! -f "$CERT_FILE" ]; then
    echo "Error: Certificate file not found!"
    echo "Expected location: $CERT_FILE"
    exit 1
fi

echo "Certificate file found: $CERT_FILE"
echo

# Detect OS and install accordingly
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS detected"
    echo "Installing certificate to system keychain..."
    echo "This requires administrator privileges."
    echo
    
    # Try to install to system keychain
    if sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$CERT_FILE"; then
        echo
        echo "================================================"
        echo " Certificate Installation Complete!"
        echo "================================================"
        echo
        echo "You can now access https://localhost:8000 without warnings."
        echo "Please restart your browser to see the changes."
    else
        echo "Error: Failed to install certificate to system keychain."
        echo "Please try installing manually:"
        echo "1. Double-click the certificate file: $CERT_FILE"
        echo "2. Select 'System' keychain"
        echo "3. Click 'Add'"
        echo "4. Open Keychain Access, find the certificate, and set it to 'Always Trust'"
        exit 1
    fi
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Linux detected"
    echo "Installing certificate to system trust store..."
    echo "This requires administrator privileges."
    echo
    
    # Install for system-wide trust
    if sudo cp "$CERT_FILE" /usr/local/share/ca-certificates/financial-command-center-ca.crt && sudo update-ca-certificates; then
        echo
        echo "================================================"
        echo " Certificate Installation Complete!"
        echo "================================================"
        echo
        echo "System-wide certificate trust has been updated."
        echo "You can now access https://localhost:8000 without warnings."
        echo "Please restart your browser to see the changes."
    else
        echo "Error: Failed to install certificate."
        echo "Please check that you have the required permissions."
        exit 1
    fi
    
    # Also try to install for browsers that use their own certificate stores
    if command -v update-ca-certificates >/dev/null 2>&1; then
        echo "Updating system certificate authorities..."
        sudo update-ca-certificates
    fi
    
else
    echo "Unsupported OS: $OSTYPE"
    echo "Please install the certificate manually:"
    echo "Certificate location: $CERT_FILE"
    echo
    echo "For most browsers, you can:"
    echo "1. Open browser settings"
    echo "2. Find 'Security' or 'Privacy' settings"
    echo "3. Look for 'Certificates' or 'Certificate Authorities'"
    echo "4. Import the certificate as a trusted root authority"
    exit 1
fi

echo
echo "Note: If you still see warnings, please:"
echo "1. Restart your browser completely"
echo "2. Clear browser cache and cookies for localhost"
echo "3. Try accessing https://localhost:8000 again"
""")
        
        # Make Unix script executable
        os.chmod(unix_script, 0o755)
        
        # Create README
        readme_file = bundle_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(self.install_ca_instructions())
        
        print(f"📦 Client bundle created in: {bundle_dir}")
        return bundle_dir
    
    def health_check(self):
        """Perform SSL health check"""
        status = {
            "certificate_valid": self.is_certificate_valid(),
            "ca_exists": Path(self.config["ca_cert"]).exists(),
            "server_cert_exists": Path(self.config["cert_file"]).exists(),
            "server_key_exists": Path(self.config["key_file"]).exists(),
            "last_generated": self.config.get("last_generated"),
            "expires": self._get_cert_expiry(),
            "hostnames": self.config["hostnames"]
        }
        
        # Test SSL connection
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection(("localhost", 8000), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname="localhost") as ssock:
                    status["ssl_connection"] = "success"
                    status["ssl_version"] = ssock.version()
                    status["cipher"] = ssock.cipher()
        except Exception as e:
            status["ssl_connection"] = f"failed: {str(e)}"
        
        return status


def main():
    """Command line interface for certificate management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SSL Certificate Manager for Financial Command Center AI")
    parser.add_argument("--generate", action="store_true", help="Generate new certificates")
    parser.add_argument("--check", action="store_true", help="Check certificate status")
    parser.add_argument("--instructions", action="store_true", help="Show installation instructions")
    parser.add_argument("--bundle", action="store_true", help="Create client installation bundle")
    parser.add_argument("--health", action="store_true", help="Perform health check")
    
    args = parser.parse_args()
    
    cert_manager = CertificateManager()
    
    if args.generate:
        cert_manager.generate_server_certificate()
    elif args.check:
        valid = cert_manager.is_certificate_valid()
        print(f"Certificate valid: {'✅ Yes' if valid else '❌ No'}")
        if not valid:
            print("Run with --generate to create new certificates")
    elif args.instructions:
        print(cert_manager.install_ca_instructions())
    elif args.bundle:
        cert_manager.create_client_bundle()
    elif args.health:
        status = cert_manager.health_check()
        print("🔐 SSL Certificate Health Check:")
        print("=" * 40)
        for key, value in status.items():
            icon = "✅" if (key.endswith("_exists") and value) or (key == "certificate_valid" and value) or (key == "ssl_connection" and value == "success") else "❌" if key.endswith("_exists") or key in ["certificate_valid", "ssl_connection"] else "ℹ️"
            print(f"{icon} {key.replace('_', ' ').title()}: {value}")
    else:
        # Default: ensure certificates exist
        cert_manager.ensure_certificates()
        print("\n📋 Available commands:")
        print("  --generate     Generate new certificates")
        print("  --check        Check certificate status")
        print("  --instructions Show installation instructions")
        print("  --bundle       Create client installation bundle")
        print("  --health       Perform health check")


if __name__ == "__main__":
    main()