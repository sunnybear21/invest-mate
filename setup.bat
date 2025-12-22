@echo off
cd /d "%~dp0"

echo ========================================
echo   Lucy Scanner Setup (Safe Mode)
echo ========================================
echo.

echo Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed.
    echo Please install Python first: https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

echo.
echo [1/3] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b
)


echo.
echo [2/3] Installing libraries (this may take a minute)...
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install --upgrade setuptools wheel
venv\Scripts\python -m pip install -r requirements.txt


if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Pip install failed.
    pause
    exit /b
)

echo.
echo [3/3] Verifying...
venv\Scripts\python -c "import pykrx; print('Validation: pykrx found!')"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation verification failed.
    pause
    exit /b
)

echo.
echo ========================================
echo Setup Complete!
echo You can now run 'run_lucy_scan.bat'
echo ========================================
pause
