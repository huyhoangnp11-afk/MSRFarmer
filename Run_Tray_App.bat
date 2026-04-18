@echo off
cd /d "%~dp0"
echo Starting Microsoft Rewards Tray App...
set "PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" set "PYTHONW=pythonw"
start "" "%PYTHONW%" "%~dp0tray_app.py"
exit
