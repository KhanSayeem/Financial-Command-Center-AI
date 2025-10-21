@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%.") do set "SCRIPT_DIR=%%~fI"
set "REPO_ROOT=%SCRIPT_DIR%\.."

if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%REPO_ROOT%\.venv\Scripts\python.exe"
) else (
    for %%P in (python.exe python) do (
        for /f "delims=" %%X in ('where %%P 2^>nul') do (
            if not defined PYTHON_CMD set "PYTHON_CMD=%%X"
        )
    )
)

if not defined PYTHON_CMD (
    echo Python 3.11+ not found on PATH. Install Python or run bootstrap-install.cmd first.
    exit /b 1
)

if "%~1"=="" (
    "%PYTHON_CMD%" -m bootstrap install
) else (
    "%PYTHON_CMD%" -m bootstrap %*
)

set "EXIT_CODE=%errorlevel%"
endlocal & exit /b %EXIT_CODE%

