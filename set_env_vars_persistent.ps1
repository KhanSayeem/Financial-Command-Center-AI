# set_env_vars_persistent.ps1
# PowerShell script to set environment variables persistently for the current user
# These will persist across PowerShell sessions and reboots

#Requires -RunAsAdministrator

Write-Host "🔧 Setting Persistent Environment Variables for Financial Command Center AI - Warp MCP" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Blue
Write-Host ""

Write-Host "⚠️  WARNING: This will set environment variables permanently for the current user!" -ForegroundColor Red
Write-Host "   These variables will be available in all new PowerShell sessions." -ForegroundColor Yellow
Write-Host ""

# Ask for confirmation
$confirmation = Read-Host "Do you want to continue? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "❌ Operation cancelled." -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "📊 Setting persistent Stripe API configuration..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("STRIPE_API_KEY", "sk_test_your_stripe_api_key_here", "User")
[Environment]::SetEnvironmentVariable("STRIPE_API_VERSION", "2024-06-20", "User")
[Environment]::SetEnvironmentVariable("STRIPE_DEFAULT_CURRENCY", "usd", "User")
[Environment]::SetEnvironmentVariable("MCP_STRIPE_PROD", "false", "User")

Write-Host "🏦 Setting persistent Plaid API configuration..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("PLAID_CLIENT_ID", "your_plaid_client_id_here", "User")
[Environment]::SetEnvironmentVariable("PLAID_SECRET", "your_plaid_secret_here", "User")
[Environment]::SetEnvironmentVariable("PLAID_ENV", "sandbox", "User")

Write-Host "📋 Setting persistent Xero API configuration..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("XERO_CLIENT_ID", "your_xero_client_id_here", "User")
[Environment]::SetEnvironmentVariable("XERO_CLIENT_SECRET", "your_xero_client_secret_here", "User")

Write-Host "🏢 Setting persistent Financial Command Center configuration..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("FCC_SERVER_URL", "https://127.0.0.1:8000", "User")
[Environment]::SetEnvironmentVariable("FCC_API_KEY", "claude-desktop-integration", "User")

Write-Host ""
Write-Host "✅ Persistent environment variables set successfully!" -ForegroundColor Green
Write-Host ""

Write-Host "🔄 Refreshing current session environment..." -ForegroundColor Cyan
# Refresh environment variables in current session
$env:STRIPE_API_KEY = [Environment]::GetEnvironmentVariable("STRIPE_API_KEY", "User")
$env:STRIPE_API_VERSION = [Environment]::GetEnvironmentVariable("STRIPE_API_VERSION", "User")
$env:STRIPE_DEFAULT_CURRENCY = [Environment]::GetEnvironmentVariable("STRIPE_DEFAULT_CURRENCY", "User")
$env:MCP_STRIPE_PROD = [Environment]::GetEnvironmentVariable("MCP_STRIPE_PROD", "User")
$env:PLAID_CLIENT_ID = [Environment]::GetEnvironmentVariable("PLAID_CLIENT_ID", "User")
$env:PLAID_SECRET = [Environment]::GetEnvironmentVariable("PLAID_SECRET", "User")
$env:PLAID_ENV = [Environment]::GetEnvironmentVariable("PLAID_ENV", "User")
$env:XERO_CLIENT_ID = [Environment]::GetEnvironmentVariable("XERO_CLIENT_ID", "User")
$env:XERO_CLIENT_SECRET = [Environment]::GetEnvironmentVariable("XERO_CLIENT_SECRET", "User")
$env:FCC_SERVER_URL = [Environment]::GetEnvironmentVariable("FCC_SERVER_URL", "User")
$env:FCC_API_KEY = [Environment]::GetEnvironmentVariable("FCC_API_KEY", "User")

Write-Host "🔍 Verification (persistent variables now active):" -ForegroundColor Cyan
Write-Host "STRIPE_API_KEY: " -NoNewline; Write-Host "sk_test_***" -ForegroundColor Green
Write-Host "PLAID_CLIENT_ID: " -NoNewline; Write-Host $env:PLAID_CLIENT_ID -ForegroundColor Green
Write-Host "PLAID_SECRET: " -NoNewline; Write-Host "***" -ForegroundColor Green
Write-Host "PLAID_ENV: " -NoNewline; Write-Host $env:PLAID_ENV -ForegroundColor Green
Write-Host "XERO_CLIENT_ID: " -NoNewline; Write-Host $env:XERO_CLIENT_ID -ForegroundColor Green
Write-Host "XERO_CLIENT_SECRET: " -NoNewline; Write-Host "***" -ForegroundColor Green
Write-Host "FCC_SERVER_URL: " -NoNewline; Write-Host $env:FCC_SERVER_URL -ForegroundColor Green
Write-Host "FCC_API_KEY: " -NoNewline; Write-Host $env:FCC_API_KEY -ForegroundColor Green

Write-Host ""
Write-Host "🚀 Ready to run Warp MCP servers!" -ForegroundColor Green
Write-Host "💡 Test with: python test_warp_mcp.py" -ForegroundColor Blue
Write-Host ""
Write-Host "✅ These variables will now be available in all new PowerShell sessions!" -ForegroundColor Green

Write-Host ""
Write-Host "🗑️  To remove these persistent variables later, run:" -ForegroundColor Cyan
Write-Host "   remove_env_vars.ps1" -ForegroundColor White