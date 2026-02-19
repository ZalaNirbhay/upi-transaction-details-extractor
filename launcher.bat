@echo off
title UPI Payment Extractor - Launcher
color 0A

echo ==================================================
echo      UPI Payment Information Extractor
echo      Developed by Zala Nirbhay
echo ==================================================
echo.

echo [1/3] Checking Python Installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org
    pause
    exit /b
)

echo [2/3] Checking Dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install requirements.
    pause
    exit /b
)

echo.
echo [3/3] Starting Application...
python main.py

pause
