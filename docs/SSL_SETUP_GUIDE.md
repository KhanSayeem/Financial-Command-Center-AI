# 🔐 SSL Certificate Management Guide

**Financial Command Center AI** now includes a comprehensive SSL certificate management system that automatically handles certificate generation, trust store management, and provides professional HTTP/HTTPS mode switching.

## 🚀 Quick Start

### 1. Automatic Setup (Recommended)
```bash
# Start the application - certificates will be generated automatically
python app.py
```

### 2. Manual Certificate Generation
```bash
# Generate SSL certificates manually
python cert_manager.py --generate

# Create client installation bundle
python cert_manager.py --bundle

# Check certificate health
python cert_manager.py --health
```

## 🔧 Features

### ✨ Automatic Certificate Generation
- Self-signed CA (Certificate Authority) creation
- Server certificates with proper Subject Alternative Names (SAN)
- Automatic renewal when certificates expire
- Support for multiple hostnames (localhost, 127.0.0.1, ::1)

### 🛡️ Professional Security Warnings
- HTTP to HTTPS redirect with countdown
- Security risk explanations
- Professional upgrade prompts
- Configurable enforcement modes

### 📦 Client-Friendly Installation
- Automated installer scripts for Windows, macOS, and Linux
- Certificate bundle generation
- Step-by-step installation instructions
- Browser-specific setup guides

### 🐳 Docker Integration
- Complete Docker Compose setup
- SSL termination with nginx
- Certificate volume management
- Health checks and monitoring

## 📋 Configuration Options

### Environment Variables

```bash
# SSL Configuration
FORCE_HTTPS=true          # Force HTTPS mode (default: true)
ALLOW_HTTP=false          # Allow HTTP connections (default: false)
SSL_CERT_FILE=certs/server.crt     # Server certificate path
SSL_KEY_FILE=certs/server.key      # Server private key path
CA_CERT_FILE=certs/ca.crt         # CA certificate path

# Certificate Settings
CERT_VALIDITY_DAYS=365    # Certificate validity period
CERT_ORGANIZATION="Financial Command Center AI"
CERT_COUNTRY="US"
CERT_HOSTNAMES="localhost,127.0.0.1,::1"
```

### Server Modes

#### 1. HTTPS Mode (Default)
```bash
# Force HTTPS with automatic certificate generation
FORCE_HTTPS=true ALLOW_HTTP=false python app.py
```

#### 2. HTTP Mode with Warnings
```bash
# Allow HTTP but show security warnings
FORCE_HTTPS=false ALLOW_HTTP=true python app.py
```

#### 3. Mixed Mode
```bash
# HTTPS preferred, HTTP allowed for health checks
FORCE_HTTPS=false ALLOW_HTTP=true python app.py
```

## 🖥️ Browser Certificate Installation

### Automatic Installation (Recommended)

1. **Generate Certificate Bundle:**
   ```bash
   python cert_manager.py --bundle
   ```

2. **Run Platform-Specific Installer:**
   
   **Windows (Run as Administrator):**
   ```cmd
   cd certs\client_bundle
   install_certificate_windows.bat
   ```
   
   **macOS/Linux:**
   ```bash
   cd certs/client_bundle
   ./install_certificate_unix.sh
   ```

### Manual Browser Installation

#### Chrome/Edge
1. Visit `https://localhost:8000`
2. Click "Advanced" → "Proceed to localhost (unsafe)"
3. Click the lock icon → "Certificate" → "Details"
4. Export certificate and import to "Trusted Root Certification Authorities"

#### Firefox
1. Visit `https://localhost:8000`
2. Click "Advanced" → "Accept the Risk and Continue"
3. Click lock icon → "View Certificate" → "Download"
4. Settings → Privacy & Security → View Certificates → Import

## 🐳 Docker Setup

### Basic Docker Compose
```bash
# Use the provided SSL-enabled Docker Compose
docker-compose -f docker-compose.ssl.yml up
```

### With Custom Certificates
```bash
# Place your certificates in ./certs/ directory
# Start with custom certificate volume
docker-compose -f docker-compose.ssl.yml up
```

### Development with Auto-Generated Certificates
```bash
# Generate certificates first
python cert_manager.py --generate

# Start Docker services
docker-compose -f docker-compose.ssl.yml up
```

## 🔍 Troubleshooting

### Certificate Warnings in Browser

**Problem:** Browser shows "Not Secure" warnings

**Solutions:**
1. **Install CA Certificate** (Recommended):
   ```bash
   python cert_manager.py --bundle
   # Run the generated installer
   ```

