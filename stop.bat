@echo off
setlocal
echo Stopping freee Cashflow Dashboard server...
powershell -NoProfile -Command "Get-WmiObject Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -like '*app.main*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
echo Done.
timeout /t 2 /nobreak >nul
