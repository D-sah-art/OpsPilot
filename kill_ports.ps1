Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  OpsPilot - Emergency Port Release (8000, 8080, 5173)" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Cyan

$ports = @(8000, 8080, 5173)
foreach ($port in $ports) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($conns) {
            foreach ($c in $conns) {
                $pidToKill = $c.OwningProcess
                if ($pidToKill -gt 4) {
                    Write-Host "Freeing port $port (Terminating PID $pidToKill)..." -ForegroundColor Yellow
                    Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
                }
            }
        } else {
            Write-Host "Port $port is free." -ForegroundColor Gray
        }
    } catch {
        # ignore
    }
}

# Also run free_ports.py if Python is found
$root = $PSScriptRoot
$pyPath = "python"
if (Test-Path "$root\.venv\Scripts\python.exe") { 
    $pyPath = "$root\.venv\Scripts\python.exe" 
} elseif (Test-Path "C:\Python313\python.exe") { 
    $pyPath = "C:\Python313\python.exe" 
}

try {
    & $pyPath "$root\scripts\free_ports.py" 2>$null
} catch {
    # Ignore python invocation errors since PowerShell already killed the ports
}

Write-Host "All ports (8000, 8080, 5173) are ready and clear!" -ForegroundColor Green
