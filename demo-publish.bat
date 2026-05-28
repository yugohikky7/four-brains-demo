@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo.
echo ================================================
echo   Four Brains Demo - Publish to Public URL
echo ================================================
echo.

REM 1. ローカルサーバーを Mock モードで起動 (バックグラウンド)
echo [STEP 1] Starting demo server (Mock mode)...
set "MOCK_MODE=true"
start "FB Demo Server" /MIN cmd /c "set MOCK_MODE=true && .venv\Scripts\python.exe -m app.main"

echo Waiting for server to start...
timeout /t 3 /nobreak > nul

REM 2. ngrok で公開URL発行
echo.
echo [STEP 2] Publishing to public URL via ngrok...
echo.
echo *** URLが表示されたら、その URL を他の方に共有してください ***
echo *** Ctrl + C で停止 ***
echo.
ngrok.exe http 8765
