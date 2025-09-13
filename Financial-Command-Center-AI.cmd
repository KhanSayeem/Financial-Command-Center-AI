@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Financial Command Center AI - Enhanced Launcher with Shortcut Creation
REM This script creates a desktop shortcut on first run and ensures HTTPS launch

title Financial Command Center AI - Setup ^& Launch
echo ===============================================
echo     Financial Command Center AI - Launcher
echo ===============================================
echo.

REM Change to this script's directory
pushd "%~dp0"

REM Check if this is first run by looking for desktop shortcut
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT_NAME=Financial Command Center AI - Quick Start"
set "SHORTCUT_PATH=%DESKTOP%\%SHORTCUT_NAME%.lnk"
set "FIRST_RUN=0"

if not exist "%SHORTCUT_PATH%" (
    set "FIRST_RUN=1"
    echo This appears to be your first time running Financial Command Center AI.
    echo We'll create a desktop shortcut for easy future access.
    echo.
)

REM Prefer pythonw to avoid console window for regular runs, but use python for setup
set "PY_EXE="
set "SETUP_PY_EXE="
if exist ".venv\Scripts\pythonw.exe" (
    set "PY_EXE=.venv\Scripts\pythonw.exe"
    set "SETUP_PY_EXE=.venv\Scripts\python.exe"
)
if not defined PY_EXE (
  for %%P in (pyw.exe pythonw.exe) do (
    where %%P >nul 2>&1 && set "PY_EXE=%%P" && goto :gotpy
  )
)
:gotpy
if not defined PY_EXE (
  echo pythonw.exe not found. Trying console python...
  for %%P in (py.exe python.exe) do (
    where %%P >nul 2>&1 && set "PY_EXE=%%P" && set "SETUP_PY_EXE=%%P" && goto :gotpy2
  )
)
:gotpy2
if not defined PY_EXE (
  echo ERROR: Could not find Python. Please install Python 3.8+ and try again.
  echo.
  pause
  popd
  endlocal
  exit /b 1
)

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run the full installer first to set up the environment.
    echo.
    echo You can download the installer from:
    echo https://github.com/KhanSayeem/Financial-Command-Center-AI
    echo.
    pause
    popd
    endlocal
    exit /b 1
)

REM If this is first run, create the desktop shortcut
if %FIRST_RUN%==1 (
    echo Creating desktop shortcut for easy future access...
    call :CreateShortcut
    echo.
)

REM Determine which app to run (prefer setup wizard version)
set "APP=app_with_setup_wizard.py"
if not exist "%APP%" (
    set "APP=app.py"
)
if not exist "%APP%" (
    echo ERROR: Could not find application file: %APP%
    echo Please ensure the installation is complete.
    pause
    popd
    endlocal
    exit /b 1
)

REM Set environment variables to ensure HTTPS on 127.0.0.1:8000
set FLASK_ENV=production
set FORCE_HTTPS=true
set ALLOW_HTTP=false
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set APP_MODE=demo
set FCC_PORT=8000

echo Starting Financial Command Center on https://127.0.0.1:8000...
echo.

if %FIRST_RUN%==1 (
    echo This will:
    echo - Start the Flask server on port 8000 with HTTPS
    echo - Open your web browser to https://127.0.0.1:8000
    echo - Create a desktop shortcut for future quick access
    echo.
    echo For future launches, just double-click the desktop shortcut!
    echo.
) else (
    echo Starting Flask server...
    echo Your browser will open automatically to https://127.0.0.1:8000
    echo.
)

REM Launch the application with proper environment
if %FIRST_RUN%==1 (
    REM For first run, show console output so user can see what's happening
    "%SETUP_PY_EXE%" "%APP%"
) else (
    REM For subsequent runs, run minimized
    start "Financial Command Center AI" /B "%PY_EXE%" "%APP%"
    
    REM Wait a moment then open browser
    timeout /t 3 /nobreak >nul
    
    REM Test if server is running and open browser
    curl -k -I https://127.0.0.1:8000/health >nul 2>&1
    if !errorlevel! equ 0 (
        echo [SUCCESS] Server is running! Opening browser...
        start https://127.0.0.1:8000
    ) else (
        echo [INFO] Server starting... Please wait a moment then visit https://127.0.0.1:8000
    )
)

