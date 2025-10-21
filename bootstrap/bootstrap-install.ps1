$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot = Join-Path $scriptDir '..'

# Auto-elevate if not running as Administrator
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    $argList = @(
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`""
    )
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $argList
    exit
}

Set-Location $repoRoot

# Prefer the project's virtualenv python if it exists after install
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -m bootstrap install --no-launch
} else {
    & python -m bootstrap install --no-launch
}
