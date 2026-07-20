@echo off
setlocal

set "PROJECT=%~dp0.."
cd /d "%PROJECT%"

".venv\Scripts\python.exe" -m pip install -e . >nul
if errorlevel 1 (
    echo Editable install failed.
    exit /b %errorlevel%
)

".venv\Scripts\python.exe" -m poster_montage_designer.app