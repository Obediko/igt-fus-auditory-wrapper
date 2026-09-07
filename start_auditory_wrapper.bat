@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Wrapper environment not found.
    echo Expected: %CD%\.venv\Scripts\python.exe
    echo Run scripts\setup_windows.bat first.
    pause
    exit /b 1
)

echo Starting IGT FUS Auditory Masking Wrapper...
".venv\Scripts\python.exe" "gui.py"
set "WRAPPER_EXIT=%ERRORLEVEL%"

if not "%WRAPPER_EXIT%"=="0" (
    echo.
    echo ERROR: The interface exited with code %WRAPPER_EXIT%.
    echo Copy the traceback shown above and send it for diagnosis.
    pause
)

endlocal & exit /b %WRAPPER_EXIT%
