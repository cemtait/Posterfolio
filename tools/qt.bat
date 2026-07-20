@echo off
setlocal

set PROJECT=%~dp0..

set DESIGNER="%PROJECT%\.venv\Scripts\pyside6-designer.exe"
set UIC="%PROJECT%\.venv\Scripts\pyside6-uic.exe"

echo.
echo ==========================================
echo Opening Qt Designer...
echo ==========================================
echo.

%DESIGNER% ^
    "%PROJECT%\src\poster_montage_designer\ui\main_window.ui"

echo.
echo ==========================================
echo Compiling .ui files...
echo ==========================================
echo.

for %%F in ("%PROJECT%\src\poster_montage_designer\ui\*.ui") do (
    echo    %%~nxF
    %UIC% "%%F" -o "%%~dpFui_%%~nF.py"
)

echo.
echo Finished compiling Qt UI files.
echo.
echo Done.
echo.
pause