@echo off
REM Simple Desktop Shortcut Creator for Financial Command Center AI
REM This creates a shortcut that uses the reliable batch script approach

set "APP_NAME=Financial Command Center AI - Quick Start"
set "CURRENT_DIR=%cd%"
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT_PATH=%DESKTOP%\%APP_NAME%.lnk"
set "BATCH_SCRIPT=%CURRENT_DIR%\Quick-Start-Flask.cmd"
set "ICON_PATH=%CURRENT_DIR%\assets\launcher_icon.ico"

echo Creating desktop shortcut for Financial Command Center AI...
echo.
echo Script location: %BATCH_SCRIPT%
echo Shortcut will be created at: %SHORTCUT_PATH%

REM Check if Quick-Start-Flask.cmd exists
if not exist "%BATCH_SCRIPT%" (
    echo ERROR: Quick-Start-Flask.cmd not found!
    echo Please ensure the file exists in the current directory.
    pause
    exit /b 1
)

REM Create shortcut using PowerShell (this part always works)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); ^
$s.TargetPath='%BATCH_SCRIPT%'; ^
$s.WorkingDirectory='%CURRENT_DIR%'; ^
$s.WindowStyle=1; ^
if (Test-Path '%ICON_PATH%') { $s.IconLocation='%ICON_PATH%' }; ^
$s.Save();"

if exist "%SHORTCUT_PATH%" (
    echo.
    echo [SUCCESS] Desktop shortcut created successfully!
    echo.
    echo The shortcut '%APP_NAME%' is now on your desktop.
    echo Double-click it to launch Financial Command Center on https://127.0.0.1:8000
    echo.
    echo The shortcut will:
    echo - Start Flask server on HTTPS port 8000
    echo - Open your browser automatically
    echo - Run the server in the background
    echo.
) else (
    echo.
    echo [ERROR] Failed to create desktop shortcut.
    echo Please check permissions and try running as administrator.
    echo.
    pause
)

timeout /t 3 /nobreak >nul