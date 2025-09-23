# 🪟 Windows Certificate Installation Guide

**Financial Command Center AI** - Eliminating SSL Certificate Warnings on Windows

## 🚀 Quick Fix (Automated)

1. **Generate Certificate Bundle:**
   ```bash
   python cert_manager.py --bundle
   ```

2. **Install Certificate:**
   - Navigate to the `certs/client_bundle` folder
   - **Right-click** on `install_certificate_windows.bat`
   - Select **"Run as administrator"**
   - Follow the prompts
   - **Restart your browser completely**

## 📋 Manual Installation (If Automatic Fails)

### Method 1: Using Certificate Manager (MMC)

1. **Open Certificate Manager:**
   - Press `Win + R`
   - Type `certlm.msc` and press Enter
   - Click "Yes" if prompted by UAC

2. **Navigate to Trusted Root:**
   - Expand **"Trusted Root Certification Authorities"**
   - Right-click on **"Certificates"**
   - Select **"All Tasks"** → **"Import"**

3. **Import Certificate:**
   - Click "Next" in the Certificate Import Wizard
   - Click "Browse" and navigate to:
     ```
     certs/client_bundle/ca_certificate.crt
     ```
   - Select the file and click "Open"
   - Click "Next"
   - Ensure "Trusted Root Certification Authorities" is selected
   - Click "Next" then "Finish"
   - Click "Yes" to confirm the installation

### Method 2: Using PowerShell (Administrator)

1. **Open PowerShell as Administrator:**
   - Press `Win + X`
   - Select **"Windows PowerShell (Admin)"**

2. **Run Import Command:**
   ```powershell
   Import-Certificate -FilePath "C:\Path\To\Your\Project\certs\client_bundle\ca_certificate.crt" -CertStoreLocation "Cert:\LocalMachine\Root"
   ```
   (Replace the path with your actual project path)

### Method 3: Browser-Specific Installation

#### For Chrome/Edge:
1. Visit `https://localhost:8000` (ignore warning for now)
2. Click the **lock icon** in address bar
3. Click **"Certificate is not valid"**
4. Click **"Details"** tab
5. Click **"Copy to File"**
6. Save as .cer file
7. Go to **Settings** → **Privacy and Security** → **Security**
8. Click **"Manage certificates"**
9. Go to **"Trusted Root Certification Authorities"** tab
10. Click **"Import"** and select the saved certificate

#### For Firefox:
1. Go to **Settings** → **Privacy & Security**
2. Scroll to **"Certificates"** and click **"View Certificates"**
3. Go to **"Authorities"** tab
4. Click **"Import"**
5. Navigate to `certs/client_bundle/ca_certificate.crt`
6. Check **"Trust this CA to identify websites"**
7. Click **"OK"**

## 🔧 Troubleshooting

### Still Seeing Warnings?

1. **Complete Browser Restart:**
   - Close ALL browser windows (including background processes)
   - Wait 10 seconds
   - Reopen browser
   - Try accessing `https://localhost:8000`

2. **Clear Browser Data:**
   - Press `Ctrl + Shift + Delete`
   - Select "All time"
   - Clear cookies, cache, and site data
   - Restart browser

3. **Check Certificate Installation:**
   ```bash
   python tests/manual/test_certificate_install.py
   ```

4. **Verify Certificate in Windows:**
   - Open `certlm.msc` as administrator
   - Navigate to **Trusted Root Certification Authorities** → **Certificates**
   - Look for **"Financial Command Center AI CA"**

### Common Issues:

#### "Access Denied" when running batch file
- **Solution:** Right-click the `.bat` file and select "Run as administrator"

#### Certificate still not trusted
- **Solution:** Make sure you installed to **"Trusted Root Certification Authorities"**, not "Personal"

#### Browser still shows warnings
- **Solution:** Complete browser restart is required (close all windows, wait, reopen)

#### PowerShell execution error
- **Solution:** Run PowerShell as Administrator and enable script execution:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

## 🧪 Verification Steps

After installation, verify the certificate is working:

1. **Test with curl:**
   ```bash
   curl -I https://localhost:8000/health
   ```
   Should return HTTP/2 200 without certificate errors

2. **Test in browser:**
   - Visit `https://localhost:8000`
   - Check for green lock icon in address bar
   - No "Not Secure" warnings should appear

3. **Run automated test:**
   ```bash
   python tests/manual/test_certificate_install.py
   ```

## 📞 Support

If you're still having issues:

1. **Check the SSL Help page:** `https://localhost:8000/admin/ssl-help`
2. **Run the health check:** `https://localhost:8000/health`
3. **Generate new certificates:** `python cert_manager.py --generate`

## ✅ Success Indicators

You'll know the certificate is properly installed when:

- ✅ Browser shows green lock icon
- ✅ No "Not Secure" warnings
- ✅ No "Proceed to localhost (unsafe)" prompts
- ✅ `curl` commands work without `-k` flag
- ✅ Test script reports "Certificate is trusted by system!"

---

**🎉 Once installed, you'll have secure HTTPS access without any browser warnings!**