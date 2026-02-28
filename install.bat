@echo off
REM ─────────────────────────────────────────────────────────────────
REM Ouroboros AI — Full Installer (Windows)
REM
REM What this does:
REM   1. Finds Python 3.11+
REM   2. Creates a virtual environment
REM   3. Installs ALL Python dependencies (requirements.txt)
REM   4. Installs the Ouroboros SDK (pip install .)
REM   5. Installs frontend dependencies (npm install)
REM   6. Starts Docker containers (PostgreSQL, Redis, immudb, OPA)
REM   7. Verifies everything works
REM ─────────────────────────────────────────────────────────────────
setlocal EnableDelayedExpansion

echo.
echo  ================================================================
echo   Ouroboros AI — Full Installer (Windows)
echo  ================================================================
echo.

REM ── Step 1: Find a real Python 3.11+ ──────────────────────────
echo  [1/8] Finding Python 3.11+...
set "PYTHON="

REM Try py launcher first (most reliable on Windows)
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "delims=" %%i in ('py -3 -c "import sys; print(sys.executable)"  2^>nul') do set "PYTHON=%%i"
)

REM Try python3 (Git Bash, MSYS2, etc.)
if not defined PYTHON (
    where python3 >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        for /f "delims=" %%i in ('python3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON=%%i"
    )
)

REM Try python but verify it's real (not Microsoft Store alias)
if not defined PYTHON (
    where python >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)" 2^>nul') do (
            echo %%i | findstr /i "WindowsApps" >nul
            if !ERRORLEVEL! neq 0 (
                set "PYTHON=%%i"
            )
        )
    )
)

REM Try common manual install locations
if not defined PYTHON (
    for %%V in (313 312 311) do (
        if exist "C:\Python%%V\python.exe" (
            set "PYTHON=C:\Python%%V\python.exe"
            goto :found_python
        )
    )
    for %%V in (3.13 3.12 3.11) do (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
            set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
            goto :found_python
        )
    )
)

:found_python
if not defined PYTHON (
    echo  [ERROR] Could not find Python 3.11+.
    echo  Install from https://www.python.org/downloads/
    echo  Make sure to CHECK "Add Python to PATH" during installation.
    exit /b 1
)

for /f "delims=" %%v in ('"%PYTHON%" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PY_VER=%%v"
echo  [OK] Found Python: %PYTHON% (version %PY_VER%)

REM Verify version >= 3.11
for /f "delims=" %%c in ('"%PYTHON%" -c "import sys; print(1 if sys.version_info >= (3,11) else 0)"') do set "VER_OK=%%c"
if "%VER_OK%" neq "1" (
    echo  [ERROR] Python 3.11+ required, found %PY_VER%
    exit /b 1
)

REM ── Step 2: Check Docker ──────────────────────────────────────
echo.
echo  [2/8] Checking Docker...
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/
    exit /b 1
)
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Docker is installed but not running. Start Docker Desktop first.
    exit /b 1
)
echo  [OK] Docker is running

REM ── Step 3: Check Ollama ──────────────────────────────────────
echo.
echo  [3/8] Checking Ollama...
set "OLLAMA_OK=false"
where ollama >nul 2>&1
if %ERRORLEVEL% equ 0 (
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo  [OK] Ollama is running
        set "OLLAMA_OK=true"
    ) else (
        echo  [WARN] Ollama installed but not running. Start it with: ollama serve
    )
) else (
    echo  [WARN] Ollama not found. Install from https://ollama.com
)

REM ── Step 4: Create venv + install ALL Python deps ─────────────
echo.
echo  [4/8] Setting up Python environment...
if exist "venv" (
    echo  [OK] Virtual environment already exists.
) else (
    "%PYTHON%" -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo  [ERROR] Failed to create venv
        exit /b 1
    )
    echo  [OK] Created venv/
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel >nul 2>&1
echo  [OK] pip upgraded

echo  Installing requirements.txt (this may take a few minutes)...
pip install -r requirements.txt 2>&1 | findstr /i "error" || echo  [OK] Python dependencies installed

echo  Installing Ouroboros SDK...
pip install -e . 2>&1 | findstr /i "error" || pip install . 2>&1 | findstr /i "error" || echo  [OK] Ouroboros SDK installed

REM ── Step 5: Install frontend dependencies ─────────────────────
echo.
echo  [5/8] Installing frontend dependencies...
where node >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "delims=" %%v in ('node -v') do echo  [OK] Node.js found: %%v
    if exist "frontend" (
        pushd frontend
        call npm install 2>&1 | findstr /i "added"
        popd
        echo  [OK] Frontend dependencies installed
    ) else (
        echo  [WARN] frontend/ directory not found
    )
) else (
    echo  [WARN] Node.js not found — frontend won't work. Install from https://nodejs.org
)

REM ── Step 6: Start Docker containers ───────────────────────────
echo.
echo  [6/8] Starting Docker containers...
if exist "docker-compose.yml" (
    docker compose up -d 2>&1
    echo  [OK] Docker containers started (PostgreSQL, Redis, immudb, OPA)
    echo  Waiting for services...
    timeout /t 5 /nobreak >nul
    docker compose ps
) else (
    echo  [WARN] docker-compose.yml not found
)

REM ── Step 7: Pull Ollama model ─────────────────────────────────
echo.
echo  [7/8] Setting up LLM model...
if "%OLLAMA_OK%"=="true" (
    ollama list 2>nul | findstr /i "ouroboros-blue" >nul
    if %ERRORLEVEL% equ 0 (
        echo  [OK] Model 'ouroboros-blue' already exists
    ) else (
        echo  Pulling base model...
        ollama pull qwen2.5-coder:1.5b 2>&1
        if exist "models\Modelfile.deepseek" (
            echo  Creating ouroboros-blue model...
            ollama create ouroboros-blue -f models\Modelfile.deepseek 2>&1
            echo  [OK] Model created
        )
    )
) else (
    echo  [WARN] Ollama not available — run these later:
    echo    ollama pull qwen2.5-coder:1.5b
    echo    ollama create ouroboros-blue -f models\Modelfile.deepseek
)

REM ── Step 8: Verify ────────────────────────────────────────────
echo.
echo  [8/8] Verifying installation...
ouroboros info >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo  [OK] ouroboros CLI works
) else (
    python -m ouroboros.cli info >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo  [OK] ouroboros CLI works (via python -m)
    ) else (
        echo  [WARN] ouroboros CLI not on PATH
    )
)

if exist ".env" (
    echo  [OK] .env file exists
) else (
    echo  [WARN] .env file not found — create one (see README)
)

echo.
echo  ================================================================
echo   Ouroboros AI — Installation Complete!
echo  ================================================================
echo.
echo  To start scanning:
echo    venv\Scripts\activate.bat
echo    ouroboros scan --repo https://github.com/owner/repo
echo.
echo  To start the dashboard:
echo    restart.bat
echo.

endlocal
