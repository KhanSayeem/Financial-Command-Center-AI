@echo off
REM Create a single desktop shortcut that points to ultimate_cert_fix.cmd
setlocal

set "APP_NAME=Financial Command Center AI"
set "CURRENT_DIR=%cd%"
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT_PATH=%DESKTOP%\%APP_NAME%.lnk"
set "TARGET_SCRIPT=%CURRENT_DIR%\ultimate_cert_fix.cmd"
set "ICON_PATH=%CURRENT_DIR%\installer_package\assets\launcher_icon.ico"
set "LEGACY_SHORTCUT=%DESKTOP%\Financial Command Center AI - Quick Start.lnk"

echo Creating desktop shortcut for %APP_NAME%...

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
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { $shortcutPath = '%SHORTCUT_PATH%'; $shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut($shortcutPath); $shortcut.TargetPath = '%TARGET_SCRIPT%'; $shortcut.WorkingDirectory = '%CURRENT_DIR%'.ToString(); $shortcut.WindowStyle = 1; if (Test-Path '%ICON_PATH%') { $shortcut.IconLocation = '%ICON_PATH%'; Write-Host 'Icon set to: %ICON_PATH%' } else { Write-Host 'Warning: Icon not found at %ICON_PATH%' }; $shortcut.Save(); Write-Host 'Shortcut saved successfully' } catch { Write-Host 'Error creating shortcut:' $_.Exception.Message; exit 1 }"

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
