@echo off
setlocal

set PROJECT=%~dp0..
cd /d "%PROJECT%"

git add .
git status

echo.
set /p MSG=Commit message:

if "%MSG%"=="" (
    echo.
    echo Commit cancelled.
    exit /b 1
)

git commit -m "%MSG%"
if errorlevel 1 exit /b %errorlevel%

git rev-parse --abbrev-ref --symbolic-full-name @{u} >nul 2>&1

if errorlevel 1 (
    echo.
    echo First push of this branch...
    git push --set-upstream origin HEAD
) else (
    git push
)