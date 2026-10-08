@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo             INSIGHTFORGE - PART 2
echo ================================================
echo.

if not exist ".env" (
    echo [INFO] .env not found.
    echo Copying .env.example to .env...
    copy /Y ".env.example" ".env" >nul
)

if not exist "venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found.
    echo Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        echo Make sure Python is installed and added to PATH.
        pause
        exit /b 1
    )
)

echo [INFO] Installing/updating dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo [INFO] Starting FastAPI...
start "InsightForge API" cmd /k "cd /d ""%~dp0"" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo [INFO] Starting Excel watcher...
start "InsightForge Watcher" cmd /k "cd /d ""%~dp0"" && venv\Scripts\python.exe watcher.py"

timeout /t 2 /nobreak >nul

echo [INFO] Opening dashboard...
start "" "http://127.0.0.1:8000/dashboard.html"

echo.
echo ================================================
echo Dashboard: http://127.0.0.1:8000/dashboard.html
echo API:       http://127.0.0.1:8000/api/data
echo Docs:      http://127.0.0.1:8000/docs
echo ================================================
echo.
echo Close the two Python command windows to stop.
pause
