# CarbonSense Backend Startup Script
# This script sets up and runs the Django backend automatically

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  CarbonSense Backend Startup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if virtual environment exists
if (-Not (Test-Path "venv")) {
    Write-Host ""
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Virtual environment created successfully" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[OK] Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to activate virtual environment" -ForegroundColor Red
    Write-Host "You may need to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if requirements.txt exists
if (-Not (Test-Path "requirements.txt")) {
    Write-Host "[ERROR] requirements.txt not found!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Install/Update dependencies
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if database exists, if not run migrations
if (-Not (Test-Path "db.sqlite3")) {
    Write-Host ""
    Write-Host "Setting up database (first time)..." -ForegroundColor Yellow

    Write-Host "  Creating migrations..." -ForegroundColor Cyan
    python manage.py makemigrations

    Write-Host "  Applying migrations..." -ForegroundColor Cyan
    python manage.py migrate

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Database setup complete" -ForegroundColor Green

        # Ask if user wants to create superuser
        Write-Host ""
        $createSuperuser = Read-Host "Would you like to create a superuser account? (y/n)"
        if ($createSuperuser -eq "y" -or $createSuperuser -eq "Y") {
            python manage.py createsuperuser
        }
    } else {
        Write-Host "[ERROR] Failed to setup database" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    # Run migrations in case there are new ones
    Write-Host ""
    Write-Host "Checking for database updates..." -ForegroundColor Yellow
    python manage.py migrate --no-input
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Database is up to date" -ForegroundColor Green
    }
}

# Start the Django server
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Starting Django Server" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend will run at: http://localhost:8000" -ForegroundColor Green
Write-Host "API endpoints at: http://localhost:8000/api/" -ForegroundColor Green
Write-Host "Admin panel at: http://localhost:8000/admin/" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python manage.py runserver
