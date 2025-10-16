@echo off
echo ================================
echo PPR Bitcoin Database Setup
echo ================================
echo.

REM Change to backend directory and activate venv
cd ..\..\backend

echo [1/3] Activating Python environment...
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run backend/setup.bat first
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo [2/3] Navigating to seeds folder...
cd ..\data\seeds

echo [3/3] Running database setup...
echo.
python setup_database.py

echo.
pause