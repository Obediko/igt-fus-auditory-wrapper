@echo off
setlocal
cd /d "%~dp0\.."

where py >nul 2>nul
if %errorlevel%==0 (
    set PY=py
) else (
    set PY=python
)

if not exist .venv (
    %PY% -m venv .venv
    if errorlevel 1 exit /b 1
)

.venv\Scripts\python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
.venv\Scripts\python -m pip install -e .
if errorlevel 1 exit /b 1

echo.
echo Setup complete.
echo Next: .venv\Scripts\python -m igt_fus_auditory devices
endlocal
