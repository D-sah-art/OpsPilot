# ShopFlow Windows PowerShell Startup Script
param (
    [switch]$Docker
)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Starting ShopFlow E-Commerce Microservices Platform" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

if ($Docker) {
    Write-Host "Starting via Docker Compose..." -ForegroundColor Green
    docker compose up --build
} else {
    Write-Host "Starting ShopFlow API Gateway on http://localhost:8000..." -ForegroundColor Green
    $env:PYTHONPATH = (Get-Location).Path
    python -m uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8000 --reload
}
