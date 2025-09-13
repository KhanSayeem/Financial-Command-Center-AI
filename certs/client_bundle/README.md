
# SSL Certificate Installation Instructions

## Automatic Trust (Recommended)

### Windows (Run as Administrator):
```cmd
certlm.msc
# Navigate to: Trusted Root Certification Authorities → Certificates
# Right-click → All Tasks → Import → Browse to: C:\Users\Hi\Documents\GitHub\Stripe Playground\Financial-Command-center-AI\certs\ca.crt
```

### macOS:
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "C:\Users\Hi\Documents\GitHub\Stripe Playground\Financial-Command-center-AI\certs\ca.crt"
```

### Linux (Ubuntu/Debian):
```bash
sudo cp "C:\Users\Hi\Documents\GitHub\Stripe Playground\Financial-Command-center-AI\certs\ca.crt" /usr/local/share/ca-certificates/financial-command-center-ca.crt
sudo update-ca-certificates
```

## Manual Browser Trust

### Chrome/Edge:
1. Visit: https://127.0.0.1:8000
2. Click "Advanced" → "Proceed to 127.0.0.1 (unsafe)"
3. Click the lock icon → "Certificate" → "Details" tab
4. Click "Copy to File" → Save as .cer file
5. Settings → Privacy and Security → Manage Certificates
6. Import to "Trusted Root Certification Authorities"

### Firefox:
1. Visit: https://127.0.0.1:8000
2. Click "Advanced" → "Accept the Risk and Continue"
3. Click lock icon → "Connection not secure" → "More Information"
4. "Security" tab → "View Certificate" → "Download"
5. Settings → Privacy & Security → Certificates → "View Certificates"
6. Import to "Authorities" tab

## Verify Installation:
```bash
curl -I https://127.0.0.1:8000/health
# Should return HTTP/2 200 without certificate errors
```

## Certificate Details:
- **CA Certificate**: C:\Users\Hi\Documents\GitHub\Stripe Playground\Financial-Command-center-AI\certs\ca.crt
- **Server Certificate**: C:\Users\Hi\Documents\GitHub\Stripe Playground\Financial-Command-center-AI\certs\server.crt
- **Valid Until**: 2027-12-13 07:57:20 UTC
- **Hostnames**: localhost, 127.0.0.1, ::1
