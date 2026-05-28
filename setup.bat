@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ============================================================
echo   freee Cashflow Dashboard - Setup
echo ============================================================
echo.

REM Detect real Python (not MS Store stub)
set "PY_CMD="
py -3 --version >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=py -3"
    goto :py_ok
)
python --version >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :py_ok
)

echo [ERROR] Python is not installed.
echo.
echo Note: A "python" stub from Microsoft Store may exist,
echo but it is not a real Python installation.
echo.
echo Please install Python 3.10 or later from:
echo   https://www.python.org/downloads/
echo.
echo IMPORTANT: During installation, check the box
echo            "Add python.exe to PATH"
echo            at the bottom of the installer.
echo.
echo After installing, also disable the MS Store stub:
echo   Settings ^> Apps ^> Advanced app settings
echo   ^> App execution aliases ^> turn OFF python.exe and python3.exe
echo.
pause
exit /b 1

:py_ok
echo [INFO] Using: %PY_CMD%
%PY_CMD% --version
echo.

echo [1/3] Creating virtual environment...

REM Detect broken .venv (e.g. leftover from another OS)
if exist .venv (
    if not exist .venv\Scripts\activate.bat (
        echo       Found broken .venv. Removing and recreating...
        rmdir /s /q .venv
    )
)

if not exist .venv (
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

if not exist .venv\Scripts\activate.bat (
    echo [ERROR] Virtual environment is incomplete.
    echo Try deleting the .venv folder manually and re-running setup.bat.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [2/3] Installing dependencies. This may take 1-2 minutes on first run...
echo       (Using --only-binary to avoid any source compilation)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies.
    echo.
    echo If you see "No matching distribution found", your Python version
    echo may not have prebuilt wheels for one of the libraries.
    echo Try installing Python 3.12 or 3.13 from python.org and re-run setup.bat.
    echo.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [3/3] Preparing .env file...
if not exist .env (
    copy .env.example .env >nul
    echo       .env created from .env.example.
) else (
    echo       .env already exists. Skipped.
)
echo.

echo ============================================================
echo   Setup completed successfully.
echo ============================================================
echo.
echo Next steps:
echo   1. Double-click start.bat to launch the app.
echo   2. Your browser will open http://localhost:8765 automatically.
echo   3. The dashboard starts in Mock mode.
echo.
pause
