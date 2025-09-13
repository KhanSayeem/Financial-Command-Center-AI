@echo off
REM Quick Start Flask App - Financial Command Center AI
REM This script directly launches the Flask app on https://127.0.0.1:8000

title Financial Command Center AI - Quick Start
echo ===============================================
echo     Financial Command Center AI - Quick Start
echo ===============================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run the full installer first: Financial-Command-Center-Launcher.exe
    echo.
    pause
    exit /b 1
)

REM Set environment variables for clean startup
set FLASK_ENV=production
set FORCE_HTTPS=true
set ALLOW_HTTP=false
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set APP_MODE=demo
set FCC_PORT=8000

echo Starting Flask server on https://127.0.0.1:8000...
echo.
echo The server will start automatically.
echo Once running, your web browser will open the application.
echo.

REM Start Flask app in background
start "Financial Command Center Flask" /B /MIN .venv\Scripts\python.exe app_with_setup_wizard.py

REM Wait a few seconds for server to start
echo Waiting for server to start...
timeout /t 5 /nobreak >nul

REM Check if server is running by attempting connection
echo Testing server connection...
curl -k -I https://127.0.0.1:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Server is running successfully!
    echo.
    echo Opening https://127.0.0.1:8000 in your browser...
    start https://127.0.0.1:8000
    echo.
    echo Server is now running in the background.
    echo You can close this window - the server will continue running.
    echo To stop the server, use Task Manager to end the Python process.
) else (
    echo [ERROR] Server failed to start or is not responding.
    echo Please check the logs and try running the full installer instead.
    echo.
    pause
)

REM Keep window open briefly
timeout /t 3 /nobreak >nul