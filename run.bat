@echo off
setlocal

:: ============================================================
:: RoutePulse Universal Launcher for Windows Laptops
:: Sense - Estimate - Detect - Decide - Verify - Explain
:: ============================================================

:: Force working directory to repository root
cd /d "%~dp0"
title RoutePulse - Campus Transit Optimization

echo ============================================================
echo   RoutePulse: Campus Transit Optimization and Live Dashboard
echo   Problem PS 02 - Universal One-Click Launcher
echo ============================================================
echo.

:: ------------------------------------------------------------
:: 1. Detect Python on this laptop
:: ------------------------------------------------------------
set PYTHON_RUN=

:: Check local virtual environment (.venv)
if exist "%~dp0.venv\Scripts\python.exe" (
    set PYTHON_RUN="%~dp0.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

:: Check if Conda environment is active in current shell
if defined CONDA_PREFIX (
    if exist "%CONDA_PREFIX%\python.exe" (
        set PYTHON_RUN="%CONDA_PREFIX%\python.exe"
        goto :PYTHON_FOUND
    )
)

:: Check standard Anaconda / Miniconda install paths
if exist "C:\Users\%USERNAME%\miniconda3\envs\tracknet\python.exe" (
    set PYTHON_RUN="C:\Users\%USERNAME%\miniconda3\envs\tracknet\python.exe"
    goto :PYTHON_FOUND
)
if exist "C:\ProgramData\miniconda3\envs\tracknet\python.exe" (
    set PYTHON_RUN="C:\ProgramData\miniconda3\envs\tracknet\python.exe"
    goto :PYTHON_FOUND
)
if exist "C:\Users\%USERNAME%\anaconda3\envs\tracknet\python.exe" (
    set PYTHON_RUN="C:\Users\%USERNAME%\anaconda3\envs\tracknet\python.exe"
    goto :PYTHON_FOUND
)
if exist "C:\Users\%USERNAME%\miniconda3\python.exe" (
    set PYTHON_RUN="C:\Users\%USERNAME%\miniconda3\python.exe"
    goto :PYTHON_FOUND
)
if exist "C:\Users\%USERNAME%\anaconda3\python.exe" (
    set PYTHON_RUN="C:\Users\%USERNAME%\anaconda3\python.exe"
    goto :PYTHON_FOUND
)

:: Check if standard 'python' is in PATH (and not the Windows Store alias)
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python -c "import sys; sys.exit(0)" >nul 2>nul
    if not errorlevel 1 (
        set PYTHON_RUN=python
        goto :PYTHON_FOUND
    )
)

:: Check Python Launcher 'py'
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py -3 -c "import sys; sys.exit(0)" >nul 2>nul
    if not errorlevel 1 (
        set PYTHON_RUN=py -3
        goto :PYTHON_FOUND
    )
)

:: ------------------------------------------------------------
:: Python Not Found Handler
:: ------------------------------------------------------------
echo [ERROR] Python 3.10+ was not found on this computer!
echo.
echo To run RoutePulse, please install Python 3.10 or higher:
echo   1. Download from: https://www.python.org/downloads/
echo   2. IMPORTANT: Check the box "Add Python to PATH" during installation.
echo.
echo Or install Miniconda from:
echo   https://docs.conda.io/en/latest/miniconda.html
echo.
pause
exit /b 1

:PYTHON_FOUND
echo [OK] Detected Python interpreter: %PYTHON_RUN%
%PYTHON_RUN% -V
echo.

:: ------------------------------------------------------------
:: 2. Check and Install Required Dependencies
:: ------------------------------------------------------------
echo [RoutePulse] Verifying required Python packages...
%PYTHON_RUN% -c "import api.main" >nul 2>nul
if errorlevel 1 (
    echo [RoutePulse] Missing required packages. Installing from requirements.txt...
    echo Note: This only occurs on first launch and requires internet access.
    echo.
    %PYTHON_RUN% -m pip install -r requirements.txt
    %PYTHON_RUN% -c "import api.main" >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed. Please check your internet connection.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed successfully.
    echo.
) else (
    echo [OK] All required packages are ready.
    echo.
)

:: ------------------------------------------------------------
:: 3. Verify Synthetic Campus Dataset
:: ------------------------------------------------------------
if not exist "data\scenarios.json" (
    echo [RoutePulse] Generating 30-day synthetic campus transit dataset...
    %PYTHON_RUN% -m sim.generate_world
    if errorlevel 1 (
        echo [ERROR] Dataset generation failed.
        pause
        exit /b 1
    )
    echo [OK] Dataset successfully generated.
    echo.
) else (
    echo [OK] Synthetic dataset verified.
)

:: ------------------------------------------------------------
:: 3.5. Verify Web Dashboard Distribution
:: ------------------------------------------------------------
if not exist "web\dist\index.html" (
    echo [RoutePulse] Pre-built web dashboard distribution not found in web\dist.
    where npm >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        echo [RoutePulse] Building production web dashboard...
        pushd web
        call npm run build
        popd
        if exist "web\dist\index.html" (
            echo [OK] Web dashboard built successfully.
        )
    ) else (
        echo [WARNING] Node.js/npm not found to build web dashboard.
        echo The API documentation will be available at http://localhost:8000/docs
    )
    echo.
) else (
    echo [OK] Web dashboard distribution verified.
)

:: ------------------------------------------------------------
:: 4. Launch Server and Open Browser
:: ------------------------------------------------------------
echo.
echo ============================================================
echo   RoutePulse is starting on: http://localhost:8000
echo ============================================================
echo   * Web Dashboard:        http://localhost:8000/
echo   * Live SSE Telemetry:   http://localhost:8000/api/live/stream
echo   * Interactive API Docs: http://localhost:8000/docs
echo   * System Health Status: http://localhost:8000/healthz
echo.
echo   Opening dashboard in your default browser in 2 seconds...
echo   Press CTRL+C in this window to stop the server at any time.
echo ============================================================
echo.

:: Automatically trigger browser open after server initializes
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000/"

:: Start single-port Uvicorn server (serves React frontend + FastAPI backend)
%PYTHON_RUN% -m uvicorn api.main:app --host 0.0.0.0 --port 8000

echo.
echo [RoutePulse] Server stopped.
pause
