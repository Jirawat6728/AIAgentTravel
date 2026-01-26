@echo off
REM Backend Server Startup Script for Windows
echo ========================================
echo Starting AI Travel Agent Backend Server
echo ========================================
echo.

REM Check if virtual environment exists
if exist .venv\Scripts\activate.bat (
    echo [1/3] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found at .venv\Scripts\activate.bat
    echo [WARNING] Using system Python (may cause dependency issues)
    echo.
)

REM Check if .env file exists
if not exist .env (
    echo [WARNING] .env file not found!
    echo [WARNING] Please create .env file with required configuration
    echo.
)

echo [2/3] Starting FastAPI server with Uvicorn...
echo [INFO] Server will run on http://localhost:8000
echo [INFO] Health check: http://localhost:8000/health
echo [INFO] API docs: http://localhost:8000/docs
echo.
echo [3/3] Press Ctrl+C to stop the server
echo ========================================
echo.

REM Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
