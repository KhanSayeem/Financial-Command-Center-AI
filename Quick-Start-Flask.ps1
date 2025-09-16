# Legacy wrapper that now calls the consolidated ultimate_cert_fix.cmd launcher
$script = Join-Path $PSScriptRoot "ultimate_cert_fix.cmd"
if (-not (Test-Path $script)) {
    Write-Error "ultimate_cert_fix.cmd is missing. Please ensure you are running from the project root."
    exit 1
}
& $script
