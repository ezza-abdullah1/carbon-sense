@echo off
REM CarbonSense Frontend Startup Script (Batch)

echo ======================================
echo   CarbonSense Frontend Startup
echo ======================================
echo.

REM Check if Node.js is installed
echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js is installed
echo.

REM Check if npm is installed
echo Checking npm installation...
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is not installed!
    pause
    exit /b 1
)
echo [OK] npm is installed
echo.

REM Check if package.json exists
if not exist "package.json" (
    echo [ERROR] package.json not found!
    echo Make sure you're in the carbonsense-frontend directory
    pause
    exit /b 1
)

REM Install dependencies if node_modules doesn't exist
if not exist "node_modules" (
    echo Installing dependencies (first time)...
    echo This may take a few minutes...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed successfully
) else (
    echo [OK] Dependencies already installed
)
echo.

REM Start development server
echo ======================================
echo   Starting Vite Dev Server
echo ======================================
echo.
echo Frontend will run at: http://localhost:5173
echo API requests will proxy to: http://localhost:8000
echo.
echo [WARNING] Make sure the backend is running!
echo.
echo Press Ctrl+C to stop the server
echo.

call npm run dev