REM Clean exit
popd
endlocal
exit /b 0

:CreateShortcut
REM Function to create desktop shortcut using PowerShell
echo Creating desktop shortcut...

REM Get current directory and script paths
set "CURRENT_DIR=%cd%"
set "QUICK_START_SCRIPT=%CURRENT_DIR%\Quick-Start-Flask.ps1"
set "ICON_PATH=%CURRENT_DIR%\assets\launcher_icon.ico"

REM Check if Quick-Start-Flask.ps1 exists, if not create it
if not exist "%QUICK_START_SCRIPT%" (
    echo Quick Start script not found. Creating it...
    call :CreateQuickStartScript
)

REM Create shortcut using PowerShell (targeting batch script for reliability)
set "BATCH_SCRIPT=%CURRENT_DIR%\Quick-Start-Flask.cmd"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath='%BATCH_SCRIPT%'; $s.WorkingDirectory='%CURRENT_DIR%'; $s.WindowStyle=1; if (Test-Path '%ICON_PATH%') { $s.IconLocation='%ICON_PATH%' }; $s.Save();"

if exist "%SHORTCUT_PATH%" (
    echo [SUCCESS] Desktop shortcut created: %SHORTCUT_NAME%
    echo You can now use this shortcut for quick future launches!
) else (
    echo [WARNING] Could not create desktop shortcut. You can still use this script.
)
goto :eof

:CreateQuickStartScript
REM Create the Quick-Start-Flask.ps1 script if it doesn't exist
echo Creating Quick Start PowerShell script...
(
echo # Quick Start Flask App - Financial Command Center AI
echo # Auto-generated by Financial-Command-Center-AI.cmd
echo.
echo $Host.UI.RawUI.WindowTitle = "Financial Command Center AI - Quick Start"
echo.
echo Write-Host "===============================================" -ForegroundColor Cyan
echo Write-Host "    Financial Command Center AI - Quick Start" -ForegroundColor Cyan
echo Write-Host "===============================================" -ForegroundColor Cyan
echo Write-Host ""
echo.
echo # Check if virtual environment exists
echo if ^(-not ^(Test-Path ".venv\Scripts\python.exe"^)^) {
echo     Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
echo     Write-Host "Please run the full installer first" -ForegroundColor Yellow
echo     Read-Host "Press Enter to exit"
echo     exit 1
echo }
echo.
echo # Set environment variables
echo $env:FLASK_ENV = "production"
echo $env:FORCE_HTTPS = "true"
echo $env:ALLOW_HTTP = "false"
echo $env:PYTHONUTF8 = "1"
echo $env:PYTHONIOENCODING = "utf-8"
echo $env:APP_MODE = "demo"
echo $env:FCC_PORT = "8000"
echo.
echo Write-Host "Starting Flask server on https://127.0.0.1:8000..." -ForegroundColor Green
echo Write-Host "Please wait while the server starts..." -ForegroundColor Yellow
echo.
echo # Start Flask app in background
echo $process = Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "app_with_setup_wizard.py" -WindowStyle Minimized -PassThru
echo.
echo # Wait for server to start
echo Start-Sleep -Seconds 6
echo.
echo # Test server and open browser
echo try {
echo     # Ignore SSL certificate errors for self-signed certificates
echo     [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}
echo     $response = Invoke-WebRequest -Uri "https://127.0.0.1:8000/health" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
echo     if ^($response.StatusCode -eq 200^) {
echo         Write-Host "[SUCCESS] Server is running!" -ForegroundColor Green
echo         Write-Host "Opening https://127.0.0.1:8000 in browser..." -ForegroundColor Cyan
echo         Start-Process "https://127.0.0.1:8000"
echo         Write-Host "Server is running in background. You can close this window." -ForegroundColor Yellow
echo     }
echo } catch {
echo     Write-Host "[ERROR] Server not responding. Please check the installation." -ForegroundColor Red
echo     Read-Host "Press Enter to exit"
echo }
echo.
echo Start-Sleep -Seconds 3
) > "%QUICK_START_SCRIPT%"

if exist "%QUICK_START_SCRIPT%" (
    echo [SUCCESS] Quick Start script created
) else (
    echo [WARNING] Could not create Quick Start script
)
goto :eof