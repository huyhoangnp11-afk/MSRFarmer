@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" zalo_agent_gui.py
) else (
    python zalo_agent_gui.py
)
