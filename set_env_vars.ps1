# set_env_vars.ps1
# PowerShell script to set environment variables for Warp MCP servers
# This sets variables for the current PowerShell session only

Write-Host "🔧 Setting Environment Variables for Financial Command Center AI - Warp MCP" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Blue

# Required API Keys
Write-Host "📊 Setting Stripe API configuration..." -ForegroundColor Yellow
$env:STRIPE_API_KEY = "sk_test_your_stripe_api_key_here"
$env:STRIPE_API_VERSION = "2024-06-20"
$env:STRIPE_DEFAULT_CURRENCY = "usd"
$env:MCP_STRIPE_PROD = "false"

Write-Host "🏦 Setting Plaid API configuration..." -ForegroundColor Yellow
$env:PLAID_CLIENT_ID = "your_plaid_client_id_here"
$env:PLAID_SECRET = "your_plaid_secret_here"
$env:PLAID_ENV = "sandbox"

Write-Host "📋 Setting Xero API configuration..." -ForegroundColor Yellow
$env:XERO_CLIENT_ID = "your_xero_client_id_here"
$env:XERO_CLIENT_SECRET = "your_xero_client_secret_here"

Write-Host "🏢 Setting Financial Command Center configuration..." -ForegroundColor Yellow
$env:FCC_SERVER_URL = "https://127.0.0.1:8000"
$env:FCC_API_KEY = "claude-desktop-integration"

Write-Host "" 
Write-Host "✅ Environment variables set successfully!" -ForegroundColor Green
Write-Host ""

# Verify the variables are set
Write-Host "🔍 Verification:" -ForegroundColor Cyan
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
Write-Host "⚠️  Note: These variables are set for this session only." -ForegroundColor Yellow
Write-Host "   Run 'set_env_vars_persistent.ps1' to make them permanent." -ForegroundColor Yellow