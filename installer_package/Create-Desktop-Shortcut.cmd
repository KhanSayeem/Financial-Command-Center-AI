@echo off
REM Create a single desktop shortcut that points to ultimate_cert_fix.cmd (installer payload)
setlocal

set "APP_NAME=Financial Command Center AI"
set "CURRENT_DIR=%cd%"
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT_PATH=%DESKTOP%\%APP_NAME%.lnk"
set "TARGET_SCRIPT=%CURRENT_DIR%\ultimate_cert_fix.cmd"
set "ICON_PATH=%CURRENT_DIR%\assets\launcher_icon.ico"
set "LEGACY_SHORTCUT=%DESKTOP%\Financial Command Center AI - Quick Start.lnk"

echo Creating desktop shortcut for %APP_NAME%...

if not exist "%TARGET_SCRIPT%" (
    echo [ERROR] Required launcher script not found: %TARGET_SCRIPT%
    echo Please run this command from the installed application directory.
    goto done
)

if exist "%LEGACY_SHORTCUT%" (
    del /f /q "%LEGACY_SHORTCUT%" >nul 2>&1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$shortcutPath = '%SHORTCUT_PATH%'; $shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut($shortcutPath); $shortcut.TargetPath = '%TARGET_SCRIPT%'; $shortcut.WorkingDirectory = '%CURRENT_DIR%'; $shortcut.WindowStyle = 1; if (Test-Path '%ICON_PATH%') { $shortcut.IconLocation = '%ICON_PATH%' }; $shortcut.Save();"

if exist "%SHORTCUT_PATH%" (
    echo [SUCCESS] Desktop shortcut created at:
    echo  %SHORTCUT_PATH%
) else (
    echo [ERROR] Failed to create the desktop shortcut.
)

:done
echo.
timeout /T 3 /NOBREAK >nul
endlocal
