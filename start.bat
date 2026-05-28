@echo off
setlocal

cd /d "%~dp0"

if not exist .venv (
    echo [ERROR] Virtual environment not found.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

if not exist .venv\Scripts\activate.bat (
    echo [ERROR] .venv is incomplete.
    echo Please delete the .venv folder and re-run setup.bat.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   freee Cashflow Dashboard
echo ============================================================
echo.
echo Starting server on http://localhost:8765
echo Browser will open automatically when server is ready.
echo To stop the server, press Ctrl+C in this window.
echo ============================================================
echo.

REM Open browser only after server responds (polls up to 20 sec)
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for ($i=0; $i -lt 20; $i++) { try { Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/status' -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop | Out-Null; Start-Process 'http://localhost:8765'; exit } catch { Start-Sleep -Seconds 1 } }"

call .venv\Scripts\activate.bat
python -m app.main
