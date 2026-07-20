@echo off
REM Run this on Windows to package walkwalk.py into a double-clickable Walk Walk.exe
REM Usage: double-click this file, or run packaging\build_windows.bat from the project folder
cd /d "%~dp0\.."

where python >nul 2>nul
if errorlevel 1 (
    echo python not found - install Python 3 first (https://www.python.org/downloads/, check "Add python.exe to PATH" during install)
    pause
    exit /b 1
)

python -m venv .build-venv
call .build-venv\Scripts\activate.bat
pip install --quiet --upgrade pip pyinstaller

pyinstaller --windowed --onefile --noconfirm --name "Walk Walk" --icon "assets\icon\icon.ico" --add-data "quotes.json;." --add-data "fonts/ttf;fonts/ttf" --add-data "assets/icon/icon-256.png;assets/icon" walkwalk.py

call .build-venv\Scripts\deactivate.bat

echo.
echo Build complete: dist\Walk Walk.exe
echo Copy it to your desktop, then just double-click to run.
pause
