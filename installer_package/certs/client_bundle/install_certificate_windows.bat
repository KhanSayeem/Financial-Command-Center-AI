@echo off
echo.
echo ================================================
echo  Financial Command Center AI - Certificate Setup
echo ================================================
echo.
echo This script will install the SSL certificate to eliminate browser warnings.
echo.
set "CERT_FILE=C:\Users\Hi\Documents\GitHub\Stripe Playground\Financial-Command-Center-AI\installer_package\certs\client_bundle\ca_certificate.crt"

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
powershell -Command "& {try { Import-Certificate -FilePath '%CERT_FILE%' -CertStoreLocation 'Cert:\LocalMachine\Root' -ErrorAction Stop; Write-Host 'Certificate installed successfully!' -ForegroundColor Green } catch { Write-Host 'Error installing certificate. Trying manual method...' -ForegroundColor Yellow; Start-Process certlm.msc -Verb RunAs }}"

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
    echo You can now access https://127.0.0.1:8000 without warnings.
    echo Please restart your browser to see the changes.
)

echo.
pause
