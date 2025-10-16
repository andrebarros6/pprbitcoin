@echo off
echo ================================
echo PPR Bitcoin Backend Setup
echo ================================
echo.

echo [1/4] Creating Python virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    echo Make sure Python 3.11+ is installed
    pause
    exit /b 1
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo [4/4] Setup complete!
echo.
echo ================================
echo Next steps:
echo 1. Start PostgreSQL: docker-compose up -d (from root folder)
echo 2. Run the server: python app.py
echo ================================
pause
