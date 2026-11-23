@echo off
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
".venv-gui\Scripts\python.exe" -B "scripts\launch_kilosort.py"
if errorlevel 1 pause
