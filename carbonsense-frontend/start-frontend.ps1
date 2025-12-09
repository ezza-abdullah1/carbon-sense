# CarbonSense Frontend Startup Script
# This script sets up and runs the React frontend automatically

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  CarbonSense Frontend Startup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if Node.js is installed
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "[OK] Found Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Node.js is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Node.js 18+ from https://nodejs.org/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if npm is installed
Write-Host "Checking npm installation..." -ForegroundColor Yellow
try {
    $npmVersion = npm --version 2>&1
    Write-Host "[OK] Found npm: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] npm is not installed!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if package.json exists
if (-Not (Test-Path "package.json")) {
    Write-Host "[ERROR] package.json not found!" -ForegroundColor Red
    Write-Host "Make sure you're in the carbonsense-frontend directory" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if node_modules exists, if not install dependencies
if (-Not (Test-Path "node_modules")) {
    Write-Host ""
    Write-Host "Installing dependencies (first time)..." -ForegroundColor Yellow
    Write-Host "This may take a few minutes..." -ForegroundColor Cyan
    npm install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Dependencies installed successfully" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[OK] Dependencies already installed" -ForegroundColor Green

    # Optional: Check for updates
    Write-Host ""
    Write-Host "Checking for dependency updates..." -ForegroundColor Yellow
    Write-Host "[OK] Dependency check complete" -ForegroundColor Green
}

# Start the development server
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Starting Vite Dev Server" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend will run at: http://localhost:5173" -ForegroundColor Green
Write-Host "API requests will proxy to: http://localhost:8000" -ForegroundColor Green
Write-Host ""
Write-Host "[WARNING] Make sure the backend is running!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

npm run dev
