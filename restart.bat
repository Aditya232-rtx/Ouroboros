@echo off
setlocal enabledelayedexpansion
REM ─────────────────────────────────────────────────────────────────
REM Ouroboros AI — Restart Script (Windows)
REM
REM Kills any existing backend/frontend processes, then starts both.
REM   Backend:  FastAPI on port 8000
REM   Frontend: Next.js on port 3000
REM ─────────────────────────────────────────────────────────────────

echo.
echo  ================================================================
echo   Ouroboros AI — Restarting Servers
echo  ================================================================
echo.

set "PROJECT_DIR=%~dp0"

REM ── Step 1: Kill existing processes ────────────────────────────
echo [1/4] Stopping existing servers...

REM Kill backend (port 8000)
for /f "tokens=5" %%p in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%p /F >nul 2>&1
)
echo   [OK] Backend stopped (port 8000)

REM Kill frontend (port 3000)
for /f "tokens=5" %%p in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%p /F >nul 2>&1
)
echo   [OK] Frontend stopped (port 3000)

timeout /t 2 /nobreak >nul

REM ── Step 2: Ensure Docker containers are running ──────────────
echo [2/4] Checking Docker containers...
if exist "%PROJECT_DIR%docker-compose.yml" (
    cd /d "%PROJECT_DIR%"
    docker compose up -d 2>nul
    echo   [OK] Docker containers running
) else (
    echo   [WARN] docker-compose.yml not found
)

REM ── Step 3: Start backend ────────────────────────────────────
echo [3/4] Starting backend (FastAPI on port 8000)...
cd /d "%PROJECT_DIR%"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo   [ERROR] venv not found — run install.bat first
    exit /b 1
)

if not exist "logs" mkdir logs

start "Ouroboros-Backend" /min cmd /c "cd /d %PROJECT_DIR% && venv\Scripts\activate.bat && uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload > logs\backend.log 2>&1"
echo   [OK] Backend starting...

REM ── Step 4: Start frontend ──────────────────────────────────
echo [4/4] Starting frontend (Next.js on port 3000)...
if exist "%PROJECT_DIR%frontend" (
    cd /d "%PROJECT_DIR%frontend"

    if not exist "node_modules" (
        echo   Installing frontend dependencies...
        npm install --silent 2>nul
    )

    start "Ouroboros-Frontend" /min cmd /c "cd /d %PROJECT_DIR%frontend && npm run dev > %PROJECT_DIR%logs\frontend.log 2>&1"
    echo   [OK] Frontend starting...
) else (
    echo   [WARN] frontend\ directory not found — skipping
)

REM ── Wait & show info ─────────────────────────────────────────
echo.
echo   Waiting for servers to start...
timeout /t 5 /nobreak >nul

echo.
echo  ================================================================
echo   Ouroboros AI is running!
echo.
echo   Backend API:  http://localhost:8000
echo   API Docs:     http://localhost:8000/docs
echo   Dashboard:    http://localhost:3000
echo.
echo   Logs:
echo     type logs\backend.log
echo     type logs\frontend.log
echo.
echo   To stop:  stop.bat
echo  ================================================================
echo.

endlocal
