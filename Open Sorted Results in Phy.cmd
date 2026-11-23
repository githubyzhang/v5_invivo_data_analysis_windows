@echo off
cd /d "%~dp0"
set QT_API=pyqt5
set PYTHONDONTWRITEBYTECODE=1
".venv-phy\Scripts\phy.exe" template-gui "viewing\pilot01-playground\params.py"
if errorlevel 1 pause
