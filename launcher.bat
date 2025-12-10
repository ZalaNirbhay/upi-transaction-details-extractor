@echo off
title UPI Payment Extractor - Launcher
echo ==================================================
echo      UPI Payment Information Extractor
echo ==================================================
echo.
echo [1/2] Checking and Installing Requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install requirements. Please ensure Python is installed.
    pause
    exit /b
)

echo.
echo [2/2] Starting Application...
python main.py

pause
