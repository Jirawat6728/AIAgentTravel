# Backend Server Startup Script for PowerShell
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting AI Travel Agent Backend Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "[1/3] Activating virtual environment..." -ForegroundColor Yellow
    & .venv\Scripts\Activate.ps1
} else {
    Write-Host "[WARNING] Virtual environment not found at .venv\Scripts\Activate.ps1" -ForegroundColor Red
    Write-Host "[WARNING] Using system Python (may cause dependency issues)" -ForegroundColor Red
    Write-Host ""
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "[WARNING] .env file not found!" -ForegroundColor Red
    Write-Host "[WARNING] Please create .env file with required configuration" -ForegroundColor Red
    Write-Host ""
}

Write-Host "[2/3] Starting FastAPI server with Uvicorn..." -ForegroundColor Yellow
Write-Host "[INFO] Server will run on http://localhost:8000" -ForegroundColor Green
Write-Host "[INFO] Health check: http://localhost:8000/health" -ForegroundColor Green
Write-Host "[INFO] API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "[3/3] Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
