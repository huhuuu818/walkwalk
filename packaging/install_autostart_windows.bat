@echo off
REM Make "Walk Walk" start automatically in the background at login (Windows, packaged exe).
REM Prerequisite: dist\Walk Walk.exe built with packaging\build_windows.bat
REM Usage: double-click this file; if the exe is elsewhere, drag it onto this file's icon
REM or pass its path as an argument.
REM
REM Note: the "Start at login" checkbox in the Settings panel does the same thing (pointing
REM at walkwalk.py directly, no packaging needed). Both configure the same startup entry —
REM set it up one way or the other, not both.
setlocal
set "EXE_PATH=%~1"
if "%EXE_PATH%"=="" set "EXE_PATH=%~dp0..\dist\Walk Walk.exe"

if not exist "%EXE_PATH%" (
    echo Not found: "%EXE_PATH%"
    echo Run packaging\build_windows.bat first, or pass the exe path as an argument
    pause
    exit /b 1
)

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
powershell -NoProfile -Command ^
  "$s=(New-Object -COM WScript.Shell).CreateShortcut('%STARTUP%\Walk Walk.lnk'); $s.TargetPath='%EXE_PATH%'; $s.Save()"

echo.
echo Login autostart installed, shortcut placed in: %STARTUP%
echo Walk Walk will now run in the background at login (tip: switch Schedule to Always in Settings so the timer starts right at boot).
echo.
echo To remove the autostart, just delete this file:
echo   %STARTUP%\Walk Walk.lnk
pause
