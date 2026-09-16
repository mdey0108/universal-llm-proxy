@echo off
title Universal LLM Proxy Server
cd /d "%~dp0"

echo [1/3] Checking and installing dependencies...
pip install -r requirements.txt -q

IF NOT EXIST "config.yaml" (
    echo.
    echo [!] 'config.yaml' not found! 
    echo [+] Creating 'config.yaml' from example...
    copy config.example.yaml config.yaml > nul
    echo.
    echo ╔═════════════════════════════════════════════════════════════════════════╗
    echo ║                          ACTION REQUIRED!                               ║
    echo ║                                                                         ║
    echo ║  1. A new 'config.yaml' file has been created for you.                  ║
    echo ║  2. Please open 'config.yaml' in any text editor.                       ║
    echo ║  3. Enter your real API Key in the 'provider -^> api_key' field.        ║
    echo ║  4. Run this 'start.bat' file again once you've saved your changes.     ║
    echo ╚═════════════════════════════════════════════════════════════════════════╝
    echo.
    pause
    exit /b
)

echo [2/3] Configuration 'config.yaml' found.
echo [3/3] Starting Universal LLM Proxy Server...
echo.

python proxy.py
pause
