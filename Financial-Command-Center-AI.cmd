@echo off
setlocal

title Financial Command Center AI - Unified Launcher
echo ===============================================
echo   Financial Command Center AI - Unified Launcher
echo ===============================================
echo.

pushd "%~dp0" >nul

echo Creating/refreshing desktop shortcut (if needed)...
call "%~dp0Create-Desktop-Shortcut.cmd" >nul 2>&1
echo.
echo Launching Ultimate Certificate Fix + Browser Helper...
call "%~dp0ultimate_cert_fix.cmd"

popd >nul
endlocal
