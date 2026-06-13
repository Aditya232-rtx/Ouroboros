@echo off
REM ─────────────────────────────────────────────────────────────────
REM Ouroboros SDK — Windows Installer
REM Resolves the Microsoft Store python.exe alias issue.
REM ─────────────────────────────────────────────────────────────────
setlocal EnableDelayedExpansion

echo.
echo  ================================================================
echo   Ouroboros SDK Installer (Windows)
echo  ================================================================
echo.

REM ── Step 1: Find a real Python 3.11+ ──────────────────────────
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
    echo  [ERROR] Could not find a real Python 3.11+ installation.
    echo.
    echo  The 'python' command on your system opens the Microsoft Store.
    echo  Please install Python from https://www.python.org/downloads/
    echo  and make sure to CHECK "Add Python to PATH" during installation.
    echo.
    echo  After installing, re-run this script.
    exit /b 1
)

echo  [OK] Found Python: %PYTHON%
for /f "delims=" %%v in ('"%PYTHON%" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PY_VER=%%v"
echo  [OK] Python version: %PY_VER%

REM ── Verify version >= 3.11 ────────────────────────────────────
for /f "delims=" %%c in ('"%PYTHON%" -c "import sys; print(1 if sys.version_info >= (3,11) else 0)"') do set "VER_OK=%%c"
if "%VER_OK%" neq "1" (
    echo  [ERROR] Python 3.11+ required, found %PY_VER%
    echo  Please install from https://www.python.org/downloads/
    exit /b 1
)

REM ── Step 2: Create virtual environment ────────────────────────
echo.
echo  [2/5] Creating virtual environment...
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

REM ── Step 3: Activate and upgrade pip ──────────────────────────
echo  [3/5] Upgrading pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel >nul 2>&1
echo  [OK] pip upgraded.

REM ── Step 4: Install the SDK ───────────────────────────────────
echo  [4/5] Installing Ouroboros SDK...

REM Prefer wheel if it exists
set "WHEEL="
for %%f in (dist\ouroboros_sdk-*.whl) do set "WHEEL=%%f"

if defined WHEEL (
    echo  [OK] Installing from wheel: %WHEEL%
    pip install "%WHEEL%" 2>&1
) else (
    echo  [OK] Installing from source (pip install .)
    pip install . 2>&1
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] SDK installation failed.
    echo  Try running manually:
    echo    venv\Scripts\activate.bat
    echo    pip install .
    exit /b 1
)

REM ── Step 5: Verify ────────────────────────────────────────────
echo  [5/5] Verifying installation...
ouroboros info
if %ERRORLEVEL% neq 0 (
    python -m ouroboros.cli info
)

echo.
echo  ================================================================
echo   SUCCESS! Ouroboros SDK installed.
echo  ================================================================
echo.
echo  Quick start:
echo    venv\Scripts\activate.bat
echo    cp config.example.yaml config.yaml
echo    # Edit config.yaml with your GitHub token
echo    ouroboros scan --repo https://github.com/owner/repo
echo.

endlocal
