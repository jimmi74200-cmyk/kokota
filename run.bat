@echo off
REM Kotak Neo Scalper Pro Launcher

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not found. Please install Python 3.8+ and add it to PATH.
    pause
    exit /b
)

if not exist "venv" (
    echo Creating virtual environment (venv)...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing/Updating requirements...
pip install -r requirements.txt >nul 2>&1

echo Starting Scalper Pro...
python main.py

pause
