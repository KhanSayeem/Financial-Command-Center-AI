# remove_env_vars.ps1
# PowerShell script to remove persistent environment variables set by set_env_vars_persistent.ps1

Write-Host "🗑️  Remove Persistent Environment Variables for Financial Command Center AI - Warp MCP" -ForegroundColor Red
Write-Host "=" * 80 -ForegroundColor Blue
Write-Host ""

Write-Host "⚠️  WARNING: This will permanently remove all Financial Command Center environment variables!" -ForegroundColor Red
Write-Host "   The following variables will be deleted:" -ForegroundColor Yellow
Write-Host "   - STRIPE_API_KEY, STRIPE_API_VERSION, STRIPE_DEFAULT_CURRENCY, MCP_STRIPE_PROD" -ForegroundColor White
Write-Host "   - PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV" -ForegroundColor White
Write-Host "   - XERO_CLIENT_ID, XERO_CLIENT_SECRET" -ForegroundColor White
Write-Host "   - FCC_SERVER_URL, FCC_API_KEY" -ForegroundColor White
Write-Host ""

# Ask for confirmation
$confirmation = Read-Host "Are you sure you want to remove all these variables? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "❌ Operation cancelled." -ForegroundColor Green
    exit
}

Write-Host ""
Write-Host "🗑️  Removing Stripe environment variables..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("STRIPE_API_KEY", $null, "User")
[Environment]::SetEnvironmentVariable("STRIPE_API_VERSION", $null, "User")
[Environment]::SetEnvironmentVariable("STRIPE_DEFAULT_CURRENCY", $null, "User")
[Environment]::SetEnvironmentVariable("MCP_STRIPE_PROD", $null, "User")

Write-Host "🗑️  Removing Plaid environment variables..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("PLAID_CLIENT_ID", $null, "User")
[Environment]::SetEnvironmentVariable("PLAID_SECRET", $null, "User")
[Environment]::SetEnvironmentVariable("PLAID_ENV", $null, "User")

Write-Host "🗑️  Removing Xero environment variables..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("XERO_CLIENT_ID", $null, "User")
[Environment]::SetEnvironmentVariable("XERO_CLIENT_SECRET", $null, "User")

Write-Host "🗑️  Removing Financial Command Center environment variables..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("FCC_SERVER_URL", $null, "User")
[Environment]::SetEnvironmentVariable("FCC_API_KEY", $null, "User")

Write-Host ""
Write-Host "🔄 Clearing current session environment..." -ForegroundColor Cyan
# Clear from current session
Remove-Item Env:STRIPE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:STRIPE_API_VERSION -ErrorAction SilentlyContinue
Remove-Item Env:STRIPE_DEFAULT_CURRENCY -ErrorAction SilentlyContinue
Remove-Item Env:MCP_STRIPE_PROD -ErrorAction SilentlyContinue
Remove-Item Env:PLAID_CLIENT_ID -ErrorAction SilentlyContinue
Remove-Item Env:PLAID_SECRET -ErrorAction SilentlyContinue
Remove-Item Env:PLAID_ENV -ErrorAction SilentlyContinue
Remove-Item Env:XERO_CLIENT_ID -ErrorAction SilentlyContinue
Remove-Item Env:XERO_CLIENT_SECRET -ErrorAction SilentlyContinue
Remove-Item Env:FCC_SERVER_URL -ErrorAction SilentlyContinue
Remove-Item Env:FCC_API_KEY -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "✅ All Financial Command Center environment variables have been removed!" -ForegroundColor Green
Write-Host ""
Write-Host "🔍 Verification - checking if variables are gone:" -ForegroundColor Cyan

$vars_to_check = @("STRIPE_API_KEY", "PLAID_CLIENT_ID", "PLAID_SECRET", "XERO_CLIENT_ID", "XERO_CLIENT_SECRET", "FCC_SERVER_URL")
$remaining = @()

foreach ($var in $vars_to_check) {
    $value = [Environment]::GetEnvironmentVariable($var, "User")
    if ($value) {
        $remaining += $var
        Write-Host "$var: Still set" -ForegroundColor Red
    } else {
        Write-Host "$var: ✅ Removed" -ForegroundColor Green
    }
}

if ($remaining.Count -eq 0) {
    Write-Host ""
    Write-Host "🎉 All environment variables successfully removed!" -ForegroundColor Green
    Write-Host "   You'll need to restart PowerShell sessions for changes to take full effect." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "⚠️  Some variables may still be set. You may need to restart your PowerShell session." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "💡 To set them again later, run: set_env_vars.ps1 or set_env_vars_persistent.ps1" -ForegroundColor Blue