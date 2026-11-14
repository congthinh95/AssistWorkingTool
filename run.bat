@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo   DevDesk - Starting...
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from https://www.python.org/downloads/
    echo         Make sure "Add Python to PATH" is checked during install.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

echo [2/3] Installing / updating dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b 1
)

echo [3/3] Launching DevDesk...
echo.
set PYTHONPATH=%~dp0
".venv\Scripts\python.exe" main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
endlocal
