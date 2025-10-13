@echo off
REM Create a single desktop shortcut that points to ultimate_cert_fix.cmd
setlocal

set "APP_NAME=FCC"
set "CURRENT_DIR=%cd%"
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT_PATH=%DESKTOP%\%APP_NAME%.lnk"
set "TARGET_SCRIPT=%CURRENT_DIR%\ultimate_cert_fix.cmd"
set "ICON_PATH="
set "LEGACY_SHORTCUT=%DESKTOP%\Financial Command Center AI - Quick Start.lnk"

set "ICON_PATH=%CURRENT_DIR%\assets\application.ico"
if not exist "%ICON_PATH%" set "ICON_PATH=%CURRENT_DIR%\installer_package\assets\application.ico"
if not exist "%ICON_PATH%" set "ICON_PATH="

echo Creating desktop shortcut for %APP_NAME%...
echo Current directory: %CURRENT_DIR%
echo Target script: %TARGET_SCRIPT%
echo Icon path: %ICON_PATH%

if not exist "%TARGET_SCRIPT%" (
    echo [ERROR] Required launcher script not found: %TARGET_SCRIPT%
    echo Please run this command from the project root directory.
    goto done
)

REM Remove legacy shortcut if present
if exist "%LEGACY_SHORTCUT%" (
    del /f /q "%LEGACY_SHORTCUT%" >nul 2>&1
)

echo Checking icon path: %ICON_PATH%
if exist "%ICON_PATH%" (
    echo [INFO] Icon file found at: %ICON_PATH%
) else (
    echo [WARNING] Icon file not found at: %ICON_PATH%
)

echo Creating shortcut with PowerShell...
echo PowerShell command: powershell -NoProfile -ExecutionPolicy Bypass -File "%CURRENT_DIR%\create_shortcut.ps1" -ShortcutPath "%SHORTCUT_PATH%" -TargetPath "%TARGET_SCRIPT%" -WorkingDirectory "%CURRENT_DIR%" -IconPath "%ICON_PATH%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%CURRENT_DIR%\create_shortcut.ps1" ^
    -ShortcutPath "%SHORTCUT_PATH%" ^
    -TargetPath "%TARGET_SCRIPT%" ^
    -WorkingDirectory "%CURRENT_DIR%" ^
    -IconPath "%ICON_PATH%"
echo PowerShell execution completed with exit code: %ERRORLEVEL%

if exist "%SHORTCUT_PATH%" (
    echo [SUCCESS] Desktop shortcut created at:
    echo  %SHORTCUT_PATH%
    echo.
    echo Double-click it any time to fix certificates and launch the app.
) else (
    echo [ERROR] Failed to create the desktop shortcut.
    echo Try running this script from an elevated command prompt.
)

:done
echo.
timeout /T 3 /NOBREAK >nul
endlocal
