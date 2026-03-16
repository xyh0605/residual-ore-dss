@echo off
chcp 936 >nul
title Residual Ore Recovery DSS v3.1
echo ============================================================
echo   Residual Ore Recovery DSS v3.1
echo ============================================================
echo.
echo Starting system, please wait...
echo.
echo URL: http://localhost:8501
echo.
echo Close this window to stop the system
echo ============================================================
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8501"

streamlit run "%~dp0app.py" --server.headless=true --browser.gatherUsageStats=false --server.port=8501 --theme.primaryColor=#2E75B6
