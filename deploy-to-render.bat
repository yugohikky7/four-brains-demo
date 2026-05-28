@echo off
setlocal
cd /d "%~dp0"
title Deploy to Render.com

echo.
echo ================================================
echo   Re-deploy to Render.com (commit + push)
echo ================================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed or not in PATH.
    pause
    exit /b 1
)

if not exist ".git" (
    echo [INFO] No local repo found. Initializing fresh...
    git init -b main
    git config user.email "y.hikita@four-brains.co.jp"
    git config user.name "Yugo Hikita"
    git remote add origin https://github.com/yugohikky7/four-brains-demo.git
)

echo.
echo Staging all changes...
git add -A

echo.
echo Committing...
git commit -m "Update demo: unified CF model + org-chart + CEO interview fix"
if errorlevel 1 (
    echo [INFO] Nothing to commit (no changes) - skipping commit step.
)

echo.
echo Pushing to GitHub (origin/main)...
git push -u origin main --force

if errorlevel 1 (
    echo.
    echo [ERROR] Push failed. Check:
    echo   1. Internet connection
    echo   2. GitHub credentials  ^(may need re-login^)
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Push successful
echo ================================================
echo.
echo Render.com will auto-detect the push and start re-deploy.
echo Estimated build time: 5-10 minutes.
echo.
echo Opening Render dashboard to watch progress...
timeout /t 3 /nobreak > nul
start "" "https://dashboard.render.com/"

echo.
echo Watch for "Deploy succeeded" in the service log.
echo Your URL: https://four-brains-demo.onrender.com (or similar)
echo.
pause
