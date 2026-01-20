@echo off
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    msg * "ERROR: Python is not installed or not in PATH!"
    exit /b 1
)

REM Check if Flask is installed, install if needed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    pip install -r requirements.txt >nul 2>&1
)

REM Start the Flask app silently using pythonw (no console window)
REM If pythonw is not available, use start /B to run in background
pythonw app.py 2>nul
if errorlevel 1 (
    REM Fallback: use start with /B flag to run in background
    start /B "" python app.py >nul 2>&1
)

REM Open browser after a short delay
timeout /t 2 /nobreak >nul
start http://localhost:5000

exit
