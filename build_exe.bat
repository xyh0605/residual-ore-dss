@echo off
chcp 936 >nul
echo ============================================================
echo   Residual Ore Recovery DSS - Build EXE
echo ============================================================
echo.

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)
python --version
echo.

echo [2/4] Installing dependencies...
pip install streamlit pandas numpy scikit-learn plotly openpyxl pyinstaller -q
echo Done.
echo.

echo [3/4] Building EXE (this takes several minutes)...
pyinstaller --noconfirm build.spec
echo.

echo [4/4] Copying application files...
if not exist "dist\ResidualOreDSS" (
    echo Build failed! Check error messages above.
    pause
    exit /b 1
)

xcopy /E /I /Y "modules" "dist\ResidualOreDSS\modules" >nul
copy /Y "app.py" "dist\ResidualOreDSS\" >nul
if exist "data" xcopy /E /I /Y "data" "dist\ResidualOreDSS\data" >nul
copy /Y "start.bat" "dist\ResidualOreDSS\" >nul

echo.
echo ============================================================
echo   Build complete!
echo   Output folder: dist\ResidualOreDSS\
echo   Run: ResidualOreDSS.exe or start.bat
echo ============================================================
echo.
pause
