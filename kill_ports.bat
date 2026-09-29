@echo off
echo ===================================================
echo   OpsPilot - Emergency Port Release (8000, 8080, 5173)
echo ===================================================
python "%~dp0scripts\free_ports.py"
echo.
pause
