@echo off
title AlphaTest
echo.
echo Starting AlphaTest...
echo.
cd /d "%~dp0"
python setup_and_run.py
if errorlevel 1 (
    echo.
    echo Python not found. Please install from: https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
)
