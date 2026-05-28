@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Deploy to Render.com

echo.
echo ================================================
echo   Deploy to Render.com  (debug version)
echo ================================================
echo Working directory:
echo   %CD%
echo.

REM ---- Step 0: check git ----
where git
if errorlevel 1 (
    echo.
    echo [ERROR] Git not found. Install from https://git-scm.com
    pause
    goto :end
)

echo.
echo ---- Step 1: git status ----
git status
echo.

echo ---- Step 2: stage all ----
git add -A
echo.

echo ---- Step 3: commit ----
git commit -m "Update demo: unified CF model + org-chart + CEO interview fix"
echo errorlevel after commit: %errorlevel%
echo.

echo ---- Step 4: check remote ----
git remote -v
echo.

REM If no remote, add it
git remote get-url origin > nul 2>&1
if errorlevel 1 (
    echo No remote configured. Adding origin...
    git remote add origin https://github.com/yugohikky7/four-brains-demo.git
    echo.
)

echo ---- Step 5: push ----
echo This may take 10-30 seconds...
git push -u origin main --force
set PUSH_EXIT=%errorlevel%
echo.
echo errorlevel after push: %PUSH_EXIT%
echo.

if not "%PUSH_EXIT%"=="0" (
    echo.
    echo ================================================
    echo   PUSH FAILED
    echo ================================================
    echo.
    echo Possible reasons:
    echo   1. Authentication needed - did a login window appear?
    echo   2. Network issue
    echo   3. GitHub repo doesn't exist or wrong URL
    echo.
    echo Press any key to close this window...
    pause
    goto :end
)

echo.
echo ================================================
echo   PUSH SUCCESSFUL!
echo ================================================
echo.
echo Render.com will detect this push and auto-rebuild.
echo Build time: 5-10 minutes.
echo.
echo Manually open these URLs in your browser:
echo.
echo   Dashboard:  https://dashboard.render.com/
echo   Your site:  https://four-brains-demo.onrender.com
echo.
echo (the site URL may have a suffix like -abc123)
echo.

:end
echo.
echo Press any key to close this window.
pause > nul
