@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "launcher_gui.py"
