# Create Quick Start Shortcut for Financial Command Center AI
# This creates a desktop shortcut that directly launches the Flask app

$AppName = "Financial Command Center AI - Quick Start"
$RepoRoot = (Get-Location).Path
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$QuickStartScript = Join-Path $RepoRoot "Quick-Start-Flask.ps1"
$IconPath = Join-Path $RepoRoot "assets\launcher_icon.ico"

# Create shortcut path
$ShortcutPath = Join-Path $Desktop "$AppName.lnk"

Write-Host "Creating Quick Start shortcut..." -ForegroundColor Yellow
Write-Host "Script location: $QuickStartScript" -ForegroundColor Gray
Write-Host "Shortcut will be created at: $ShortcutPath" -ForegroundColor Gray

try {
    # Create WScript.Shell COM object
    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
    
    # Set shortcut properties
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$QuickStartScript`""
    $Shortcut.WorkingDirectory = $RepoRoot
    $Shortcut.WindowStyle = 7  # Minimized window
    
    # Set icon if it exists
    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = $IconPath
        Write-Host "Using icon: $IconPath" -ForegroundColor Gray
    } else {
        Write-Host "Icon not found, using default" -ForegroundColor Yellow
    }
    
    # Save shortcut
    $Shortcut.Save()
    
    Write-Host "[SUCCESS] Quick Start shortcut created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "The shortcut '$AppName' is now on your desktop." -ForegroundColor Cyan
    Write-Host "Double-click it to quickly launch the Flask app on https://127.0.0.1:8000" -ForegroundColor White
    
} catch {
    Write-Host "[ERROR] Failed to create shortcut: $($_.Exception.Message)" -ForegroundColor Red
}