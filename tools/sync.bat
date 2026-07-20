@echo off
setlocal

set PROJECT=%~dp0..
cd /d "%PROJECT%"

echo.
echo ========================================
echo Syncing Poster Montage Designer
echo ========================================
echo.

echo Pulling latest changes...
git pull
if errorlevel 1 (
    echo.
    echo Git pull failed.
    exit /b %errorlevel%
)

echo.
echo Activating virtual environment...
call ".venv\Scripts\activate.bat"

echo.
echo Updating editable install...
pip install -e .
if errorlevel 1 (
    echo.
    echo pip install failed.
    exit /b %errorlevel%
)

echo.
echo Done.