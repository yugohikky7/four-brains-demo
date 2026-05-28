@echo off
setlocal
cd /d "%~dp0"
echo Restarting freee Cashflow Dashboard server...
powershell -NoProfile -Command "Get-WmiObject Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -like '*app.main*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
timeout /t 2 /nobreak >nul
if exist _silent_run.vbs (
    wscript _silent_run.vbs
    echo Server restarted in background.
) else (
    echo [ERROR] _silent_run.vbs not found. Run install_autostart.bat first.
    pause
)
timeout /t 2 /nobreak >nul
