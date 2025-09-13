#!/bin/bash

echo "================================================"
echo " Financial Command Center AI - Certificate Setup"
echo "================================================"
echo
echo "This script will install the SSL certificate to eliminate browser warnings."
echo

CERT_FILE="C:\Users\Hi\Documents\GitHub\Stripe Playground\Financial-Command-Center-AI\certs\client_bundle\ca_certificate.crt"

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
        echo "You can now access https://127.0.0.1:8000 without warnings."
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
        echo "You can now access https://127.0.0.1:8000 without warnings."
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
echo "2. Clear browser cache and cookies for 127.0.0.1"
echo "3. Try accessing https://127.0.0.1:8000 again"
