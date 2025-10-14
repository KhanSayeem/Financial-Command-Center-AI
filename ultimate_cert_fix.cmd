@echo off
setlocal enabledelayedexpansion

set "EXIT_CODE=0"
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

for %%I in ("%SCRIPT_DIR%.") do set "SCRIPT_DIR=%%~fI"

set "INSTALL_FLAG_FILE=%SCRIPT_DIR%\.fcc_installed"

:: Resolve the actual Desktop path (handles OneDrive or custom locations)
set "DESKTOP_DIR="
for /f "usebackq delims=" %%D in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::GetFolderPath('Desktop')"`) do (
    if not defined DESKTOP_DIR set "DESKTOP_DIR=%%D"
)
if not defined DESKTOP_DIR (
    if exist "%USERPROFILE%\Desktop" (
        set "DESKTOP_DIR=%USERPROFILE%\Desktop"
    ) else (
        if exist "%USERPROFILE%\OneDrive\Desktop" (
            set "DESKTOP_DIR=%USERPROFILE%\OneDrive\Desktop"
        ) else (
            set "DESKTOP_DIR=%USERPROFILE%\Desktop"
        )
    )
)
if not exist "%DESKTOP_DIR%" (
    mkdir "%DESKTOP_DIR%" >nul 2>&1
)
set "DESKTOP_SHORTCUT=%DESKTOP_DIR%\FCC.lnk"

if exist "%INSTALL_FLAG_FILE%" (
    if exist "%DESKTOP_SHORTCUT%" (
        set "LAUNCH_MODE=quick"
        echo.
        echo ================================================================
        echo  QUICK LAUNCHER - Financial Command Center AI
        echo ================================================================
        echo.
    ) else (
        set "LAUNCH_MODE=repair"
        echo.
        echo ================================================================
        echo  REPAIR MODE - Financial Command Center AI
        echo ================================================================
        echo.
    )
) else (
    set "LAUNCH_MODE=install"
    echo.
    echo ================================================================
    echo  INSTALLER - Financial Command Center AI (First Time Setup)
    echo ================================================================
    echo.
)

if not defined LOCALAPPDATA (
    set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
)
set "MKCERT_ROOT=%LOCALAPPDATA%\mkcert\rootCA.pem"
set "DESKTOP_CERT=%DESKTOP_DIR%\mkcert-rootCA.crt"

echo Step 1: Closing previous Financial Command Center Python processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$repo = Convert-Path $env:SCRIPT_DIR; $procs = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'python' -and $_.Path -and $_.Path.StartsWith($repo, [System.StringComparison]::OrdinalIgnoreCase) }; if ($procs) { $procs | ForEach-Object { Write-Host (' - Stopping PID {0}' -f $_.Id) -ForegroundColor Yellow; try { $_ | Stop-Process -Force -ErrorAction Stop } catch { Write-Host ('   Warning: ' + $_.Exception.Message) -ForegroundColor DarkYellow } } } else { Write-Host ' - No running repo python processes found.' -ForegroundColor DarkGray }"

if "!LAUNCH_MODE!"=="quick" (
    echo.
    echo Skipping certificate setup - Quick launch mode enabled.
    goto launch_app
)

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

if "!LAUNCH_MODE!"=="install" (
    echo.
    echo Step 5: Creating desktop shortcut for future quick launches...
    set "SHORTCUT_ICON=%SCRIPT_DIR%\assets\application.ico"
    if not exist "!SHORTCUT_ICON!" set "SHORTCUT_ICON=%SCRIPT_DIR%\installer_package\assets\application.ico"
    if exist "!SHORTCUT_ICON!" (
        echo  - Using shortcut icon: !SHORTCUT_ICON!
    ) else (
        echo  - No custom icon found, default icon will be used
    )
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\create_shortcut.ps1" ^
        -ShortcutPath "%DESKTOP_SHORTCUT%" ^
        -TargetPath "%SCRIPT_DIR%\ultimate_cert_fix.cmd" ^
        -WorkingDirectory "%SCRIPT_DIR%" ^
        -IconPath "!SHORTCUT_ICON!"
    if exist "%DESKTOP_SHORTCUT%" (
        echo  - Desktop shortcut created successfully
        echo  - Use the desktop shortcut for quick launches in the future
    ) else (
        echo  - Warning: Could not create desktop shortcut
        echo  - Try running as administrator if the issue persists
    )

    echo %DATE% %TIME% > "%INSTALL_FLAG_FILE%"
    echo  - Installation flag file created
)

if "!LAUNCH_MODE!"=="repair" (
    echo.
    echo Step 5: Recreating desktop shortcut...
    set "SHORTCUT_ICON=%SCRIPT_DIR%\assets\application.ico"
    if not exist "!SHORTCUT_ICON!" set "SHORTCUT_ICON=%SCRIPT_DIR%\installer_package\assets\application.ico"
    if exist "!SHORTCUT_ICON!" (
        echo  - Using shortcut icon: !SHORTCUT_ICON!
    ) else (
        echo  - No custom icon found, default icon will be used
    )
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\create_shortcut.ps1" ^
        -ShortcutPath "%DESKTOP_SHORTCUT%" ^
        -TargetPath "%SCRIPT_DIR%\ultimate_cert_fix.cmd" ^
        -WorkingDirectory "%SCRIPT_DIR%" ^
        -IconPath "!SHORTCUT_ICON!"
    if exist "%DESKTOP_SHORTCUT%" (
        echo  - Desktop shortcut recreated successfully
    ) else (
        echo  - Warning: Could not recreate desktop shortcut
    )
)

:launch_app
echo.
echo Step 6: Launching Financial Command Center...
set "FCC_HOST=127.0.0.1"
if not defined FCC_PORT set "FCC_PORT=8000"
set "SERVER_URL=https://%FCC_HOST%:%FCC_PORT%"

set "FLASK_ENV=production"
set "FORCE_HTTPS=true"
set "ALLOW_HTTP=false"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "APP_MODE=demo"
set "XERO_REDIRECT_HOST=localhost"
set "ASSISTANT_MODEL_TYPE=llama32"
set "USE_LLAMA32=true"

if "!LAUNCH_MODE!"=="quick" (
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
)

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
if "!LAUNCH_MODE!"=="install" (
    echo INSTALLATION COMPLETE!
    echo.
    echo 1. A desktop shortcut has been created for quick future launches
    echo 2. If the browser did not open, navigate manually to %SERVER_URL%
    echo 3. If you still see "Not Secure", import mkcert-rootCA.crt from your Desktop
    echo 4. Restart your browser after trusting the certificate
    echo.
    echo IMPORTANT: Next time, just double-click the desktop shortcut for instant launch!
) else if "!LAUNCH_MODE!"=="quick" (
    echo QUICK LAUNCH COMPLETE!
    echo.
    echo 1. If the browser did not open, navigate manually to %SERVER_URL%
    echo 2. The app should start much faster in quick launch mode
) else (
    echo REPAIR COMPLETE!
    echo.
    echo 1. Desktop shortcut has been recreated
    echo 2. If the browser did not open, navigate manually to %SERVER_URL%
    echo 3. If you still see certificate issues, delete .fcc_installed and run again for full setup
)
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