2. **Accept Risk** (Development only):
   - Chrome: Advanced → Proceed to localhost
   - Firefox: Advanced → Accept Risk and Continue

### Connection Refused Errors

**Problem:** Cannot connect to `https://localhost:8000`

**Solutions:**
1. **Check if app is running:**
   ```bash
   curl -k https://localhost:8000/health
   ```

2. **Verify certificate files exist:**
   ```bash
   python cert_manager.py --check
   ```

3. **Regenerate certificates:**
   ```bash
   python cert_manager.py --generate
   ```

### Certificate Expired

**Problem:** Certificate has expired

**Solution:**
```bash
# Regenerate certificates (automatic on app start)
python cert_manager.py --generate
```

### Docker SSL Issues

**Problem:** SSL not working in Docker

**Solutions:**
1. **Check certificate volume:**
   ```bash
   docker-compose -f docker-compose.ssl.yml exec financial-command-center ls -la /app/certs/
   ```

2. **Regenerate in container:**
   ```bash
   docker-compose -f docker-compose.ssl.yml exec financial-command-center python cert_manager.py --generate
   ```

## 🏢 Enterprise Deployment

### Using Organizational CA

1. **Replace CA files:**
   ```bash
   cp your-org-ca.crt certs/ca.crt
   cp your-org-ca.key certs/ca.key
   ```

2. **Generate server certificates:**
   ```bash
   python cert_manager.py --generate
   ```

### Load Balancer / Reverse Proxy

For production deployments with load balancers:

1. **Configure SSL termination at load balancer**
2. **Run app in HTTP mode:**
   ```bash
   FORCE_HTTPS=false ALLOW_HTTP=true python app.py
   ```
3. **Use provided nginx configuration:**
   ```bash
   # Copy nginx/ssl.conf to your nginx configuration
   ```

### Cloud Deployment

For cloud deployments (AWS ELB, GCP Load Balancer, etc.):

1. **Use cloud SSL certificates**
2. **Configure health checks:**
   ```bash
   # Health check endpoint works over HTTP
   GET /health
   ```
3. **Set environment variables:**
   ```bash
   FORCE_HTTPS=false  # SSL handled by cloud load balancer
   ALLOW_HTTP=true    # Internal traffic
   ```

## 📊 Monitoring and Health Checks

### SSL Health Check
```bash
# Complete SSL system health check
python cert_manager.py --health
```

### Application Health Check
```bash
# Basic health check (works over HTTP/HTTPS)
curl -k https://localhost:8000/health
```

### Certificate Status API
```bash
# Get certificate information via API
curl -k https://localhost:8000/admin/ssl-help
```

## 🔧 Command Line Tools

### Certificate Manager CLI

```bash
# Available commands
python cert_manager.py --help

# Generate new certificates
python cert_manager.py --generate

# Check certificate status
python cert_manager.py --check

# Show installation instructions
python cert_manager.py --instructions

# Create client installation bundle
python cert_manager.py --bundle

# Perform complete health check
python cert_manager.py --health
```

## 🆘 Support

### Getting Help

1. **SSL Setup Guide:** Visit `https://localhost:8000/admin/ssl-help`
2. **Certificate Bundle:** Download from `https://localhost:8000/admin/certificate-bundle`
3. **Health Check:** Monitor at `https://localhost:8000/health`

### Common Issues

| Issue | Solution |
|-------|----------|
| Certificate warnings | Install CA certificate using bundle |
| Connection refused | Check if app is running on correct port |
| Certificate expired | Regenerate with `--generate` |
| Docker SSL issues | Check volume mounts and permissions |
| Browser trust issues | Clear browser cache and retry |

### Support Channels

- **Documentation:** Check this guide and `/admin/ssl-help`
- **Health Check:** Use `python cert_manager.py --health`
- **GitHub Issues:** Report issues on the project repository

## 🔒 Security Best Practices

1. **Use HTTPS in Production:**
   ```bash
   FORCE_HTTPS=true ALLOW_HTTP=false
   ```

2. **Regularly Update Certificates:**
   - Certificates auto-renew 7 days before expiry
   - Monitor certificate health regularly

3. **Secure Certificate Storage:**
   - Certificate files have restrictive permissions (600)
   - Private keys are never transmitted

4. **Network Security:**
   - Use reverse proxy for production
   - Enable rate limiting
   - Configure proper firewall rules

---

**🎉 You're now ready to use Financial Command Center AI with professional SSL certificate management!**

For additional help, visit the SSL setup guide at `https://localhost:8000/admin/ssl-help`