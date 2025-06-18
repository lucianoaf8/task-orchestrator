# run_orchestrator.bat - Windows Service Script
@echo off
echo Starting Python Orchestrator...
cd /d "%~dp0"
echo Current directory: %CD%
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

REM Check if virtual environment exists (optional)
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check if requirements are installed
python -c "import sqlite3, croniter, flask" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing requirements...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install requirements
        pause
        exit /b 1
    )
)

REM Check if database exists
if not exist "data\orchestrator.db" (
    echo Database not found. Running configuration...
    python configure.py
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Configuration failed
        pause
        exit /b 1
    )
)

echo Starting orchestrator...
echo Press Ctrl+C to stop
python main.py

pause