@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ============================================================
echo   freee Cashflow Dashboard - Auto-start Installer
echo ============================================================
echo.
echo This will:
echo   1. Run the server silently in the background.
echo   2. Auto-start the server every time you log in to Windows.
echo   3. Open the dashboard in your browser.
echo.
echo To stop, run stop.bat anytime.
echo To remove auto-start, run uninstall_autostart.bat.
echo.
pause

REM Check prerequisites
if not exist .venv (
    echo [ERROR] Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)
if not exist .venv\Scripts\pythonw.exe (
    echo [ERROR] .venv is incomplete. Delete .venv and run setup.bat again.
    pause
    exit /b 1
)

REM Create silent launcher VBS
echo [1/4] Creating silent launcher...
set "VBS=%~dp0_silent_run.vbs"
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.CurrentDirectory = "%~dp0"
    echo WshShell.Run """%~dp0.venv\Scripts\pythonw.exe"" -m app.main", 0, False
    echo Set WshShell = Nothing
) > "%VBS%"
echo       Done.

REM Create startup shortcut
echo [2/4] Creating startup shortcut...
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP%\freee-cashflow-dashboard.lnk"
powershell -NoProfile -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%VBS%'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'freee Cashflow Dashboard (silent background)'; $s.Save()"
if errorlevel 1 (
    echo [ERROR] Failed to create startup shortcut.
    pause
    exit /b 1
)
echo       Done.

REM Stop any existing instance
echo [3/4] Stopping any existing instance...
powershell -NoProfile -Command "Get-WmiObject Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -like '*app.main*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
echo       Done.

REM Launch silently right now
echo [4/4] Starting server in background...
wscript "%VBS%"
timeout /t 3 /nobreak >nul
echo       Done.

REM Create desktop shortcut to URL (optional but handy)
set "DESKTOP=%USERPROFILE%\Desktop"
set "URLSHORTCUT=%DESKTOP%\freee Cashflow Dashboard.url"
(
    echo [InternetShortcut]
    echo URL=http://localhost:8765
    echo IconIndex=0
) > "%URLSHORTCUT%"

REM Open browser
start http://localhost:8765

echo.
echo ============================================================
echo   Installation complete.
echo ============================================================
echo.
echo - Server now runs silently in the background.
echo - It will auto-start every time you log in to Windows.
echo - Browser shortcut created on Desktop:
echo     "freee Cashflow Dashboard.url"
echo - To stop the server, run: stop.bat
echo - To remove auto-start, run: uninstall_autostart.bat
echo.
pause
