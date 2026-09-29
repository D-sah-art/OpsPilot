@echo off
setlocal
cd /d "%~dp0"

REM 1. Augment PATH with common Python and Node.js installation paths
set "PATH=%~dp0.venv\Scripts;C:\Python313;C:\Python312;C:\Python311;C:\Program Files\nodejs;%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%PATH%"

REM 2. Detect exact Python executable
set "PYTHON_EXE=python"
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else if exist "C:\Python313\python.exe" (
    set "PYTHON_EXE=C:\Python313\python.exe"
)

REM 3. Detect exact NPM executable
set "NPM_EXE=npm"
if exist "C:\Program Files\nodejs\npm.cmd" (
    set "NPM_EXE=C:\Program Files\nodejs\npm.cmd"
)

echo ===================================================
echo   OpsPilot - Starting Complete Incident Command Center
echo ===================================================
echo.

echo 0. Clearing any lingering processes on ports 8000, 8080, 5173...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kill_ports.ps1"
echo.

echo 1. Starting ShopFlow Microservices on port 8000...
start "ShopFlow (Port 8000)" cmd /k "cd /d "%~dp0shopflow-test" && "%PYTHON_EXE%" -m uvicorn services.api_gateway.main:app --port 8000 --host 127.0.0.1"

echo 2. Starting OpsPilot Backend on port 8080...
start "OpsPilot Backend (Port 8080)" cmd /k "cd /d "%~dp0backend" && "%PYTHON_EXE%" -m uvicorn app.main:app --port 8080 --host 127.0.0.1"

echo 3. Starting OpsPilot React Frontend on port 5173...
start "OpsPilot Frontend (Port 5173)" cmd /k "cd /d "%~dp0frontend" && "%NPM_EXE%" run dev"

echo.
echo All services launched! Waiting 4 seconds for startup...
timeout /t 4 >nul
start http://localhost:5173
echo.
echo Done! OpsPilot Command Center is live at http://localhost:5173
echo Keep the opened terminal windows running during the demo.
