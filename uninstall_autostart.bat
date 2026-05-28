@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo   freee Cashflow Dashboard - Uninstall Auto-start
echo ============================================================
echo.

REM Remove startup shortcut
set "SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\freee-cashflow-dashboard.lnk"
if exist "%SHORTCUT%" (
    del /q "%SHORTCUT%"
    echo [OK] Removed startup shortcut.
) else (
    echo [SKIP] Startup shortcut not found.
)

REM Stop running instances
echo Stopping running server instances...
powershell -NoProfile -Command "Get-WmiObject Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -like '*app.main*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
echo [OK] Done.

REM Remove VBS launcher
if exist _silent_run.vbs (
    del /q _silent_run.vbs
    echo [OK] Removed silent launcher.
)

REM Remove desktop shortcut
set "URLSHORTCUT=%USERPROFILE%\Desktop\freee Cashflow Dashboard.url"
if exist "%URLSHORTCUT%" (
    del /q "%URLSHORTCUT%"
    echo [OK] Removed desktop shortcut.
)

echo.
echo ============================================================
echo   Uninstalled. You can still use start.bat / stop.bat
echo   to run the server manually anytime.
echo ============================================================
echo.
pause
