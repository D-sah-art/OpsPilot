$root = $PSScriptRoot

# 1. Augment PATH with standard Python and Node.js locations
$extraPaths = @(
    "$root\.venv\Scripts",
    "C:\Python313",
    "C:\Python312",
    "C:\Python311",
    "C:\Program Files\nodejs",
    "$env:LOCALAPPDATA\Programs\Python\Python313",
    "$env:LOCALAPPDATA\Programs\Python\Python312",
    "$env:LOCALAPPDATA\Programs\Python\Python311",
    "$env:APPDATA\npm"
)
foreach ($p in $extraPaths) {
    if ((Test-Path $p) -and ($env:PATH -notlike "*$p*")) {
        $env:PATH = "$p;$env:PATH"
    }
}

# 2. Resolve Python binary
$pythonExe = "python"
if (Test-Path "$root\.venv\Scripts\python.exe") {
    $pythonExe = "$root\.venv\Scripts\python.exe"
} elseif (Test-Path "C:\Python313\python.exe") {
    $pythonExe = "C:\Python313\python.exe"
}

# 3. Resolve NPM binary
$npmCmd = "npm"
if (Test-Path "C:\Program Files\nodejs\npm.cmd") {
    $npmCmd = "C:\Program Files\nodejs\npm.cmd"
}

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  OpsPilot - Starting Complete Incident Command Center" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "0. Releasing ports 8000, 8080, and 5173..." -ForegroundColor Yellow
& "$root\kill_ports.ps1"

Write-Host "1. Starting ShopFlow on port 8000..." -ForegroundColor Yellow
$shopflowCmd = "`$host.UI.RawUI.WindowTitle = 'ShopFlow (Port 8000)'; cd `"$root\shopflow-test`"; & '$pythonExe' -m uvicorn services.api_gateway.main:app --port 8000 --host 127.0.0.1"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $shopflowCmd

Write-Host "2. Starting OpsPilot Backend on port 8080..." -ForegroundColor Yellow
$backendCmd = "`$host.UI.RawUI.WindowTitle = 'OpsPilot Backend (Port 8080)'; cd `"$root\backend`"; & '$pythonExe' -m uvicorn app.main:app --port 8080 --host 127.0.0.1"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Write-Host "3. Starting OpsPilot Frontend on port 5173..." -ForegroundColor Yellow
$frontendCmd = "`$host.UI.RawUI.WindowTitle = 'OpsPilot UI (Port 5173)'; cd `"$root\frontend`"; & '$npmCmd' run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Start-Sleep -Seconds 4
Write-Host "Opening OpsPilot Dashboard..." -ForegroundColor Green
Start-Process "http://localhost:5173"
Write-Host "Done! All services are active." -ForegroundColor Green
