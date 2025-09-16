# Create or refresh the single desktop shortcut for Financial Command Center AI

$AppName = "Financial Command Center AI"
$RepoRoot = (Get-Location).Path
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$TargetScript = Join-Path $RepoRoot "ultimate_cert_fix.cmd"
$ShortcutPath = Join-Path $Desktop ("$AppName.lnk")
$IconPath = Join-Path $RepoRoot "assets\launcher_icon.ico"
$LegacyShortcuts = @(
    Join-Path $Desktop "Financial Command Center AI - Quick Start.lnk"
)

Write-Host "Preparing desktop shortcut for $AppName" -ForegroundColor Yellow
Write-Host "Target script: $TargetScript" -ForegroundColor Gray
Write-Host "Shortcut path: $ShortcutPath" -ForegroundColor Gray

if (-not (Test-Path $TargetScript)) {
    Write-Host "[ERROR] Required script 'ultimate_cert_fix.cmd' not found." -ForegroundColor Red
    Write-Host "Run this command from the project root directory." -ForegroundColor Red
    exit 1
}

foreach ($legacy in $LegacyShortcuts) {
    if (Test-Path $legacy) {
        try {
            Remove-Item $legacy -Force -ErrorAction Stop
            Write-Host "Removed legacy shortcut: $legacy" -ForegroundColor DarkGray
        } catch {
            Write-Host "Warning: Could not remove $legacy ($($_.Exception.Message))" -ForegroundColor DarkYellow
        }
    }
}

try {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetScript
    $shortcut.Arguments = ''
    $shortcut.WorkingDirectory = $RepoRoot
    $shortcut.WindowStyle = 1
    if (Test-Path $IconPath) {
        $shortcut.IconLocation = $IconPath
        Write-Host "Using icon: $IconPath" -ForegroundColor Gray
    }
    $shortcut.Save()
    Write-Host "[SUCCESS] Shortcut created/updated at $ShortcutPath" -ForegroundColor Green
    Write-Host "Double-click it to trust certs and open the browser." -ForegroundColor Cyan
} catch {
    Write-Host "[ERROR] Failed to create shortcut: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
