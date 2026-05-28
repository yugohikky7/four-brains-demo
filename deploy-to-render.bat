@echo off
setlocal
cd /d "%~dp0"
title Deploy to Render.com

echo.
echo ================================================
echo   Checking git installation
echo ================================================
echo.
where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed or not in PATH.
    echo Please install Git from https://git-scm.com/download/win
    pause
    exit /b 1
)
git --version

echo.
echo ================================================
echo   Step 1: Reset corrupt git state
echo ================================================
echo.

if exist ".git" (
    echo Removing existing .git folder...
    rmdir /s /q .git
)

echo Initializing fresh repository on branch 'main'...
git init -b main
if errorlevel 1 (
    echo [WARN] Old git version. Falling back to manual rename.
    git init
    git checkout -b main 2>nul
)

git config user.email "y.hikita@four-brains.co.jp"
git config user.name "Yugo Hikita"

echo.
echo ================================================
echo   Step 2: Stage and commit all files
echo ================================================
echo.
echo (cloudflared.exe is excluded by .gitignore)

git add -A
git commit -m "Initial demo: keieidashboard mock SterTechnology"
if errorlevel 1 (
    echo [ERROR] Commit failed. Check git config and try again.
    pause
    exit /b 1
)
git log --oneline -1

echo.
echo ================================================
echo   Step 3: Push to GitHub
echo ================================================
echo.
echo Checking remote configuration...
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo Adding remote: https://github.com/yugohikky7/four-brains-demo.git
    git remote add origin https://github.com/yugohikky7/four-brains-demo.git
) else (
    echo Remote already configured:
    git remote get-url origin
)

echo.
echo Pushing to origin/main ^(force - overwrites remote^)...
echo (If a login window appears, sign in with your GitHub account)
echo.
git push -u origin main --force

if errorlevel 1 (
    echo.
    echo ================================================
    echo   [WARN] Push failed
    echo ================================================
    echo.
    echo Possible causes:
    echo   1. GitHub authentication needed - a login window may have opened
    echo   2. Repository does not exist - create at https://github.com/new
    echo      ^(name: four-brains-demo, Public, no README^)
    echo   3. Network issue - check internet connection
    echo.
    echo If you saw a browser login window, complete login and run this bat again.
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Step 4: Opening Render.com Blueprint page
echo ================================================
echo.
echo What to do on the Render page that opens:
echo   1. Sign in / sign up with GitHub
echo   2. Click "+ New Blueprint Instance"
echo   3. Select repo "four-brains-demo"
echo   4. Click "Apply"
echo   5. Wait 5-10 minutes for build to finish
echo   6. URL appears at top of service page
echo      ^(format: https://four-brains-demo-xxxx.onrender.com^)
echo.
timeout /t 3 /nobreak > nul
start "" "https://dashboard.render.com/blueprints"

echo.
echo Once the URL appears, you can share it freely.
echo The site stays up 24/7 even when your PC is off.
echo.
pause
