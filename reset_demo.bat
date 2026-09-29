@echo off
echo ===================================================
echo   OpsPilot - Resetting Demo to Clean Baseline
echo ===================================================
echo.

echo 1. Resetting ShopFlow Chaos Lab to IDLE...
curl.exe -s -X POST http://127.0.0.1:8000/api/chaos/reset
echo.

echo 2. Resetting OpsPilot SQLite Database...
del /f /q "%~dp0backend\opspilot.db" 2>nul
echo Clean baseline restored!
echo.
echo Ready for new live demo run!
