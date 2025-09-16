@echo off
title Financial Command Center AI - Launcher
echo.
echo ==============================================
echo  Financial Command Center AI - Starting...
echo ==============================================
echo.

REM Try the compiled launcher first
if exist "Financial-Command-Center-Launcher.exe" (
    "Financial-Command-Center-Launcher.exe"
    if not errorlevel 1 goto :success
    echo Warning: Compiled launcher failed, trying script launcher...
)

REM Fall back to script launcher
if exist "ultimate_cert_fix.cmd" (
    call "ultimate_cert_fix.cmd"
    if not errorlevel 1 goto :success
)

echo.
echo Error: Could not start Financial Command Center AI
echo Please check that all files are present and try again.
echo.
pause
goto :end

:success
echo.
echo Financial Command Center AI started successfully!
echo You can close this window.
echo.

:end
