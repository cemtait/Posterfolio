@echo off
set PROJECT=%~dp0..

cd /d "%PROJECT%"
py -3.13 -m venv .venv
call ".venv\Scripts\activate.bat"
pip install -r requirements.txt
pip install -e .