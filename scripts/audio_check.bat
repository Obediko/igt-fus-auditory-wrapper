@echo off
setlocal
cd /d "%~dp0\.."
if not exist .venv\Scripts\python.exe (
    echo Run scripts\setup_windows.bat first.
    exit /b 1
)
.venv\Scripts\python -m igt_fus_auditory audio-test --config config\study_mask.local.json --seconds 3
endlocal
