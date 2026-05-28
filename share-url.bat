@echo off
cd /d "%~dp0"
title Four Brains Demo - Share URL
echo.
echo ================================================
echo   Four Brains Demo (MOCK DATA ONLY)
echo ================================================
echo.

REM Stop any existing server on 8765
echo [Cleanup] Stopping any existing server on port 8765...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765 " ^| findstr LISTENING') do (
    echo   Killing PID %%a
    taskkill /F /PID %%a > nul 2>&1
)
timeout /t 2 /nobreak > nul

REM Backup real freee tokens (privacy)
if exist "data\tokens.json" (
    if not exist "data\tokens.json.demo-backup" (
        echo [Privacy] Backing up tokens.json
        move /Y "data\tokens.json" "data\tokens.json.demo-backup" > nul
    ) else (
        del /F /Q "data\tokens.json"
    )
)
if exist "data\employee_overrides.json" (
    if not exist "data\employee_overrides.json.demo-backup" (
        move /Y "data\employee_overrides.json" "data\employee_overrides.json.demo-backup" > nul
    )
)
if exist "data\forecast_overrides.json" (
    if not exist "data\forecast_overrides.json.demo-backup" (
        move /Y "data\forecast_overrides.json" "data\forecast_overrides.json.demo-backup" > nul
    )
)

REM Download cloudflared if missing
if not exist "cloudflared.exe" (
    echo [Setup] Downloading cloudflared.exe...
    powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe' -UseBasicParsing } catch { Write-Host 'Download failed:' $_.Exception.Message; exit 1 }"
    if errorlevel 1 (pause & exit /b 1)
)

REM Start server in VISIBLE window so errors are visible
echo.
echo [1/2] Starting demo server (visible window so errors are visible)...
start "FB-Demo-Server" cmd /k "set MOCK_MODE=true&& set FREEE_CLIENT_ID=demo&& set FREEE_CLIENT_SECRET=demo&& .venv\Scripts\python.exe -m app.main"

REM Wait for server
echo Waiting 8 seconds for server to start...
timeout /t 8 /nobreak > nul

REM Verify server is responding AND in mock mode
echo.
echo [Verify] Checking server health...
powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://localhost:8765/api/status' -TimeoutSec 5; if ($r.mock_mode) { Write-Host '[OK] MOCK mode active' -ForegroundColor Green; exit 0 } else { Write-Host '[FAIL] Not mock mode' -ForegroundColor Red; exit 1 } } catch { Write-Host '[FAIL] Server not responding:' $_.Exception.Message -ForegroundColor Red; exit 1 }"
if errorlevel 1 (
    echo.
    echo ================================================
    echo   ABORT: Server did not start properly.
    echo.
    echo   Please check the "FB-Demo-Server" window
    echo   for Python error messages and report them.
    echo ================================================
    pause
    exit /b 1
)

echo.
echo [2/2] Creating public URL...
echo.
echo ================================================
echo   Look for "https://xxx.trycloudflare.com" below.
echo   Copy and share that URL.
echo ================================================
echo.

cloudflared.exe tunnel --url http://localhost:8765 --no-autoupdate

echo.
pause
