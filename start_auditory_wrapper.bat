@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo Wrapper environment not found.
    echo Run scripts\setup_windows.bat first.
    pause
    exit /b 1
)

start "IGT FUS Auditory Masking Wrapper" ".venv\Scripts\pythonw.exe" "gui.py"
endlocal
