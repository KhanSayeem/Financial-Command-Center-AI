# Quick Start Flask App - Financial Command Center AI
# This script directly launches the Flask app on https://127.0.0.1:8000

$Host.UI.RawUI.WindowTitle = "Financial Command Center AI - Quick Start"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "    Financial Command Center AI - Quick Start" -ForegroundColor Cyan  
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run the full installer first: Financial-Command-Center-Launcher.exe" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Set environment variables for clean startup  
$env:FLASK_ENV = "production"
$env:FORCE_HTTPS = "true"
$env:ALLOW_HTTP = "false"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:APP_MODE = "demo"
$env:FCC_PORT = "8000"

Write-Host "Starting Flask server on https://127.0.0.1:8000..." -ForegroundColor Green
Write-Host ""
Write-Host "The server will start automatically." -ForegroundColor White
Write-Host "Once running, your web browser will open the application." -ForegroundColor White
Write-Host ""

# Start Flask app in background
Write-Host "Launching Flask application..." -ForegroundColor Yellow
$process = Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "app_with_setup_wizard.py" -WindowStyle Minimized -PassThru

# Wait a few seconds for server to start
Write-Host "Waiting for server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 6

# Check if server is running
Write-Host "Testing server connection..." -ForegroundColor Yellow
try {
    # Ignore SSL certificate errors for self-signed certificates
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}
    $response = Invoke-WebRequest -Uri "https://127.0.0.1:8000/health" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "[SUCCESS] Server is running successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Opening https://127.0.0.1:8000 in your browser..." -ForegroundColor Cyan
        Start-Process "https://127.0.0.1:8000"
        Write-Host ""
        Write-Host "Server is now running in the background." -ForegroundColor Green
        Write-Host "Process ID: $($process.Id)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "You can close this window - the server will continue running." -ForegroundColor Yellow
        Write-Host "To stop the server, use Task Manager to end the Python process." -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Server failed to start or is not responding." -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please check the logs and try running the full installer instead." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Keep window open briefly then minimize
Start-Sleep -Seconds 3