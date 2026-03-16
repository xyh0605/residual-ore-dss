@echo off
chcp 936 >nul
echo ============================================================
echo   Residual Ore Recovery DSS - First-Time Setup
echo ============================================================
echo.

echo [1/2] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python not found!
    echo Please install Python 3.10 or 3.11 first:
    echo Download: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)
echo OK - Python installed:
python --version
echo.

echo [2/2] Installing dependencies (please wait)...
echo.
pip install streamlit pandas numpy scikit-learn plotly openpyxl
echo.
echo ============================================================
echo   Setup complete!
echo   Now double-click "start.bat" to run the system
echo ============================================================
echo.
pause
