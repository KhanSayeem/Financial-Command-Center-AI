@echo off
setlocal enabledelayedexpansion

set "EXIT_CODE=0"
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

for %%I in ("%SCRIPT_DIR%.") do set "SCRIPT_DIR=%%~fI"

echo.
echo ================================================================
echo  ULTIMATE CERTIFICATE FIX AND LAUNCHER - Financial Command Center AI
echo ================================================================
echo.

if not defined LOCALAPPDATA (
    set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
)
set "MKCERT_ROOT=%LOCALAPPDATA%\mkcert\rootCA.pem"
set "DESKTOP_CERT=%USERPROFILE%\Desktop\mkcert-rootCA.crt"

echo Step 1: Closing previous Financial Command Center Python processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$repo = Convert-Path $env:SCRIPT_DIR; $procs = Get-Process -ErrorAction SilentlyContinue ^| Where-Object { $_.Name -eq 'python' -and $_.Path -and $_.Path.StartsWith($repo, [System.StringComparison]::OrdinalIgnoreCase) }; if ($procs) { $procs ^| ForEach-Object { Write-Host (' - Stopping PID {0}' -f $_.Id) -ForegroundColor Yellow; try { $_ ^| Stop-Process -Force -ErrorAction Stop } catch { Write-Host ('   Warning: ' + $_.Exception.Message) -ForegroundColor DarkYellow } } } else { Write-Host ' - No running repo python processes found.' -ForegroundColor DarkGray }"

echo.
echo Step 2: Ensuring mkcert root certificate exists...
set "PYTHON_CMD="
set "VENV_PY=%SCRIPT_DIR%\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    set "PYTHON_CMD=%VENV_PY%"
)
if not defined PYTHON_CMD (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined PYTHON_CMD set "PYTHON_CMD=%%P"
    )
)
if not defined PYTHON_CMD (
    echo [ERROR] Python 3 was not found in PATH. Please install Python 3.11+ and re-run this tool.
    goto cleanup_fail
)
if not exist "%MKCERT_ROOT%" (
    echo  - mkcert root certificate not found. Generating with cert_manager.py...
    "%PYTHON_CMD%" "cert_manager.py" --mkcert
) else (
    echo  - Existing mkcert root certificate found.
)

if not exist "%MKCERT_ROOT%" (
    echo [ERROR] mkcert root certificate is still missing after generation attempt.
    goto cleanup_fail
)

echo.
echo Step 3: Importing certificate into trust stores...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$certPath = $env:MKCERT_ROOT; if (-not (Test-Path $certPath)) { Write-Host ' - mkcert root certificate not available.' -ForegroundColor Red; exit }; try { Import-Certificate -FilePath $certPath -CertStoreLocation 'Cert:\LocalMachine\Root' -ErrorAction Stop; Write-Host 'SUCCESS: Certificate installed to Local Machine store.' -ForegroundColor Green } catch { Write-Host 'INFO: Could not add to Local Machine store (try Run as administrator).' -ForegroundColor Yellow }"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$certPath = $env:MKCERT_ROOT; if (-not (Test-Path $certPath)) { Write-Host ' - mkcert root certificate not available.' -ForegroundColor Red; exit }; try { Import-Certificate -FilePath $certPath -CertStoreLocation 'Cert:\CurrentUser\Root' -ErrorAction Stop; Write-Host 'SUCCESS: Certificate installed to Current User store.' -ForegroundColor Green } catch { Write-Host 'WARNING: Could not add to Current User store.' -ForegroundColor Red }"

if exist "%MKCERT_ROOT%" (
    copy /Y "%MKCERT_ROOT%" "%DESKTOP_CERT%" >nul 2>&1
    if exist "%DESKTOP_CERT%" (
        echo  - A copy of the root certificate is available at: %DESKTOP_CERT%
    )
)

echo.
echo Step 4: Verifying certificate health...
"%PYTHON_CMD%" "cert_manager.py" --health

echo.
echo Step 5: Launching Financial Command Center without reinstalling...
set "FCC_HOST=127.0.0.1"
if not defined FCC_PORT set "FCC_PORT=8000"
set "SERVER_URL=https://%FCC_HOST%:%FCC_PORT%"

set "FLASK_ENV=production"
set "FORCE_HTTPS=true"
set "ALLOW_HTTP=false"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "APP_MODE=demo"
set "XERO_REDIRECT_HOST=%FCC_HOST%"

if exist "%VENV_PY%" (
    echo  - Using virtual environment Python at %VENV_PY%
) else (
    echo  - Virtual environment not found, using %PYTHON_CMD%
)

start "Financial Command Center Server" /MIN "%PYTHON_CMD%" "app_with_setup_wizard.py"

echo  - Waiting for server to become ready on %SERVER_URL% ...
set "SERVER_READY="
for /L %%I in (1,1,12) do (
    curl -k --silent --show-error --fail "%SERVER_URL%/health" >nul 2>&1
    if !errorlevel! equ 0 (
        set "SERVER_READY=1"
        goto open_browser
    )
    timeout /T 2 /NOBREAK >nul
)

echo [WARNING] Could not confirm the server responded at %SERVER_URL%/health.
echo Please ensure the application started correctly.
goto post_launch

:open_browser
echo [SUCCESS] Server is responding. Opening %SERVER_URL% in your default browser...
start "" "%SERVER_URL%"

:post_launch
echo.
echo ================================================================
echo  Next Steps
echo ================================================================
echo 1. If the browser did not open, navigate manually to %SERVER_URL%
echo 2. If you still see "Not Secure", import mkcert-rootCA.crt from your Desktop
echo 3. Restart your browser after trusting the certificate
echo.
goto done

:cleanup_fail
set "EXIT_CODE=1"
echo.
echo ================================================================
echo  An error prevented completion of the certificate fix/launch process.
echo  Review messages above, resolve any issues, and re-run this tool.
echo ================================================================
echo.

:done
popd >nul
echo.
pause
endlocal & exit /b %EXIT_CODE%
