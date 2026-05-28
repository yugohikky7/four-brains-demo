@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo.
echo ================================================
echo   Four Brains Demo - Auto Deploy to GitHub
echo ================================================
echo.

REM Check git
where git > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed.
    echo Please install Git from: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

REM Check if git repo exists
if not exist ".git" (
    echo [INFO] Initializing git repository...
    git init
    git branch -M main
)

REM Check if remote is set
git remote -v | findstr "origin" > nul 2>&1
if errorlevel 1 (
    echo.
    echo [SETUP] Git remote not configured yet.
    echo.
    set /p REPO_URL="Enter your GitHub repo URL (e.g. https://github.com/yugohikky7/four-brains-demo.git): "
    git remote add origin %REPO_URL%
)

REM Stage all changes
echo.
echo [STEP 1] Staging all files...
git add .

REM Commit
echo.
echo [STEP 2] Committing changes...
git commit -m "Auto deploy update"
if errorlevel 1 (
    echo [INFO] No changes to commit. Continuing to push...
)

REM Push
echo.
echo [STEP 3] Pushing to GitHub...
echo If prompted, login via browser window that opens.
echo.
git push -u origin main

if errorlevel 1 (
    echo.
    echo ================================================
    echo [ERROR] Push failed.
    echo ================================================
    echo.
    echo If you see "authentication failed":
    echo   1. Install GitHub CLI: https://cli.github.com/
    echo   2. Run: gh auth login
    echo   3. Re-run this script
    echo.
    echo Or use GitHub Desktop (easier):
    echo   1. Download: https://desktop.github.com/
    echo   2. Open this folder in GitHub Desktop
    echo   3. Click "Push" button
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   SUCCESS! Code pushed to GitHub.
echo ================================================
echo.
echo Now go back to Render.com and click "Retry" button.
echo Your demo will be live in 5-10 minutes.
echo.
pause
