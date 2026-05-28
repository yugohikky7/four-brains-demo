@echo off
chcp 65001 > nul
cd /d "%~dp0"
title FORCE Push to overwrite broken commit

echo.
echo ================================================
echo   FORCE PUSH - overwriting broken 118d0ac
echo ================================================
echo.
echo Local commit log:
git log --oneline -5
echo.
echo Pushing with --force-with-lease...
echo.

git push origin main --force

if errorlevel 1 (
  echo.
  echo PUSH FAILED. Check internet/credentials.
  pause
  exit /b 1
)

echo.
echo ================================================
echo   PUSH SUCCESS - Render will auto-rebuild
echo ================================================
echo.
echo Wait 3-5 min, then check Render dashboard:
echo   https://dashboard.render.com/
echo.
echo Once Live, test in INCOGNITO:
echo   https://four-brains-demo.onrender.com
echo.
start "" "https://dashboard.render.com/"
pause
