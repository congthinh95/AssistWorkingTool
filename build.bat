@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set VENV_DIR=.venv

echo ========================================
echo   DevDesk - Build ^& Validate
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ and ensure it is in PATH.
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/4] Creating virtual environment...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo [2/4] Upgrading pip...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip -q
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
)

echo [3/4] Installing dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [4/4] Running tests and packaging...
set PYTHONPATH=%~dp0
"%VENV_DIR%\Scripts\python.exe" -m pytest tests/ -q
if errorlevel 1 (
    echo [ERROR] Tests failed.
    pause
    exit /b 1
)
"%VENV_DIR%\Scripts\python.exe" scripts\build_package.py --target windows
if errorlevel 1 (
    echo [ERROR] Package build failed.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Build completed successfully
echo ========================================
endlocal
