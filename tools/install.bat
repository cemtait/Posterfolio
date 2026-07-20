@echo off
set PROJECT=%~dp0..

cd /d "%PROJECT%"
call ".venv\Scripts\activate.bat"
pip install -r requirements.txt
pip install -e .