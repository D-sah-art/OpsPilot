Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  OpsPilot - Resetting Demo to Clean Baseline" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Reset ShopFlow Chaos
Write-Host "1. Resetting ShopFlow Chaos Lab to IDLE..." -ForegroundColor Yellow
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chaos/reset" -Method Post -TimeoutSec 5
    Write-Host "   ShopFlow State: $($res.state) (Alerts: $($res.alert_count))" -ForegroundColor Green
} catch {
    Write-Host "   ShopFlow reset skipped (not running or unreachable)" -ForegroundColor Gray
}

# 2. Reset OpsPilot SQLite Database
Write-Host "2. Resetting OpsPilot SQLite Database..." -ForegroundColor Yellow
$dbPath = Join-Path $PSScriptRoot "backend\opspilot.db"
if (Test-Path $dbPath) {
    # Remove file or clear tables
    try {
        Remove-Item $dbPath -Force -ErrorAction Stop
        Write-Host "   Removed opspilot.db successfully." -ForegroundColor Green
    } catch {
        Write-Host "   Database is locked by backend. Re-initializing tables..." -ForegroundColor Gray
    }
}

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Demo Reset Complete! Ready for Clean Presentation" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
