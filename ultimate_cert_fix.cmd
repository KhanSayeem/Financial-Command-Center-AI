@echo off
setlocal enabledelayedexpansion

set "EXIT_CODE=0"
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

for %%I in ("%SCRIPT_DIR%.") do set "SCRIPT_DIR=%%~fI"

set "APP_ENTRY=%SCRIPT_DIR%\app_with_setup_wizard.py"
if not exist "%APP_ENTRY%" (
    set "APP_ENTRY=%SCRIPT_DIR%\installer_package\app_with_setup_wizard.py"
)
if not exist "%APP_ENTRY%" (
    echo [ERROR] Unable to locate app_with_setup_wizard.py near %SCRIPT_DIR%.
    echo         Ensure you extracted the full repository before running this tool.
    goto cleanup_fail
)

set "ENV_FILE=%SCRIPT_DIR%\.env"
if exist "%ENV_FILE%" (
    echo Loading environment overrides from %ENV_FILE% ...
    for /f "usebackq tokens=1* delims==" %%A in (`findstr /R "^[A-Za-z0-9_][A-Za-z0-9_]*=" "%ENV_FILE%"`) do (
        call :set_env_from_line "%%~A" "%%~B"
    )
) else (
    echo [INFO] No .env file found beside ultimate_cert_fix.cmd; relying on existing environment variables.
)

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

set "PYTHON_CMD="
set "PYTHON_ARGS="
set "PYTHON_DISPLAY="
set "VENV_PY=%SCRIPT_DIR%\.venv\Scripts\python.exe"

echo Step 0a: Ensuring Python 3.11+ runtime availability...
call :resolve_python
if errorlevel 1 (
    echo [ERROR] Unable to locate or install Python 3.11+. Please install it manually and re-run this tool.
    goto cleanup_fail
)
if defined PYTHON_ARGS (
    set "PYTHON_DISPLAY=%PYTHON_CMD% %PYTHON_ARGS%"
) else (
    set "PYTHON_DISPLAY=%PYTHON_CMD%"
)
echo  - Using Python interpreter: %PYTHON_DISPLAY%

