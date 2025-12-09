@echo off
REM CarbonSense Backend Startup Script (Batch)
REM This is an alternative to the PowerShell script

echo ======================================
echo   CarbonSense Backend Startup
echo ======================================
echo.

REM Check if Python is installed
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)
echo [OK] Python is installed
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM Setup database if it doesn't exist
if not exist "db.sqlite3" (
    echo Setting up database (first time)...
    echo   Creating migrations...
    python manage.py makemigrations
    echo   Applying migrations...
    python manage.py migrate
    if errorlevel 1 (
        echo [ERROR] Failed to setup database
        pause
        exit /b 1
    )
    echo [OK] Database setup complete
    echo.

    set /p createuser="Would you like to create a superuser? (y/n): "
    if /i "%createuser%"=="y" (
        python manage.py createsuperuser
    )
) else (
    echo Checking for database updates...
    python manage.py migrate --no-input
    echo [OK] Database is up to date
)
echo.

REM Start Django server
echo ======================================
echo   Starting Django Server
echo ======================================
echo.
echo Backend will run at: http://localhost:8000
echo API endpoints at: http://localhost:8000/api/
echo Admin panel at: http://localhost:8000/admin/
echo.
echo Press Ctrl+C to stop the server
echo.

python manage.py runserver
