@echo off
echo ========================================
echo IT Operations Dashboard - Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
python -m venv venv

echo [2/4] Activating virtual environment...
call venv\Scripts\activate

echo [3/4] Installing dependencies...
pip install flask pandas openpyxl

echo [4/4] Creating .env folder if needed...
if not exist ".env" mkdir .env
if not exist ".env\users.json" (
    echo {"users":[{"username":"viewer","password_hash":"65375049b9e4d7cad6c9ba286fdeb9394b28135a3e84136404cfccfdcc438894","role":"viewer","display_name":"Demo Viewer"}]} > .env\users.json
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo To start the dashboard, run: start_windows.bat
echo Or run manually: venv\Scripts\python app.py
echo.
pause
