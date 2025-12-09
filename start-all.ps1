# CarbonSense Complete Startup Script
# This script starts both backend and frontend in separate windows

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  CarbonSense - Start All Services" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the root directory
if (-Not (Test-Path "carbonsense-backend") -or -Not (Test-Path "carbonsense-frontend")) {
    Write-Host "Error: carbonsense-backend or carbonsense-frontend folder not found!" -ForegroundColor Red
    Write-Host "Make sure you're running this script from the root carbon-sense directory" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting CarbonSense services..." -ForegroundColor Yellow
Write-Host ""

# Get absolute paths
$backendPath = Join-Path $PSScriptRoot "carbonsense-backend"
$frontendPath = Join-Path $PSScriptRoot "carbonsense-frontend"
$backendScript = Join-Path $backendPath "start-backend.ps1"
$frontendScript = Join-Path $frontendPath "start-frontend.ps1"

# Start Backend in a new PowerShell window
Write-Host "1. Starting Backend (Django)..." -ForegroundColor Cyan

if (Test-Path $backendScript) {
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "Set-Location '$backendPath'; & '$backendScript'"
    Write-Host "   Backend window opened" -ForegroundColor Green
} else {
    Write-Host "   Backend script not found at: $backendScript" -ForegroundColor Red
}

# Wait a moment before starting frontend
Write-Host ""
Write-Host "Waiting 3 seconds before starting frontend..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start Frontend in a new PowerShell window
Write-Host ""
Write-Host "2. Starting Frontend (React + Vite)..." -ForegroundColor Cyan

if (Test-Path $frontendScript) {
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "Set-Location '$frontendPath'; & '$frontendScript'"
    Write-Host "   Frontend window opened" -ForegroundColor Green
} else {
    Write-Host "   Frontend script not found at: $frontendScript" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Services Starting..." -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Two new windows have been opened:" -ForegroundColor White
Write-Host "  1. Backend (Django) - http://localhost:8000" -ForegroundColor Green
Write-Host "  2. Frontend (React) - http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Wait a few seconds for both to start, then:" -ForegroundColor Yellow
Write-Host "  Open http://localhost:5173 in your browser" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop the servers:" -ForegroundColor Yellow
Write-Host "  Press Ctrl+C in each window" -ForegroundColor Cyan
Write-Host ""
Write-Host "Startup complete!" -ForegroundColor Green
Write-Host ""

Read-Host "Press Enter to close this window"