echo.
echo Step 0b: Verifying license with license.daywinlabs.com...
call :verify_license
if errorlevel 1 goto cleanup_fail

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
if not exist "%MKCERT_ROOT%" (
    echo  - mkcert root certificate not found. Generating with cert_manager.py...
    call :run_python "%SCRIPT_DIR%\cert_manager.py" --mkcert
    if errorlevel 1 (
        echo [ERROR] Failed to generate mkcert certificates automatically.
        goto cleanup_fail
    )
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
call :run_python "%SCRIPT_DIR%\cert_manager.py" --health
if errorlevel 1 (
    echo [WARNING] Certificate health check returned issues. Review the log above for details.
)

if "!LAUNCH_MODE!"=="install" (
    echo.
    echo Step 5: Creating desktop shortcut for future quick launches...
    set "SHORTCUT_ICON=%SCRIPT_DIR%\assets\application.ico"
    if not exist "!SHORTCUT_ICON!" set "SHORTCUT_ICON=%SCRIPT_DIR%\FCC\assets\application.ico"
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
    if not exist "!SHORTCUT_ICON!" set "SHORTCUT_ICON=%SCRIPT_DIR%\FCC\assets\application.ico"
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

if exist "%VENV_PY%" (
    echo  - Using virtual environment Python at %VENV_PY%
) else (
    echo  - Virtual environment not found, using %PYTHON_DISPLAY%
)
echo  - Entrypoint: %APP_ENTRY%

if defined PYTHON_ARGS (
    start "Financial Command Center Server" /MIN "%PYTHON_CMD%" %PYTHON_ARGS% "%APP_ENTRY%"
) else (
    start "Financial Command Center Server" /MIN "%PYTHON_CMD%" "%APP_ENTRY%"
)

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

:: ------------------------------------------------------------------
:: Helper routines
:: ------------------------------------------------------------------
:run_python
setlocal EnableExtensions EnableDelayedExpansion
set "SCRIPT_PATH=%~f1"
shift
set "ARGS="
:run_python_collect
if "%~1"=="" goto run_python_exec
if defined ARGS (
    set "ARGS=!ARGS! "%~1""
) else (
    set "ARGS="%~1""
)
shift
goto run_python_collect
:run_python_exec
if defined PYTHON_ARGS (
    if defined ARGS (
        call "%PYTHON_CMD%" %PYTHON_ARGS% "%SCRIPT_PATH%" !ARGS!
    ) else (
        call "%PYTHON_CMD%" %PYTHON_ARGS% "%SCRIPT_PATH%"
    )
) else (
    if defined ARGS (
        call "%PYTHON_CMD%" "%SCRIPT_PATH%" !ARGS!
    ) else (
        call "%PYTHON_CMD%" "%SCRIPT_PATH%"
    )
)
set "RPCODE=%errorlevel%"
endlocal & exit /b %RPCODE%

:verify_license
echo  - Contacting license server to validate entitlement...
call :run_python "%SCRIPT_DIR%\license_manager.py" --verify --stateless
set "LIC_RC=%errorlevel%"
if not "%LIC_RC%"=="0" (
    echo [ERROR] License verification failed or was cancelled.
)
exit /b %LIC_RC%

:resolve_python
set "RESOLVED_CMD="
set "RESOLVED_ARGS="
if exist "%VENV_PY%" (
    set "RESOLVED_CMD=%VENV_PY%"
    goto resolve_python_done
)
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined RESOLVED_CMD set "RESOLVED_CMD=%%P"
)
if defined RESOLVED_CMD goto resolve_python_done
set "LOCAL_PY_BASE=%USERPROFILE%\AppData\Local\Programs\Python"
for /f "delims=" %%D in ('dir /b /ad "%LOCAL_PY_BASE%\Python3*" 2^>nul ^| sort /R') do (
    if not defined RESOLVED_CMD (
        if exist "%LOCAL_PY_BASE%\%%D\python.exe" set "RESOLVED_CMD=%LOCAL_PY_BASE%\%%D\python.exe"
    )
)
if defined RESOLVED_CMD goto resolve_python_done
for /f "delims=" %%P in ('where py 2^>nul') do (
    if not defined RESOLVED_CMD (
        set "RESOLVED_CMD=%%P"
        set "RESOLVED_ARGS=-3"
    )
)
if defined RESOLVED_CMD goto resolve_python_done
call :install_python
if errorlevel 1 exit /b 1
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined RESOLVED_CMD set "RESOLVED_CMD=%%P"
)
if defined RESOLVED_CMD goto resolve_python_done
for /f "delims=" %%D in ('dir /b /ad "%LOCAL_PY_BASE%\Python3*" 2^>nul ^| sort /R') do (
    if not defined RESOLVED_CMD (
        if exist "%LOCAL_PY_BASE%\%%D\python.exe" set "RESOLVED_CMD=%LOCAL_PY_BASE%\%%D\python.exe"
    )
)
if defined RESOLVED_CMD goto resolve_python_done
for /f "delims=" %%P in ('where py 2^>nul') do (
    if not defined RESOLVED_CMD (
        set "RESOLVED_CMD=%%P"
        set "RESOLVED_ARGS=-3"
    )
)
if not defined RESOLVED_CMD exit /b 1

:resolve_python_done
set "PYTHON_CMD=%RESOLVED_CMD%"
set "PYTHON_ARGS=%RESOLVED_ARGS%"
exit /b 0

:install_python
setlocal
set "PY_TMP=%TEMP%\python311-installer.exe"
set "PY_URL=https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe"
echo  - Python not detected. Downloading installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri $env:PY_URL -OutFile $env:PY_TMP -UseBasicParsing"
if errorlevel 1 (
    echo [ERROR] Failed to download Python installer from %PY_URL%.
    del /f /q "%PY_TMP%" >nul 2>&1
    endlocal & exit /b 1
)
echo  - Installing Python (per-user)...
start /wait "" "%PY_TMP%" /quiet InstallAllUsers=0 Include_test=0 Include_launcher=1 Include_pip=1 PrependPath=1
set "INSTALL_RC=%errorlevel%"
del /f /q "%PY_TMP%" >nul 2>&1
if not "%INSTALL_RC%"=="0" (
    echo [ERROR] Python installer returned exit code %INSTALL_RC%.
    endlocal & exit /b 1
)
endlocal & exit /b 0

:set_env_from_line
setlocal EnableDelayedExpansion
set "NAME=%~1"
set "VALUE=%~2"
if defined VALUE (
    if "!VALUE:~0,1!"=="\"" if "!VALUE:~-1!"=="\"" set "VALUE=!VALUE:~1,-1!"
)
endlocal & set "%NAME%=%VALUE%"
exit /b 0

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
