param(
    [string]$CertPath,
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

function Resolve-CertPath {
    param([string]$PathCandidate)

    $candidates = @()
    if ($PathCandidate) { $candidates += $PathCandidate }
    if ($env:MKCERT_ROOT) { $candidates += $env:MKCERT_ROOT }
    if ($env:DESKTOP_CERT) { $candidates += $env:DESKTOP_CERT }

    $desktop = [Environment]::GetFolderPath('Desktop')
    if ($desktop) { $candidates += (Join-Path $desktop "mkcert-rootCA.crt") }

    $candidates += (Join-Path $PSScriptRoot "certs\ca.crt")
    $candidates += (Join-Path $PSScriptRoot "certs\server.crt")

    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate)
        }
    }

    throw "Could not find a certificate file to trust. Tried: $($candidates -join ', ')"
}

function Ensure-Admin {
    param([string]$ResolvedCert, [switch]$SilentMode)

    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)

    if (-not $isAdmin) {
        if (-not $SilentMode) { Write-Host "Requesting elevation to install certificate trust..." -ForegroundColor Yellow }
        $args = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$($MyInvocation.MyCommand.Path)`"",
            "-CertPath", "`"$ResolvedCert`"",
            "-Silent"
        )
        $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $args -Verb RunAs -Wait -PassThru
        exit $proc.ExitCode
    }
}

try {
    $resolved = Resolve-CertPath -PathCandidate $CertPath
} catch {
    if (-not $Silent) { Write-Host $_.Exception.Message -ForegroundColor Red }
    exit 1
}

Ensure-Admin -ResolvedCert $resolved -SilentMode:$Silent

$errors = 0

try {
    Import-Certificate -FilePath $resolved -CertStoreLocation 'Cert:\LocalMachine\Root' -ErrorAction Stop | Out-Null
    if (-not $Silent) { Write-Host "Installed certificate to Local Machine Root." -ForegroundColor Green }
} catch {
    $errors++
    if (-not $Silent) { Write-Host "Could not install to Local Machine Root (trying certutil fallback): $($_.Exception.Message)" -ForegroundColor Yellow }
    try {
        certutil.exe -f -addstore "Root" $resolved | Out-Null
        if (-not $Silent) { Write-Host "Installed via certutil to Local Machine Root." -ForegroundColor Green }
        $errors--
    } catch {
        if (-not $Silent) { Write-Host "certutil fallback failed for Local Machine: $($_.Exception.Message)" -ForegroundColor Red }
    }
}

try {
    Import-Certificate -FilePath $resolved -CertStoreLocation 'Cert:\CurrentUser\Root' -ErrorAction Stop | Out-Null
    if (-not $Silent) { Write-Host "Installed certificate to Current User Root." -ForegroundColor Green }
} catch {
    $errors++
    if (-not $Silent) { Write-Host "Could not install to Current User Root (trying certutil fallback): $($_.Exception.Message)" -ForegroundColor Yellow }
    try {
        certutil.exe -user -f -addstore "Root" $resolved | Out-Null
        if (-not $Silent) { Write-Host "Installed via certutil to Current User Root." -ForegroundColor Green }
        $errors--
    } catch {
        if (-not $Silent) { Write-Host "certutil fallback failed for Current User: $($_.Exception.Message)" -ForegroundColor Red }
    }
}

if ($errors -eq 0) {
    if (-not $Silent) { Write-Host "Certificate trust completed successfully." -ForegroundColor Green }
    exit 0
} else {
    if (-not $Silent) { Write-Host "Certificate trust finished with warnings." -ForegroundColor Yellow }
    exit 1
}
