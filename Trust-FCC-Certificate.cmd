@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "TRUST_HELPER=%SCRIPT_DIR%trust_fcc_cert.ps1"

if not exist "%TRUST_HELPER%" (
    echo [ERROR] trust_fcc_cert.ps1 not found beside this file.
    exit /b 1
)

echo This will install the FCC root certificate into Trusted Root stores.
echo You may see a Windows security prompt. Please click Yes/Allow.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Start-Process powershell.exe -Verb RunAs -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File','\"%TRUST_HELPER%\"')"

if errorlevel 1 (
    echo [WARNING] The trust helper did not start. Run this as Administrator.
) else (
    echo A trust window should have appeared. If prompted, click Yes/Allow.
)

echo.
pause
endlocal
